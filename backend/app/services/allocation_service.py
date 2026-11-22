from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.allocation import OrderAllocation
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
    def __init__(self, db: Session):
        self.db = db
        self.repo = AllocationRepository(db)
        self.inv_repo = InventoryRepository(db)

    def allocate_order_item(self, req: AllocationCreateRequest, actor: Optional[User] = None) -> OrderAllocation:
        # 1. Lock OrderItem & verify Order state
        order_item = (
            self.db.query(OrderItem)
            .filter(OrderItem.order_item_id == req.order_item_id)
            .with_for_update()
            .first()
        )
        if not order_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found.")

        order = self.db.query(Order).filter(Order.order_id == order_item.order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent order not found.")
        if order.status in ("FULFILLED", "CANCELLED", "REJECTED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot allocate items for an order in {order.status} state.",
            )

        # 2. Verify Shop-Warehouse relationship
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

        # 3. Prevent Over-Allocation
        unallocated_qty = order_item.quantity_requested - order_item.quantity_allocated
        if req.allocated_quantity > unallocated_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Over-allocation rejected. Requested {req.allocated_quantity}, but only {unallocated_qty} remains unallocated.",
            )

        # 4. Lock warehouse stock & verify available
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
                detail=f"Insufficient available stock at warehouse. Available: {available_stock}, Requested: {req.allocated_quantity}.",
            )

        # 5. Create Allocation
        alloc = OrderAllocation(
            order_item_id=req.order_item_id,
            source_location_id=req.source_location_id,
            allocated_quantity=req.allocated_quantity,
            status="ALLOCATED",
        )
        self.db.add(alloc)
        self.db.flush()

        # Update order item allocated quantity
        order_item.quantity_allocated += req.allocated_quantity

        # 6. Auto-reserve if requested (Stock Reservation Lifecycle rule 1)
        if req.auto_reserve:
            inv.reserved_quantity += req.allocated_quantity
            reservation = StockReservation(
                allocation_id=alloc.allocation_id,
                quantity_reserved=req.allocated_quantity,
                status="ACTIVE",
            )
            self.db.add(reservation)
            alloc.status = "RESERVED"

        # 7. Update Order status
        all_items = self.db.query(OrderItem).filter(OrderItem.order_id == order.order_id).all()
        all_allocated = all(item.quantity_allocated >= item.quantity_requested for item in all_items)
        if all_allocated:
            order.status = "PROCESSING"
        elif any(item.quantity_allocated > 0 for item in all_items):
            order.status = "PROCESSING"

        self.db.commit()
        self.db.refresh(alloc)

        # Audit post-commit
        AuditLogService.log_event(
            event_type="ORDER_ALLOCATED",
            actor_id=actor.user_id if actor else None,
            entity_type="order_allocations",
            entity_id=alloc.allocation_id,
            details={"order_id": order.order_id, "quantity": float(req.allocated_quantity)},
        )

        return alloc

    def cancel_allocation(self, allocation_id: int, actor: Optional[User] = None) -> OrderAllocation:
        alloc = self.repo.get_by_id(allocation_id, lock=True)
        if not alloc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found.")
        if alloc.status in ("DISPATCHED", "DELIVERED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel allocation in {alloc.status} state.",
            )
        if alloc.status == "CANCELLED":
            return alloc

        # Release active reservation if exists
        for res in alloc.reservations:
            if res.status == "ACTIVE":
                order_item = self.db.query(OrderItem).filter_by(order_item_id=alloc.order_item_id).first()
                if order_item:
                    inv = (
                        self.db.query(Inventory)
                        .filter_by(location_id=alloc.source_location_id, product_id=order_item.product_id)
                        .with_for_update()
                        .first()
                    )
                    if inv:
                        inv.reserved_quantity = max(Decimal("0.00"), inv.reserved_quantity - res.quantity_reserved)
                res.status = "RELEASED"

        # Decrement order item quantity_allocated
        order_item = self.db.query(OrderItem).filter_by(order_item_id=alloc.order_item_id).with_for_update().first()
        if order_item:
            order_item.quantity_allocated = max(Decimal("0.00"), order_item.quantity_allocated - alloc.allocated_quantity)

        alloc.status = "CANCELLED"
        self.db.commit()
        self.db.refresh(alloc)

        AuditLogService.log_event(
            event_type="ALLOCATION_CANCELLED",
            actor_id=actor.user_id if actor else None,
            entity_type="order_allocations",
            entity_id=alloc.allocation_id,
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
