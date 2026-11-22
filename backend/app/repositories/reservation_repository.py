from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.reservation import StockReservation


class ReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, reservation_id: int, lock: bool = False) -> Optional[StockReservation]:
        query = self.db.query(StockReservation).filter(StockReservation.reservation_id == reservation_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def get_by_allocation(self, allocation_id: int, lock: bool = False) -> Optional[StockReservation]:
        query = self.db.query(StockReservation).filter(StockReservation.allocation_id == allocation_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def list_by_allocation(self, allocation_id: int) -> List[StockReservation]:
        return self.db.query(StockReservation).filter(StockReservation.allocation_id == allocation_id).all()

    def list_active(self, skip: int = 0, limit: int = 50) -> List[StockReservation]:
        return (
            self.db.query(StockReservation)
            .filter(StockReservation.status == "ACTIVE")
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, reservation: StockReservation) -> StockReservation:
        self.db.add(reservation)
        self.db.commit()
        self.db.refresh(reservation)
        return reservation

    def update(self, reservation: StockReservation) -> StockReservation:
        self.db.commit()
        self.db.refresh(reservation)
        return reservation
