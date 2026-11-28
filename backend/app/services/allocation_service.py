from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.allocation import OrderAllocation
from app.models.dispatch import Dispatch, DispatchItem
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem
from app.models.reservation import StockReservation
from app.models.shop_warehouse import ShopWarehouse
from app.models.user import User
from app.repositories.allocation_repository import AllocationRepository
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.allocation import AllocationCreateRequest, OrderAllocationSummaryResponse
from app.services.audit_service import AuditLogService


class AllocationService:
    """
    Manages order-item allocations across associated warehouses.

    Standardised lock acquisition order (strictly increasing rank to reduce deadlocks):
      1. orders (order_id ASC)
      2. order_items (order_item_id ASC)
      3. order_allocations (allocation_id ASC)
      4. stock_reservations (reservation_id ASC)
      5. dispatches (dispatch_id ASC)
      6. inventory (location_id ASC, product_id ASC)
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = AllocationRepository(db)
        self.inv_repo = InventoryRepository(db)

    def _get_non_cancelled_dispatched_quantity(self, allocation_id: int) -> Decimal:
        val = (
            self.db.query(func.coalesce(func.sum(DispatchItem.quantity), 0))
            .join(Dispatch, DispatchItem.dispatch_id == Dispatch.dispatch_id)
            .filter(
                DispatchItem.allocation_id == allocation_id,
                Dispatch.status != "CANCELLED",
            )
            .scalar()
        )
        return Decimal(str(val))

    def get_candidate_warehouses(self, shop_id: int) -> List[ShopWarehouse]:
        """
        Return warehouses associated with a shop ordered by preference and priority:
        preferred warehouse first, then ascending ShopWarehouse.priority, then warehouse_id.
        """
        return (
            self.db.query(ShopWarehouse)
            .filter(ShopWarehouse.shop_id == shop_id)
            .order_by(
                ShopWarehouse.is_preferred.desc(),
                ShopWarehouse.priority.asc(),
                ShopWarehouse.warehouse_id.asc(),
            )
            .all()
        )

    def allocate_order_item(self, req: AllocationCreateRequest, actor: Optional[User] = None) -> OrderAllocation:
        if req.allocated_quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Allocated quantity must be positive.",
            )

        try:
            # Non-locking lookup of order_id so locks follow canonical order: Order -> OrderItem -> Inventory
            item_meta = (
                self.db.query(OrderItem.order_id)
                .filter(OrderItem.order_item_id == req.order_item_id)
                .first()
            )
            if not item_meta:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found.")

            # 1. Lock Order (Rank 1)
            order = (
                self.db.query(Order)
                .filter(Order.order_id == item_meta.order_id)
                .with_for_update()
                .first()
            )
            if not order:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent order not found.")
            if order.status in ("FULFILLED", "CANCELLED", "REJECTED"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot allocate items for an order in {order.status} state.",
                )

            # 2. Lock OrderItem (Rank 2)
            order_item = (
                self.db.query(OrderItem)
                .filter(OrderItem.order_item_id == req.order_item_id)
                .with_for_update()
                .first()
            )
            if not order_item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found.")

            # 3. Verify Shop-Warehouse association
            link = (
                self.db.query(ShopWarehouse)
                .filter(
                    ShopWarehouse.shop_id == order.shop_id,
                    ShopWarehouse.warehouse_id == req.source_location_id,
                )
                .first()
            )
            if not link:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Warehouse {req.source_location_id} is not associated with shop {order.shop_id}.",
                )

            # 4. Prevent Over-Allocation (cross-check column & active allocations sum)
            active_allocated_sum = self.repo.get_total_allocated_for_order_item(order_item.order_item_id)
            effective_allocated = max(Decimal(str(order_item.quantity_allocated)), active_allocated_sum)
            unallocated_qty = Decimal(str(order_item.quantity_requested)) - effective_allocated
            if unallocated_qty < 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Inconsistent order item state: allocated quantity exceeds requested quantity.",
                )
            if req.allocated_quantity > unallocated_qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Over-allocation rejected. Requested {req.allocated_quantity}, "
                        f"but only {unallocated_qty} remains unallocated."
                    ),
                )

            # 5. Lock warehouse Inventory (Rank 6) & verify available stock
            inv = (
                self.db.query(Inventory)
                .filter(
                    Inventory.location_id == req.source_location_id,
                    Inventory.product_id == order_item.product_id,
                )
                .with_for_update()
                .first()
            )
            if not inv:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product does not exist in source warehouse inventory.",
                )

            available_stock = inv.quantity - inv.reserved_quantity
            if available_stock < req.allocated_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Insufficient available stock at warehouse. "
                        f"Available: {available_stock}, Requested: {req.allocated_quantity}."
                    ),
                )

            # 6. Create Allocation
            alloc = OrderAllocation(
                order_item_id=req.order_item_id,
                source_location_id=req.source_location_id,
                allocated_quantity=req.allocated_quantity,
                status="ALLOCATED",
            )
            self.db.add(alloc)
            self.db.flush()

            # Update order item allocated quantity
            order_item.quantity_allocated = Decimal(str(order_item.quantity_allocated)) + req.allocated_quantity

            # 7. Auto-reserve if requested (increases reserved_quantity only, not physical quantity)
            if req.auto_reserve:
                if inv.reserved_quantity + req.allocated_quantity > inv.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Cannot reserve more than available physical stock.",
                    )
                inv.reserved_quantity += req.allocated_quantity
                reservation = StockReservation(
                    allocation_id=alloc.allocation_id,
                    quantity_reserved=req.allocated_quantity,
                    status="ACTIVE",
                )
                self.db.add(reservation)
                alloc.status = "RESERVED"

            # 8. Update Order status
            all_items = (
                self.db.query(OrderItem)
                .filter(OrderItem.order_id == order.order_id)
                .order_by(OrderItem.order_item_id.asc())
                .all()
            )
            if any(item.quantity_allocated > 0 for item in all_items) and order.status == "PENDING":
                order.status = "PROCESSING"

            self.db.commit()
            self.db.refresh(alloc)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type="ALLOCATION_CREATED",
            actor_id=actor.user_id if actor else None,
            actor_role=actor.role if actor else None,
            entity_type="ALLOCATION",
            entity_id=alloc.allocation_id,
            location_id=alloc.source_location_id,
            details={
                "order_id": order.order_id,
                "order_item_id": alloc.order_item_id,
                "quantity": str(req.allocated_quantity),
                "status": alloc.status,
            },
        )

        return alloc

    def auto_allocate_order_item(
        self,
        order_item_id: int,
        auto_reserve: bool = True,
        actor: Optional[User] = None,
    ) -> List[OrderAllocation]:
        """
        Automatically allocate an order item across associated warehouses,
        respecting preferred warehouse first and then ShopWarehouse.priority ascending
        so alternative warehouses fulfil shortages from higher-priority warehouses.
        """
        try:
            item_meta = (
                self.db.query(OrderItem.order_id)
                .filter(OrderItem.order_item_id == order_item_id)
                .first()
            )
            if not item_meta:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found.")

            # 1. Lock Order (Rank 1)
            order = (
                self.db.query(Order)
                .filter(Order.order_id == item_meta.order_id)
                .with_for_update()
                .first()
            )
            if not order:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent order not found.")
            if order.status in ("FULFILLED", "CANCELLED", "REJECTED"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot allocate items for an order in {order.status} state.",
                )

            # 2. Lock OrderItem (Rank 2)
            order_item = (
                self.db.query(OrderItem)
                .filter(OrderItem.order_item_id == order_item_id)
                .with_for_update()
                .first()
            )
            if not order_item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found.")

            active_allocated_sum = self.repo.get_total_allocated_for_order_item(order_item.order_item_id)
            effective_allocated = max(Decimal(str(order_item.quantity_allocated)), active_allocated_sum)
            remaining = Decimal(str(order_item.quantity_requested)) - effective_allocated
            if remaining <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Order item is already fully allocated.",
                )

            # 3. Get associated warehouses in preference/priority order
            candidates = self.get_candidate_warehouses(order.shop_id)
            if not candidates:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No warehouses are associated with shop {order.shop_id}.",
                )

            # 4. Lock candidate Inventory rows in deterministic order (location_id ASC, product_id ASC)
            candidate_wh_ids = sorted({link.warehouse_id for link in candidates})
            locked_inventories = (
                self.db.query(Inventory)
                .filter(
                    Inventory.location_id.in_(candidate_wh_ids),
                    Inventory.product_id == order_item.product_id,
                )
                .order_by(Inventory.location_id.asc(), Inventory.product_id.asc())
                .with_for_update()
                .all()
            )
            inv_by_wh = {inv.location_id: inv for inv in locked_inventories}

            # 5. Allocate in preference/priority order across preferred + alternative warehouses
            created_allocations: List[OrderAllocation] = []
            for link in candidates:
                if remaining <= 0:
                    break
                inv = inv_by_wh.get(link.warehouse_id)
                if not inv:
                    continue
                available = inv.quantity - inv.reserved_quantity
                if available <= 0:
                    continue

                take_qty = min(remaining, available)
                alloc = OrderAllocation(
                    order_item_id=order_item.order_item_id,
                    source_location_id=link.warehouse_id,
                    allocated_quantity=take_qty,
                    status="ALLOCATED",
                )
                self.db.add(alloc)
                self.db.flush()

                if auto_reserve:
                    if inv.reserved_quantity + take_qty > inv.quantity:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Cannot reserve more than available physical stock.",
                        )
                    inv.reserved_quantity += take_qty
                    reservation = StockReservation(
                        allocation_id=alloc.allocation_id,
                        quantity_reserved=take_qty,
                        status="ACTIVE",
                    )
                    self.db.add(reservation)
                    alloc.status = "RESERVED"

                order_item.quantity_allocated = Decimal(str(order_item.quantity_allocated)) + take_qty
                remaining -= take_qty
                created_allocations.append(alloc)

            if not created_allocations:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient available stock across associated warehouses.",
                )

            if order.status == "PENDING":
                order.status = "PROCESSING"

            self.db.commit()
            for alloc in created_allocations:
                self.db.refresh(alloc)
        except Exception:
            self.db.rollback()
            raise

        for alloc in created_allocations:
            AuditLogService.log_event(
                event_type="ALLOCATION_CREATED",
                actor_id=actor.user_id if actor else None,
                actor_role=actor.role if actor else None,
                entity_type="ALLOCATION",
                entity_id=alloc.allocation_id,
                location_id=alloc.source_location_id,
                details={
                    "order_id": order.order_id,
                    "order_item_id": alloc.order_item_id,
                    "quantity": str(alloc.allocated_quantity),
                    "status": alloc.status,
                    "auto_allocated": True,
                },
            )

        return created_allocations

    def cancel_allocation(self, allocation_id: int, actor: Optional[User] = None) -> OrderAllocation:
        try:
            # Non-locking metadata lookup so we acquire locks in canonical order:
            # Order -> OrderItem -> OrderAllocation -> StockReservation -> Inventory
            meta = (
                self.db.query(
                    OrderAllocation.allocation_id,
                    OrderAllocation.order_item_id,
                    OrderAllocation.source_location_id,
                    OrderItem.order_id,
                    OrderItem.product_id,
                )
                .join(OrderItem, OrderAllocation.order_item_id == OrderItem.order_item_id)
                .filter(OrderAllocation.allocation_id == allocation_id)
                .first()
            )
            if not meta:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found.")

            # 1. Lock Order (Rank 1)
            order = (
                self.db.query(Order)
                .filter(Order.order_id == meta.order_id)
                .with_for_update()
                .first()
            )

            # 2. Lock OrderItem (Rank 2)
            order_item = (
                self.db.query(OrderItem)
                .filter(OrderItem.order_item_id == meta.order_item_id)
                .with_for_update()
                .first()
            )
            if not order_item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found.")

            # 3. Lock OrderAllocation (Rank 3)
            alloc = (
                self.db.query(OrderAllocation)
                .filter(OrderAllocation.allocation_id == allocation_id)
                .with_for_update()
                .first()
            )
            if not alloc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found.")

            if alloc.status == "CANCELLED":
                return alloc

            previous_status = alloc.status

            if alloc.status in ("DISPATCHED", "DELIVERED"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel allocation in {alloc.status} state.",
                )

            # Reject cancellation if any quantity has already been dispatched (including partial dispatch)
            dispatched_qty = self._get_non_cancelled_dispatched_quantity(alloc.allocation_id)
            if dispatched_qty > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Cannot cancel allocation {alloc.allocation_id}: "
                        f"{dispatched_qty} units have already been dispatched."
                    ),
                )

            # 4. Lock ACTIVE reservations in canonical order (Rank 4: reservation_id ASC)
            active_reservations = (
                self.db.query(StockReservation)
                .filter(
                    StockReservation.allocation_id == alloc.allocation_id,
                    StockReservation.status == "ACTIVE",
                )
                .order_by(StockReservation.reservation_id.asc())
                .with_for_update()
                .all()
            )

            # 5. Lock Inventory (Rank 6) if releasing active reservations
            if active_reservations:
                inv = (
                    self.db.query(Inventory)
                    .filter(
                        Inventory.location_id == alloc.source_location_id,
                        Inventory.product_id == order_item.product_id,
                    )
                    .with_for_update()
                    .first()
                )
                if not inv:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Inventory record missing while releasing active reservations.",
                    )

                total_to_release = sum(
                    (Decimal(str(res.quantity_reserved)) for res in active_reservations),
                    Decimal("0.00"),
                )
                if inv.reserved_quantity < total_to_release:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Inconsistent inventory state: reserved quantity ({inv.reserved_quantity}) "
                            f"is less than active reservations ({total_to_release})."
                        ),
                    )

                inv.reserved_quantity -= total_to_release
                for res in active_reservations:
                    res.status = "RELEASED"

            # Decrement order item quantity_allocated without silently clamping to zero
            if order_item.quantity_allocated < alloc.allocated_quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Inconsistent order item state: quantity_allocated ({order_item.quantity_allocated}) "
                        f"is less than allocation quantity ({alloc.allocated_quantity})."
                    ),
                )
            order_item.quantity_allocated -= alloc.allocated_quantity
            alloc.status = "CANCELLED"

            # Revert order status back to PENDING if no allocated quantities remain
            if order and order.status == "PROCESSING":
                all_items = (
                    self.db.query(OrderItem)
                    .filter(OrderItem.order_id == order.order_id)
                    .all()
                )
                if all(item.quantity_allocated == 0 for item in all_items):
                    order.status = "PENDING"

            self.db.commit()
            self.db.refresh(alloc)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type="ALLOCATION_CANCELLED",
            actor_id=actor.user_id if actor else None,
            actor_role=actor.role if actor else None,
            entity_type="ALLOCATION",
            entity_id=alloc.allocation_id,
            location_id=alloc.source_location_id,
            details={"previous_status": previous_status, "new_status": "CANCELLED"},
        )

        return alloc

    def list_by_order(self, order_id: int) -> List[OrderAllocation]:
        return self.repo.list_by_order(order_id)

    def list_by_warehouse(self, warehouse_id: int, status: Optional[str] = None) -> List[OrderAllocation]:
        return self.repo.list_by_warehouse(warehouse_id, status=status)

    def get_order_summary(self, order_id: int) -> OrderAllocationSummaryResponse:
        order = self.db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

        allocations = self.repo.list_by_order(order_id)
        items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

        unallocated_list = []
        for item in items:
            unallocated = item.quantity_requested - item.quantity_allocated
            if unallocated > 0:
                unallocated_list.append({
                    "order_item_id": item.order_item_id,
                    "product_id": item.product_id,
                    "unallocated_quantity": float(unallocated),
                })

        return OrderAllocationSummaryResponse(
            order_id=order.order_id,
            order_status=order.status,
            allocations=allocations,
            unallocated_items=unallocated_list,
        )
