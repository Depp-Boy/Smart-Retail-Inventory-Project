from decimal import Decimal
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.dispatch import Dispatch, DispatchItem


class DispatchRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, dispatch_id: int, lock: bool = False) -> Optional[Dispatch]:
        query = self.db.query(Dispatch).filter(Dispatch.dispatch_id == dispatch_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def get_by_code(self, dispatch_code: str) -> Optional[Dispatch]:
        return self.db.query(Dispatch).filter(Dispatch.dispatch_code == dispatch_code).first()

    def list_by_order(self, order_id: int) -> List[Dispatch]:
        return self.db.query(Dispatch).filter(Dispatch.order_id == order_id).all()

    def list_by_warehouse(self, warehouse_id: int, status: Optional[str] = None) -> List[Dispatch]:
        query = self.db.query(Dispatch).filter(Dispatch.source_location_id == warehouse_id)
        if status:
            query = query.filter(Dispatch.status == status.upper())
        return query.order_by(Dispatch.created_at.desc()).all()

    def get_dispatched_quantity_for_allocation(self, allocation_id: int) -> Decimal:
        val = (
            self.db.query(func.coalesce(func.sum(DispatchItem.quantity), 0))
            .filter(DispatchItem.allocation_id == allocation_id)
            .scalar()
        )
        return Decimal(str(val))

    def create(self, dispatch: Dispatch) -> Dispatch:
        self.db.add(dispatch)
        self.db.commit()
        self.db.refresh(dispatch)
        return dispatch

    def update(self, dispatch: Dispatch) -> Dispatch:
        self.db.commit()
        self.db.refresh(dispatch)
        return dispatch
