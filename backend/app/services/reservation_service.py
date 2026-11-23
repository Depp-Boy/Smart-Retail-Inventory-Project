from datetime import datetime, timedelta, timezone
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
from app.models.user import User
from app.repositories.reservation_repository import ReservationRepository
from app.schemas.reservation import ReservationCreateRequest
from app.services.audit_service import AuditLogService


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ReservationService:
    """
    Manages stock reservations for order allocations.

    Follows the canonical lock acquisition order:
      OrderAllocation (allocation_id ASC) -> StockReservation (reservation_id ASC) -> Inventory (location_id, product_id)
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = ReservationRepository(db)

    def _authorize_warehouse_write(self, actor: Optional[User], warehouse_id: int, action: str) -> None:
        if actor is None:
            return
        if actor.role == "ADMIN":
            return
        if actor.role == "WAREHOUSE_MANAGER":
            if actor.location_id is None or actor.location_id != warehouse_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Warehouse managers can only {action} reservations for their own warehouse.",
                )
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to {action} reservations.",
        )

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

    def create_reservation(self, req: ReservationCreateRequest, actor: Optional[User] = None) -> StockReservation:
        if req.quantity_reserved <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reservation quantity must be positive.",
            )

        try:
            # 1. Lock OrderAllocation (Rank 3)
            alloc = (
                self.db.query(OrderAllocation)
                .filter(OrderAllocation.allocation_id == req.allocation_id)
                .with_for_update()
                .first()
            )
            if not alloc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found.")

            self._authorize_warehouse_write(actor, alloc.source_location_id, "create")

            if alloc.status in ("CANCELLED", "DISPATCHED", "DELIVERED"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot reserve stock for allocation in {alloc.status} status.",
                )

            order_item = self.db.query(OrderItem).filter_by(order_item_id=alloc.order_item_id).first()
            if not order_item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found.")

            order = self.db.query(Order).filter_by(order_id=order_item.order_id).first()
            if order and order.status in ("CANCELLED", "REJECTED", "FULFILLED"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot reserve stock for an order in {order.status} status.",
                )

            # 2. Lock existing StockReservations for this allocation (Rank 4: reservation_id ASC)
            existing_reservations = (
                self.db.query(StockReservation)
                .filter(StockReservation.allocation_id == alloc.allocation_id)
                .order_by(StockReservation.reservation_id.asc())
                .with_for_update()
                .all()
            )

            active_reserved = sum(
                (Decimal(str(r.quantity_reserved)) for r in existing_reservations if r.status == "ACTIVE"),
                Decimal("0.00"),
            )
            confirmed_reserved = sum(
                (Decimal(str(r.quantity_reserved)) for r in existing_reservations if r.status == "CONFIRMED"),
                Decimal("0.00"),
            )
            dispatched_qty = self._get_non_cancelled_dispatched_quantity(alloc.allocation_id)
            consumed_qty = max(dispatched_qty, confirmed_reserved)

            if consumed_qty >= alloc.allocated_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot create reservation for a fully dispatched or consumed allocation.",
                )

            # 3. Lock Inventory (Rank 6)
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
                    detail=(
                        f"Insufficient available stock to reserve. "
                        f"Available: {available}, Requested: {req.quantity_reserved}."
                    ),
                )

            if active_reserved + consumed_qty + req.quantity_reserved > alloc.allocated_quantity:
                remaining_alloc = alloc.allocated_quantity - active_reserved - consumed_qty
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Reservation quantity ({req.quantity_reserved}) exceeds remaining allocation capacity "
                        f"({remaining_alloc}). Allocated: {alloc.allocated_quantity}, "
                        f"Active reserved: {active_reserved}, Consumed: {consumed_qty}."
                    ),
                )

            # Increase inventory.reserved_quantity without changing physical quantity
            if inv.reserved_quantity + req.quantity_reserved > inv.quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Reservation would cause reserved_quantity to exceed physical quantity.",
                )
            inv.reserved_quantity += req.quantity_reserved

            now_utc = datetime.now(timezone.utc)
            expires_at = None
            if req.expires_in_hours is not None:
                expires_at = now_utc + timedelta(hours=req.expires_in_hours)

            res = StockReservation(
                allocation_id=alloc.allocation_id,
                quantity_reserved=req.quantity_reserved,
                reserved_at=now_utc,
                expires_at=expires_at,
                status="ACTIVE",
            )
            self.db.add(res)
            alloc.status = "RESERVED"
            self.db.commit()
            self.db.refresh(res)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type="RESERVATION_CREATED",
            actor_id=actor.user_id if actor else None,
            actor_role=actor.role if actor else None,
            entity_type="RESERVATION",
            entity_id=res.reservation_id,
            location_id=alloc.source_location_id,
            details={
                "allocation_id": alloc.allocation_id,
                "quantity_reserved": str(req.quantity_reserved),
                "status": "ACTIVE",
            },
        )

        return res

    def _lock_reservation_chain(self, reservation_id: int):
        """
        Acquire locks in canonical order:
        OrderAllocation (Rank 3) -> StockReservation (Rank 4, reservation_id ASC)
        Returns (alloc, target_res, all_alloc_reservations).
        """
        meta = (
            self.db.query(StockReservation.reservation_id, StockReservation.allocation_id)
            .filter(StockReservation.reservation_id == reservation_id)
            .first()
        )
        if not meta:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")

        alloc = (
            self.db.query(OrderAllocation)
            .filter(OrderAllocation.allocation_id == meta.allocation_id)
            .with_for_update()
            .first()
        )
        if not alloc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent allocation not found.")

        all_res = (
            self.db.query(StockReservation)
            .filter(StockReservation.allocation_id == alloc.allocation_id)
            .order_by(StockReservation.reservation_id.asc())
            .with_for_update()
            .all()
        )
        target_res = next((r for r in all_res if r.reservation_id == reservation_id), None)
        if not target_res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")

        return alloc, target_res, all_res

    def release_reservation(self, reservation_id: int, actor: Optional[User] = None) -> StockReservation:
        try:
            alloc, res, all_res = self._lock_reservation_chain(reservation_id)
            self._authorize_warehouse_write(actor, alloc.source_location_id, "release")

            if res.status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Reservation cannot be released because status is {res.status}.",
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
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Inventory record missing while releasing reservation.",
                )

            if inv.reserved_quantity < res.quantity_reserved:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot release reservation: reserved_quantity ({inv.reserved_quantity}) "
                        f"is less than reservation quantity ({res.quantity_reserved})."
                    ),
                )

            inv.reserved_quantity -= res.quantity_reserved
            res.status = "RELEASED"

            has_other_active = any(
                r.reservation_id != res.reservation_id and r.status == "ACTIVE"
                for r in all_res
            )
            if alloc.status == "RESERVED" and not has_other_active:
                alloc.status = "ALLOCATED"

            self.db.commit()
            self.db.refresh(res)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type="RESERVATION_RELEASED",
            actor_id=actor.user_id if actor else None,
            actor_role=actor.role if actor else None,
            entity_type="RESERVATION",
            entity_id=res.reservation_id,
            location_id=alloc.source_location_id,
            details={"allocation_id": alloc.allocation_id, "previous_status": "ACTIVE", "new_status": "RELEASED"},
        )

        return res

    def expire_reservation(self, reservation_id: int, actor: Optional[User] = None) -> StockReservation:
        try:
            alloc, res, all_res = self._lock_reservation_chain(reservation_id)
            self._authorize_warehouse_write(actor, alloc.source_location_id, "expire")

            if res.status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Reservation cannot be expired because status is {res.status}.",
                )

            if res.expires_at is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reservation has no expiration timestamp and cannot be expired.",
                )

            now_utc = datetime.now(timezone.utc)
            if _to_utc(res.expires_at) > now_utc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot expire an unexpired reservation.",
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
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Inventory record missing while expiring reservation.",
                )

            if inv.reserved_quantity < res.quantity_reserved:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot expire reservation: reserved_quantity ({inv.reserved_quantity}) "
                        f"is less than reservation quantity ({res.quantity_reserved})."
                    ),
                )

            inv.reserved_quantity -= res.quantity_reserved
            res.status = "EXPIRED"

            has_other_active = any(
                r.reservation_id != res.reservation_id and r.status == "ACTIVE"
                for r in all_res
            )
            if alloc.status == "RESERVED" and not has_other_active:
                alloc.status = "ALLOCATED"

            self.db.commit()
            self.db.refresh(res)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type="RESERVATION_EXPIRED",
            actor_id=actor.user_id if actor else None,
            actor_role=actor.role if actor else None,
            entity_type="RESERVATION",
            entity_id=res.reservation_id,
            location_id=alloc.source_location_id,
            details={"allocation_id": alloc.allocation_id, "previous_status": "ACTIVE", "new_status": "EXPIRED"},
        )

        return res

    def confirm_reservation(self, reservation_id: int, actor: Optional[User] = None) -> StockReservation:
        try:
            alloc, res, all_res = self._lock_reservation_chain(reservation_id)
            self._authorize_warehouse_write(actor, alloc.source_location_id, "confirm")

            if res.status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Reservation cannot be confirmed because status is {res.status}.",
                )

            if alloc.status in ("CANCELLED", "DELIVERED"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot confirm reservation for allocation in {alloc.status} status.",
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
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Inventory record missing while confirming reservation.",
                )

            if inv.quantity < res.quantity_reserved or inv.reserved_quantity < res.quantity_reserved:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot confirm reservation: inventory would become negative. "
                        f"Quantity: {inv.quantity}, Reserved: {inv.reserved_quantity}, "
                        f"Reservation: {res.quantity_reserved}."
                    ),
                )

            # Decrement both physical quantity and reserved_quantity exactly once
            inv.quantity -= res.quantity_reserved
            inv.reserved_quantity -= res.quantity_reserved
            res.status = "CONFIRMED"

            self.db.commit()
            self.db.refresh(res)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type="RESERVATION_CONFIRMED",
            actor_id=actor.user_id if actor else None,
            actor_role=actor.role if actor else None,
            entity_type="RESERVATION",
            entity_id=res.reservation_id,
            location_id=alloc.source_location_id,
            details={
                "allocation_id": alloc.allocation_id,
                "quantity_confirmed": str(res.quantity_reserved),
                "previous_status": "ACTIVE",
                "new_status": "CONFIRMED",
            },
        )

        return res

    def list_by_allocation(self, allocation_id: int, actor: Optional[User] = None) -> List[StockReservation]:
        alloc = self.db.query(OrderAllocation).filter(OrderAllocation.allocation_id == allocation_id).first()
        if alloc and actor is not None and actor.role != "ADMIN":
            if actor.role in ("WAREHOUSE_MANAGER", "WAREHOUSE_WORKER"):
                if actor.location_id is None or actor.location_id != alloc.source_location_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: allocation belongs to a different warehouse.",
                    )
            elif actor.role == "SHOP_OWNER":
                order_item = self.db.query(OrderItem).filter_by(order_item_id=alloc.order_item_id).first()
                order = self.db.query(Order).filter_by(order_id=order_item.order_id).first() if order_item else None
                if not order or actor.location_id != order.shop_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: allocation belongs to a different shop.",
                    )
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        return self.repo.list_by_allocation(allocation_id)

    def list_active(
        self,
        skip: int = 0,
        limit: int = 50,
        actor: Optional[User] = None,
    ) -> List[StockReservation]:
        if actor is None or actor.role == "ADMIN":
            return self.repo.list_active(skip=skip, limit=limit)

        if actor.role == "WAREHOUSE_MANAGER":
            if actor.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse manager is not assigned to a warehouse.",
                )
            return (
                self.db.query(StockReservation)
                .join(OrderAllocation, StockReservation.allocation_id == OrderAllocation.allocation_id)
                .filter(
                    StockReservation.status == "ACTIVE",
                    OrderAllocation.source_location_id == actor.location_id,
                )
                .offset(skip)
                .limit(limit)
                .all()
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to active reservations list.",
        )
