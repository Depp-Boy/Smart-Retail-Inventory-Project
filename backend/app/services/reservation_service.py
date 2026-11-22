from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.allocation import OrderAllocation
from app.models.inventory import Inventory
from app.models.order import OrderItem
from app.models.reservation import StockReservation
from app.models.user import User
from app.repositories.reservation_repository import ReservationRepository
from app.schemas.reservation import ReservationCreateRequest
from app.services.audit_service import AuditLogService


class ReservationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ReservationRepository(db)

    def create_reservation(self, req: ReservationCreateRequest, actor: Optional[User] = None) -> StockReservation:
        alloc = (
            self.db.query(OrderAllocation)
            .filter(OrderAllocation.allocation_id == req.allocation_id)
            .with_for_update()
            .first()
        )
        if not alloc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found.")
        if alloc.status in ("CANCELLED", "DELIVERED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reserve stock for allocation in {alloc.status} status.",
            )

        order_item = self.db.query(OrderItem).filter_by(order_item_id=alloc.order_item_id).first()
        if not order_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found.")

        inv = (
            self.db.query(Inventory)
            .filter_by(location_id=alloc.source_location_id, product_id=order_item.product_id)
            .with_for_update()
            .first()
        )
        if not inv:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inventory record not found.")

        available = inv.quantity - inv.reserved_quantity
        if available < req.quantity_reserved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient available stock to reserve. Available: {available}, Requested: {req.quantity_reserved}.",
            )

        # Lifecycle rule 1: Increase inventory.reserved_quantity without changing physical quantity
        inv.reserved_quantity += req.quantity_reserved

        expires_at = None
        if req.expires_in_hours:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=req.expires_in_hours)

        res = StockReservation(
            allocation_id=alloc.allocation_id,
            quantity_reserved=req.quantity_reserved,
            expires_at=expires_at,
            status="ACTIVE",
        )
        self.db.add(res)
        alloc.status = "RESERVED"
        self.db.commit()
        self.db.refresh(res)

        AuditLogService.log_event(
            event_type="RESERVATION_CREATED",
            actor_id=actor.user_id if actor else None,
            entity_type="stock_reservations",
            entity_id=res.reservation_id,
            details={"quantity": float(req.quantity_reserved)},
        )

        return res

    def release_reservation(self, reservation_id: int, actor: Optional[User] = None) -> StockReservation:
        res = self.repo.get_by_id(reservation_id, lock=True)
        if not res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")
        if res.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Reservation cannot be released because status is {res.status}.",
            )

        alloc = self.db.query(OrderAllocation).filter_by(allocation_id=res.allocation_id).first()
        if alloc:
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
        self.db.commit()
        self.db.refresh(res)

        AuditLogService.log_event(
            event_type="RESERVATION_RELEASED",
            actor_id=actor.user_id if actor else None,
            entity_type="stock_reservations",
            entity_id=res.reservation_id,
        )

        return res

    def expire_reservation(self, reservation_id: int) -> StockReservation:
        res = self.repo.get_by_id(reservation_id, lock=True)
        if not res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")
        if res.status != "ACTIVE":
            return res

        alloc = self.db.query(OrderAllocation).filter_by(allocation_id=res.allocation_id).first()
        if alloc:
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

        res.status = "EXPIRED"
        self.db.commit()
        self.db.refresh(res)
        return res

    def confirm_reservation(self, reservation_id: int) -> StockReservation:
        res = self.repo.get_by_id(reservation_id, lock=True)
        if not res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")
        if res.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Reservation cannot be confirmed because status is {res.status}.",
            )

        alloc = self.db.query(OrderAllocation).filter_by(allocation_id=res.allocation_id).first()
        if alloc:
            order_item = self.db.query(OrderItem).filter_by(order_item_id=alloc.order_item_id).first()
            if order_item:
                inv = (
                    self.db.query(Inventory)
                    .filter_by(location_id=alloc.source_location_id, product_id=order_item.product_id)
                    .with_for_update()
                    .first()
                )
                if inv:
                    # Lifecycle rule 1: Decrement both quantity and reserved_quantity exactly once
                    inv.quantity = max(Decimal("0.00"), inv.quantity - res.quantity_reserved)
                    inv.reserved_quantity = max(Decimal("0.00"), inv.reserved_quantity - res.quantity_reserved)

        res.status = "CONFIRMED"
        self.db.commit()
        self.db.refresh(res)
        return res

    def list_by_allocation(self, allocation_id: int) -> List[StockReservation]:
        return self.repo.list_by_allocation(allocation_id)

    def list_active(self, skip: int = 0, limit: int = 50) -> List[StockReservation]:
        return self.repo.list_active(skip=skip, limit=limit)
