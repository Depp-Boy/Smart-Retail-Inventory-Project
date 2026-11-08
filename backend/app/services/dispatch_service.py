import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.allocation import OrderAllocation
from app.models.dispatch import Dispatch, DispatchItem
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem
from app.models.reservation import StockReservation
from app.models.user import User
from app.repositories.dispatch_repository import DispatchRepository
from app.schemas.dispatch import DispatchCreateRequest, DispatchStatusUpdate
from app.services.audit_service import AuditLogService


class DispatchService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DispatchRepository(db)

    def create_dispatch(self, req: DispatchCreateRequest, actor: User) -> Dispatch:
        order = self.db.query(Order).filter(Order.order_id == req.order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

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

        seen_allocations = set()
        for item_in in req.items:
            if item_in.allocation_id in seen_allocations:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate allocation {item_in.allocation_id} in single dispatch.",
                )
            seen_allocations.add(item_in.allocation_id)

            alloc = (
                self.db.query(OrderAllocation)
                .filter(OrderAllocation.allocation_id == item_in.allocation_id)
                .with_for_update()
                .first()
            )
            if not alloc or alloc.source_location_id != req.source_location_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Allocation {item_in.allocation_id} does not match source warehouse.",
                )

            # Rule 4: Partial dispatch support & cumulative dispatch check
            dispatched_so_far = self.repo.get_dispatched_quantity_for_allocation(alloc.allocation_id)
            if dispatched_so_far + item_in.quantity > alloc.allocated_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cumulative dispatch quantity exceeds allocated quantity ({alloc.allocated_quantity}).",
                )

            # Consume active reservation if present (Rule 1: exactly once)
            for res in alloc.reservations:
                if res.status == "ACTIVE":
                    inv = (
                        self.db.query(Inventory)
                        .filter_by(location_id=alloc.source_location_id, product_id=item_in.product_id)
                        .with_for_update()
                        .first()
                    )
                    if inv:
                        inv.quantity = max(Decimal("0.00"), inv.quantity - item_in.quantity)
                        inv.reserved_quantity = max(Decimal("0.00"), inv.reserved_quantity - item_in.quantity)
                    res.status = "CONFIRMED"

            alloc.status = "DISPATCHED"
            dsp_item = DispatchItem(
                dispatch_id=dispatch.dispatch_id,
                allocation_id=alloc.allocation_id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
            )
            self.db.add(dsp_item)

        self.db.commit()
        self.db.refresh(dispatch)

        AuditLogService.log_event(
            event_type="DISPATCH_CREATED",
            actor_id=actor.user_id,
            entity_type="dispatches",
            entity_id=dispatch.dispatch_id,
            details={"order_id": order.order_id},
        )

        return dispatch

    def update_status(self, dispatch_id: int, req: DispatchStatusUpdate, actor: User) -> Dispatch:
        dispatch = self.repo.get_by_id(dispatch_id, lock=True)
        if not dispatch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found.")

        target_status = req.status.upper()
        if target_status == "IN_TRANSIT":
            dispatch.dispatch_date = datetime.now(timezone.utc)
            if req.tracking_reference:
                dispatch.tracking_reference = req.tracking_reference

        elif target_status == "DELIVERED":
            # Mark all linked allocations as DELIVERED
            for item in dispatch.items:
                alloc = self.db.query(OrderAllocation).filter_by(allocation_id=item.allocation_id).first()
                if alloc:
                    alloc.status = "DELIVERED"

            # Rule 3: Re-evaluate Order fulfillment based on total delivered quantities
            order = self.db.query(Order).filter(Order.order_id == dispatch.order_id).first()
            if order:
                items = self.db.query(OrderItem).filter(OrderItem.order_id == order.order_id).all()
                all_fulfilled = True
                any_delivered = False
                for it in items:
                    # Sum delivered quantity across all delivered dispatches for this item
                    delivered_qty = Decimal("0.00")
                    for a in it.allocations:
                        for di in a.dispatch_items:
                            if di.dispatch.status == "DELIVERED" or di.dispatch.dispatch_id == dispatch.dispatch_id:
                                delivered_qty += di.quantity

                    if delivered_qty > 0:
                        any_delivered = True
                    if delivered_qty < it.quantity_requested:
                        all_fulfilled = False

                if all_fulfilled:
                    order.status = "FULFILLED"
                elif any_delivered:
                    order.status = "PARTIALLY_FULFILLED"

        elif target_status == "CANCELLED":
            if dispatch.status in ("DELIVERED", "IN_TRANSIT"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot cancel dispatch in {dispatch.status} status.",
                )

        dispatch.status = target_status
        if req.notes:
            dispatch.notes = req.notes

        self.db.commit()
        self.db.refresh(dispatch)

        AuditLogService.log_event(
            event_type="DISPATCH_STATUS_UPDATED",
            actor_id=actor.user_id,
            entity_type="dispatches",
            entity_id=dispatch.dispatch_id,
            details={"new_status": target_status},
        )

        return dispatch

    def list_by_order(self, order_id: int) -> List[Dispatch]:
        return self.repo.list_by_order(order_id)

    def list_by_warehouse(self, warehouse_id: int, status: Optional[str] = None) -> List[Dispatch]:
        return self.repo.list_by_warehouse(warehouse_id, status=status)
