import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Set
from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session
from app.models.allocation import OrderAllocation
from app.models.dispatch import Dispatch, DispatchItem
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem
from app.models.reservation import StockReservation
from app.models.user import User
from app.models.worker_task import WorkerTask
from app.repositories.dispatch_repository import DispatchRepository
from app.schemas.dispatch import DispatchCreateRequest, DispatchStatusUpdate
from app.services.audit_service import AuditLogService

VALID_DISPATCH_STATUSES: Set[str] = {
    "PENDING",
    "PACKING",
    "READY",
    "IN_TRANSIT",
    "DELIVERED",
    "CANCELLED",
}

ALLOWED_DISPATCH_TRANSITIONS: Dict[str, Set[str]] = {
    "PENDING": {"PACKING", "CANCELLED"},
    "PACKING": {"READY", "CANCELLED"},
    "READY": {"IN_TRANSIT", "CANCELLED"},
    "IN_TRANSIT": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}


class DispatchService:
    """
    Manages dispatch creation, controlled status transitions, delivery fulfillment,
    and role/warehouse/task authorization.

    Follows the canonical lock acquisition order:
      Order (Rank 1) -> OrderItem (Rank 2) -> OrderAllocation (Rank 3)
      -> StockReservation (Rank 4) -> Dispatch (Rank 5) -> Inventory (Rank 6)
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = DispatchRepository(db)

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

    def _get_delivered_quantity_for_allocation(self, allocation_id: int) -> Decimal:
        val = (
            self.db.query(func.coalesce(func.sum(DispatchItem.quantity), 0))
            .join(Dispatch, DispatchItem.dispatch_id == Dispatch.dispatch_id)
            .filter(
                DispatchItem.allocation_id == allocation_id,
                Dispatch.status == "DELIVERED",
            )
            .scalar()
        )
        return Decimal(str(val))

    def _get_delivered_quantity_for_order_item(self, order_item_id: int) -> Decimal:
        val = (
            self.db.query(func.coalesce(func.sum(DispatchItem.quantity), 0))
            .join(Dispatch, DispatchItem.dispatch_id == Dispatch.dispatch_id)
            .join(OrderAllocation, DispatchItem.allocation_id == OrderAllocation.allocation_id)
            .filter(
                OrderAllocation.order_item_id == order_item_id,
                Dispatch.status == "DELIVERED",
            )
            .scalar()
        )
        return Decimal(str(val))

    def _get_worker_valid_tasks_for_dispatch(
        self,
        worker_id: int,
        dispatch_id: int,
        allocation_ids: List[int],
    ) -> List[WorkerTask]:
        conditions = [WorkerTask.dispatch_id == dispatch_id]
        if allocation_ids:
            conditions.append(
                and_(
                    WorkerTask.dispatch_id.is_(None),
                    WorkerTask.allocation_id.in_(allocation_ids),
                )
            )
        return (
            self.db.query(WorkerTask)
            .filter(
                WorkerTask.assigned_worker_id == worker_id,
                WorkerTask.status != "CANCELLED",
                or_(*conditions),
            )
            .all()
        )

    def _authorize_create_dispatch(self, actor: User, source_location_id: int) -> None:
        if actor.role == "ADMIN":
            return
        if actor.role == "WAREHOUSE_MANAGER":
            if actor.location_id is None or actor.location_id != source_location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse managers can only create dispatches for their own warehouse.",
                )
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to create dispatches.",
        )

    def _authorize_status_update(
        self,
        actor: User,
        dispatch: Dispatch,
        target_status: str,
        allocation_ids: List[int],
    ) -> None:
        if actor.role == "ADMIN":
            return

        if actor.role == "WAREHOUSE_MANAGER":
            if actor.location_id is None or actor.location_id != dispatch.source_location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse managers can only update dispatches belonging to their own warehouse.",
                )
            return

        if actor.role == "WAREHOUSE_WORKER":
            if actor.location_id is None or actor.location_id != dispatch.source_location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workers cannot update dispatches belonging to another warehouse.",
                )

            valid_dispatch_task = (
                self.db.query(WorkerTask)
                .filter(
                    WorkerTask.assigned_worker_id == actor.user_id,
                    WorkerTask.dispatch_id == dispatch.dispatch_id,
                    WorkerTask.task_type == "DISPATCH",
                    WorkerTask.status != "CANCELLED",
                )
                .first()
            )
            if not valid_dispatch_task:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workers can only update dispatch progress when assigned a valid, non-cancelled DISPATCH task linked to that dispatch.",
                )

            if target_status in ("CANCELLED", "DELIVERED"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Workers are not authorized to set dispatch status to {target_status}.",
                )
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to update dispatch status.",
        )

    def create_dispatch(self, req: DispatchCreateRequest, actor: User) -> Dispatch:
        self._authorize_create_dispatch(actor, req.source_location_id)

        if not req.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dispatch must include at least one item.",
            )

        seen_allocations: Set[int] = set()
        for item_in in req.items:
            if item_in.quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dispatch item quantity must be positive.",
                )
            if item_in.allocation_id in seen_allocations:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate allocation {item_in.allocation_id} in single dispatch.",
                )
            seen_allocations.add(item_in.allocation_id)

        # Sort items by allocation_id ASC for deterministic lock acquisition
        sorted_items = sorted(req.items, key=lambda x: x.allocation_id)

        try:
            # 1. Lock Order (Rank 1)
            order = (
                self.db.query(Order)
                .filter(Order.order_id == req.order_id)
                .with_for_update()
                .first()
            )
            if not order:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
            if order.status in ("CANCELLED", "REJECTED", "FULFILLED"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot create dispatch for an order in {order.status} status.",
                )

            # 2. Lock OrderAllocations in allocation_id ASC order (Rank 3) & validate each item
            alloc_ids = [item_in.allocation_id for item_in in sorted_items]
            locked_allocs = (
                self.db.query(OrderAllocation)
                .filter(OrderAllocation.allocation_id.in_(alloc_ids))
                .order_by(OrderAllocation.allocation_id.asc())
                .with_for_update()
                .all()
            )
            alloc_by_id = {a.allocation_id: a for a in locked_allocs}

            validated_entries = []
            for item_in in sorted_items:
                alloc = alloc_by_id.get(item_in.allocation_id)
                if not alloc:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Allocation {item_in.allocation_id} not found.",
                    )

                if alloc.source_location_id != req.source_location_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Allocation {item_in.allocation_id} does not match source warehouse {req.source_location_id}.",
                    )

                order_item = self.db.query(OrderItem).filter_by(order_item_id=alloc.order_item_id).first()
                if not order_item:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Order item for allocation {item_in.allocation_id} not found.",
                    )

                if order_item.order_id != req.order_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Allocation {item_in.allocation_id} does not belong to order {req.order_id}.",
                    )

                if order_item.product_id != item_in.product_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Product {item_in.product_id} does not match allocation {item_in.allocation_id} "
                            f"product ({order_item.product_id})."
                        ),
                    )

                if alloc.status in ("CANCELLED", "DISPATCHED", "DELIVERED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot dispatch allocation {alloc.allocation_id} in {alloc.status} state.",
                    )

                dispatched_so_far = self._get_non_cancelled_dispatched_quantity(alloc.allocation_id)
                if dispatched_so_far + item_in.quantity > alloc.allocated_quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Cumulative dispatch quantity ({dispatched_so_far + item_in.quantity}) "
                            f"exceeds allocated quantity ({alloc.allocated_quantity})."
                        ),
                    )

                validated_entries.append((item_in, alloc, dispatched_so_far))

            # 3. Lock ACTIVE StockReservations for all involved allocations (Rank 4: reservation_id ASC)
            locked_active_reservations = (
                self.db.query(StockReservation)
                .filter(
                    StockReservation.allocation_id.in_(alloc_ids),
                    StockReservation.status == "ACTIVE",
                )
                .order_by(StockReservation.reservation_id.asc())
                .with_for_update()
                .all()
            )
            active_res_by_alloc: Dict[int, List[StockReservation]] = {aid: [] for aid in alloc_ids}
            for res in locked_active_reservations:
                active_res_by_alloc[res.allocation_id].append(res)

            # 4. Lock Inventory rows in deterministic order (Rank 6: location_id ASC, product_id ASC)
            product_ids = sorted({item_in.product_id for item_in in sorted_items})
            locked_inventories = (
                self.db.query(Inventory)
                .filter(
                    Inventory.location_id == req.source_location_id,
                    Inventory.product_id.in_(product_ids),
                )
                .order_by(Inventory.location_id.asc(), Inventory.product_id.asc())
                .with_for_update()
                .all()
            )
            inv_by_product = {inv.product_id: inv for inv in locked_inventories}

            # 5. Create Dispatch header
            dispatch_code = f"DSP-{uuid.uuid4().hex[:8].upper()}"
            dispatch = Dispatch(
                dispatch_code=dispatch_code,
                order_id=req.order_id,
                source_location_id=req.source_location_id,
                created_by_user_id=actor.user_id,
                status="PENDING",
                tracking_reference=req.tracking_reference,
                notes=req.notes,
            )
            self.db.add(dispatch)
            self.db.flush()

            # 6. Process stock consumption and dispatch items
            for item_in, alloc, dispatched_so_far in validated_entries:
                inv = inv_by_product.get(item_in.product_id)
                if not inv:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Inventory record not found for product {item_in.product_id} at warehouse {req.source_location_id}.",
                    )

                qty_to_dispatch = Decimal(str(item_in.quantity))
                alloc_active_reservations = active_res_by_alloc.get(alloc.allocation_id, [])
                total_active_reserved = sum(
                    (Decimal(str(r.quantity_reserved)) for r in alloc_active_reservations),
                    Decimal("0.00"),
                )

                # Consume active reservation quantity first, then unreserved available stock
                reserved_to_consume = min(qty_to_dispatch, total_active_reserved)
                unreserved_to_consume = qty_to_dispatch - reserved_to_consume

                if inv.reserved_quantity < reserved_to_consume:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Inconsistent inventory state: reserved quantity ({inv.reserved_quantity}) "
                            f"is less than reservation to consume ({reserved_to_consume})."
                        ),
                    )

                if inv.quantity < qty_to_dispatch:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Insufficient physical stock at warehouse. "
                            f"Available physical stock: {inv.quantity}, Requested: {qty_to_dispatch}."
                        ),
                    )

                available_unreserved = inv.quantity - inv.reserved_quantity
                if unreserved_to_consume > 0 and available_unreserved < unreserved_to_consume:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Insufficient available unreserved stock at warehouse. "
                            f"Available: {available_unreserved}, Unreserved needed: {unreserved_to_consume}."
                        ),
                    )

                # Consume active reservations (handling full and partial reservation consumption)
                remaining_from_res = reserved_to_consume
                for res in alloc_active_reservations:
                    if remaining_from_res <= 0:
                        break
                    res_qty = Decimal(str(res.quantity_reserved))
                    if res_qty <= remaining_from_res:
                        remaining_from_res -= res_qty
                        res.status = "CONFIRMED"
                    else:
                        consumed_part = remaining_from_res
                        res.quantity_reserved = res_qty - consumed_part
                        consumed_res = StockReservation(
                            allocation_id=alloc.allocation_id,
                            quantity_reserved=consumed_part,
                            reserved_at=res.reserved_at,
                            expires_at=res.expires_at,
                            status="CONFIRMED",
                        )
                        self.db.add(consumed_res)
                        remaining_from_res = Decimal("0.00")

                # Deduct physical stock once and reserved stock once (never clamp to zero)
                new_quantity = inv.quantity - qty_to_dispatch
                new_reserved = inv.reserved_quantity - reserved_to_consume
                if new_quantity < 0 or new_reserved < 0 or new_reserved > new_quantity:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Dispatch would produce invalid inventory quantities.",
                    )
                inv.quantity = new_quantity
                inv.reserved_quantity = new_reserved

                # Support partial dispatch without prematurely marking allocation DISPATCHED
                new_cumulative_dispatched = dispatched_so_far + qty_to_dispatch
                if new_cumulative_dispatched == alloc.allocated_quantity:
                    alloc.status = "DISPATCHED"
                else:
                    has_remaining_active_res = any(r.status == "ACTIVE" for r in alloc_active_reservations)
                    alloc.status = "RESERVED" if has_remaining_active_res else "ALLOCATED"

                dsp_item = DispatchItem(
                    dispatch_id=dispatch.dispatch_id,
                    allocation_id=alloc.allocation_id,
                    product_id=item_in.product_id,
                    quantity=qty_to_dispatch,
                )
                self.db.add(dsp_item)

            self.db.commit()
            self.db.refresh(dispatch)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type="DISPATCH_CREATED",
            actor_id=actor.user_id,
            actor_role=actor.role,
            entity_type="DISPATCH",
            entity_id=dispatch.dispatch_id,
            location_id=dispatch.source_location_id,
            details={
                "order_id": order.order_id,
                "shop_id": order.shop_id,
                "item_count": len(dispatch.items),
                "status": "PENDING",
            },
        )

        return dispatch

    def update_status(self, dispatch_id: int, req: DispatchStatusUpdate, actor: User) -> Dispatch:
        target_status = req.status.strip().upper()
        if target_status not in VALID_DISPATCH_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid dispatch status '{target_status}'.",
            )

        try:
            # Non-locking metadata lookup for canonical lock ordering
            meta = (
                self.db.query(Dispatch.dispatch_id, Dispatch.order_id, Dispatch.source_location_id)
                .filter(Dispatch.dispatch_id == dispatch_id)
                .first()
            )
            if not meta:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found.")

            # 1. Lock Order (Rank 1)
            order = (
                self.db.query(Order)
                .filter(Order.order_id == meta.order_id)
                .with_for_update()
                .first()
            )

            # 2. Lock OrderItems if transitioning to DELIVERED (Rank 2)
            order_items: List[OrderItem] = []
            if target_status == "DELIVERED" and order:
                order_items = (
                    self.db.query(OrderItem)
                    .filter(OrderItem.order_id == order.order_id)
                    .order_by(OrderItem.order_item_id.asc())
                    .with_for_update()
                    .all()
                )

            # 3. Lock linked OrderAllocations (Rank 3: allocation_id ASC)
            item_rows = (
                self.db.query(DispatchItem.allocation_id, DispatchItem.product_id)
                .filter(DispatchItem.dispatch_id == dispatch_id)
                .order_by(DispatchItem.allocation_id.asc())
                .all()
            )
            linked_alloc_ids = sorted({row.allocation_id for row in item_rows})
            locked_allocs: List[OrderAllocation] = []
            if linked_alloc_ids:
                locked_allocs = (
                    self.db.query(OrderAllocation)
                    .filter(OrderAllocation.allocation_id.in_(linked_alloc_ids))
                    .order_by(OrderAllocation.allocation_id.asc())
                    .with_for_update()
                    .all()
                )

            # 4. Lock Dispatch (Rank 5)
            dispatch = self.repo.get_by_id(dispatch_id, lock=True)
            if not dispatch:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found.")

            # Enforce authorization before any mutation
            self._authorize_status_update(actor, dispatch, target_status, linked_alloc_ids)

            current_status = dispatch.status

            # Enforce controlled transitions
            if target_status == "CANCELLED" and current_status in ("IN_TRANSIT", "DELIVERED"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot cancel dispatch in {current_status} status. Cancellation is allowed only before transit.",
                )

            if target_status not in ALLOWED_DISPATCH_TRANSITIONS.get(current_status, set()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid dispatch status transition from {current_status} to {target_status}.",
                )

            credited_items_summary: List[Dict[str, object]] = []
            if target_status == "IN_TRANSIT":
                dispatch.status = "IN_TRANSIT"
                dispatch.dispatch_date = datetime.now(timezone.utc)
                if req.tracking_reference:
                    dispatch.tracking_reference = req.tracking_reference

            elif target_status == "DELIVERED":
                # Exactly-once delivery crediting: reachable only from IN_TRANSIT under FOR UPDATE lock;
                # DELIVERED is terminal so this dispatch can never be credited twice.
                # Source warehouse stock was already deducted on dispatch creation and is NEVER deducted again.
                if not order:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Cannot credit delivered stock: parent order not found.",
                    )

                dispatch.status = "DELIVERED"
                self.db.flush()

                # Aggregate DispatchItem quantities by product_id to enforce (location_id, product_id) uniqueness
                qty_by_product: Dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
                for item in dispatch.items:
                    qty_by_product[item.product_id] += Decimal(str(item.quantity))

                product_ids = sorted(qty_by_product.keys())
                if product_ids:
                    # Lock destination shop Inventory rows in canonical order (Rank 6: location_id ASC, product_id ASC)
                    shop_inventories = (
                        self.db.query(Inventory)
                        .filter(
                            Inventory.location_id == order.shop_id,
                            Inventory.product_id.in_(product_ids),
                        )
                        .order_by(Inventory.location_id.asc(), Inventory.product_id.asc())
                        .with_for_update()
                        .all()
                    )
                    shop_inv_by_product = {inv.product_id: inv for inv in shop_inventories}

                    for pid in product_ids:
                        credit_qty = qty_by_product[pid]
                        shop_inv = shop_inv_by_product.get(pid)
                        if shop_inv is not None:
                            shop_inv.quantity = Decimal(str(shop_inv.quantity)) + credit_qty
                        else:
                            shop_inv = Inventory(
                                location_id=order.shop_id,
                                product_id=pid,
                                quantity=credit_qty,
                                reserved_quantity=Decimal("0.00"),
                            )
                            self.db.add(shop_inv)
                            shop_inv_by_product[pid] = shop_inv
                        credited_items_summary.append({"product_id": pid, "quantity": str(credit_qty)})

                    self.db.flush()

                # Mark an allocation DELIVERED only when its full allocated quantity has been delivered
                for alloc in locked_allocs:
                    delivered_for_alloc = self._get_delivered_quantity_for_allocation(alloc.allocation_id)
                    if delivered_for_alloc >= alloc.allocated_quantity:
                        alloc.status = "DELIVERED"

                # Calculate order fulfillment using DELIVERED dispatches only
                all_fulfilled = len(order_items) > 0
                any_delivered = False
                for it in order_items:
                    delivered_qty = self._get_delivered_quantity_for_order_item(it.order_item_id)
                    if delivered_qty > 0:
                        any_delivered = True
                    if delivered_qty < it.quantity_requested:
                        all_fulfilled = False

                if all_fulfilled:
                    order.status = "FULFILLED"
                elif any_delivered:
                    order.status = "PARTIALLY_FULFILLED"

            elif target_status == "CANCELLED":
                # Allowed only before transit (PENDING, PACKING, READY)
                # Lock Inventory in canonical order (Rank 6: location_id ASC, product_id ASC)
                product_ids = sorted({item.product_id for item in dispatch.items})
                locked_inventories = (
                    self.db.query(Inventory)
                    .filter(
                        Inventory.location_id == dispatch.source_location_id,
                        Inventory.product_id.in_(product_ids),
                    )
                    .order_by(Inventory.location_id.asc(), Inventory.product_id.asc())
                    .with_for_update()
                    .all()
                )
                inv_by_product = {inv.product_id: inv for inv in locked_inventories}

                dispatch.status = "CANCELLED"
                self.db.flush()

                # Restore physical stock that never left the warehouse
                for item in dispatch.items:
                    inv = inv_by_product.get(item.product_id)
                    if not inv:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Inventory record missing while cancelling dispatch.",
                        )
                    inv.quantity += item.quantity

                # Revert fully-dispatched allocations if their dispatched qty is now below allocated qty
                for alloc in locked_allocs:
                    if alloc.status == "DISPATCHED":
                        remaining_dispatched = self._get_non_cancelled_dispatched_quantity(alloc.allocation_id)
                        if remaining_dispatched < alloc.allocated_quantity:
                            has_active_res = (
                                self.db.query(StockReservation)
                                .filter_by(allocation_id=alloc.allocation_id, status="ACTIVE")
                                .first()
                                is not None
                            )
                            alloc.status = "RESERVED" if has_active_res else "ALLOCATED"

            else:
                # PACKING or READY
                dispatch.status = target_status

            if req.notes:
                dispatch.notes = req.notes

            self.db.commit()
            self.db.refresh(dispatch)
        except Exception:
            self.db.rollback()
            raise

        event_name = (
            "DISPATCH_CANCELLED"
            if target_status == "CANCELLED"
            else "DISPATCH_DELIVERED"
            if target_status == "DELIVERED"
            else "DISPATCH_STATUS_UPDATED"
        )
        audit_details: Dict[str, object] = {
            "order_id": dispatch.order_id,
            "previous_status": current_status,
            "new_status": target_status,
        }
        if target_status == "DELIVERED" and order:
            audit_details["destination_shop_id"] = order.shop_id
            audit_details["credited_items"] = credited_items_summary

        AuditLogService.log_event(
            event_type=event_name,
            actor_id=actor.user_id,
            actor_role=actor.role,
            entity_type="DISPATCH",
            entity_id=dispatch.dispatch_id,
            location_id=dispatch.source_location_id,
            details=audit_details,
        )

        return dispatch

    def get_dispatch(self, dispatch_id: int, actor: Optional[User] = None) -> Dispatch:
        dispatch = self.repo.get_by_id(dispatch_id)
        if not dispatch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found.")

        if actor is None or actor.role == "ADMIN":
            return dispatch

        if actor.role == "WAREHOUSE_MANAGER":
            if actor.location_id is None or actor.location_id != dispatch.source_location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse managers can only access dispatches belonging to their own warehouse.",
                )
            return dispatch

        if actor.role == "WAREHOUSE_WORKER":
            if actor.location_id is None or actor.location_id != dispatch.source_location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workers cannot access dispatches belonging to another warehouse.",
                )
            alloc_ids = [item.allocation_id for item in dispatch.items]
            valid_tasks = self._get_worker_valid_tasks_for_dispatch(
                worker_id=actor.user_id,
                dispatch_id=dispatch.dispatch_id,
                allocation_ids=alloc_ids,
            )
            if not valid_tasks:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workers can only access dispatches associated with their valid assigned tasks.",
                )
            return dispatch

        if actor.role == "SHOP_OWNER":
            order = self.db.query(Order).filter(Order.order_id == dispatch.order_id).first()
            if not order or actor.location_id != order.shop_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Shop owners can only access dispatches for their own shop's orders.",
                )
            return dispatch

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    def list_dispatches(
        self,
        actor: User,
        warehouse_id: Optional[int] = None,
        order_id: Optional[int] = None,
        status_filter: Optional[str] = None,
    ) -> List[Dispatch]:
        status_upper = status_filter.strip().upper() if status_filter else None

        if actor.role == "ADMIN":
            query = self.db.query(Dispatch)
            if order_id is not None:
                query = query.filter(Dispatch.order_id == order_id)
            if warehouse_id is not None:
                query = query.filter(Dispatch.source_location_id == warehouse_id)
            if status_upper:
                query = query.filter(Dispatch.status == status_upper)
            return query.order_by(Dispatch.created_at.desc()).all()

        if actor.role == "WAREHOUSE_MANAGER":
            if actor.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse manager is not assigned to a warehouse.",
                )
            if warehouse_id is not None and warehouse_id != actor.location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse managers can only access dispatches belonging to their own warehouse.",
                )
            query = self.db.query(Dispatch).filter(Dispatch.source_location_id == actor.location_id)
            if order_id is not None:
                query = query.filter(Dispatch.order_id == order_id)
            if status_upper:
                query = query.filter(Dispatch.status == status_upper)
            return query.order_by(Dispatch.created_at.desc()).all()

        if actor.role == "WAREHOUSE_WORKER":
            if actor.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Worker is not assigned to a warehouse.",
                )
            if warehouse_id is not None and warehouse_id != actor.location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workers cannot access dispatches belonging to another warehouse.",
                )
            worker_tasks = (
                self.db.query(WorkerTask)
                .filter(
                    WorkerTask.assigned_worker_id == actor.user_id,
                    WorkerTask.status != "CANCELLED",
                )
                .all()
            )
            direct_dispatch_ids = {t.dispatch_id for t in worker_tasks if t.dispatch_id is not None}
            alloc_only_ids = {
                t.allocation_id
                for t in worker_tasks
                if t.dispatch_id is None and t.allocation_id is not None
            }
            if alloc_only_ids:
                via_alloc = (
                    self.db.query(DispatchItem.dispatch_id)
                    .filter(DispatchItem.allocation_id.in_(alloc_only_ids))
                    .all()
                )
                direct_dispatch_ids.update(row.dispatch_id for row in via_alloc)

            if not direct_dispatch_ids:
                return []

            query = self.db.query(Dispatch).filter(
                Dispatch.source_location_id == actor.location_id,
                Dispatch.dispatch_id.in_(direct_dispatch_ids),
            )
            if order_id is not None:
                query = query.filter(Dispatch.order_id == order_id)
            if status_upper:
                query = query.filter(Dispatch.status == status_upper)
            return query.order_by(Dispatch.created_at.desc()).all()

        if actor.role == "SHOP_OWNER":
            if actor.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Shop owner is not assigned to a shop.",
                )
            if warehouse_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Shop owners cannot filter dispatches by warehouse.",
                )
            if order_id is not None:
                order = self.db.query(Order).filter(Order.order_id == order_id).first()
                if order and order.shop_id != actor.location_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Shop owners can only access dispatches for their own shop's orders.",
                    )
            query = (
                self.db.query(Dispatch)
                .join(Order, Dispatch.order_id == Order.order_id)
                .filter(Order.shop_id == actor.location_id)
            )
            if order_id is not None:
                query = query.filter(Dispatch.order_id == order_id)
            if status_upper:
                query = query.filter(Dispatch.status == status_upper)
            return query.order_by(Dispatch.created_at.desc()).all()

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    def list_by_order(self, order_id: int) -> List[Dispatch]:
        return self.repo.list_by_order(order_id)

    def list_by_warehouse(self, warehouse_id: int, status: Optional[str] = None) -> List[Dispatch]:
        return self.repo.list_by_warehouse(warehouse_id, status=status)
