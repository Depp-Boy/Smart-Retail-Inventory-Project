from decimal import Decimal
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.allocation import OrderAllocation
from app.models.dispatch import DispatchItem
from app.models.order import OrderItem


class AllocationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, allocation_id: int, lock: bool = False) -> Optional[OrderAllocation]:
        query = self.db.query(OrderAllocation).filter(OrderAllocation.allocation_id == allocation_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def list_by_order(self, order_id: int) -> List[OrderAllocation]:
        return (
            self.db.query(OrderAllocation)
            .join(OrderItem, OrderAllocation.order_item_id == OrderItem.order_item_id)
            .filter(OrderItem.order_id == order_id)
            .all()
        )

    def list_by_order_item(self, order_item_id: int) -> List[OrderAllocation]:
        return self.db.query(OrderAllocation).filter(OrderAllocation.order_item_id == order_item_id).all()

    def list_by_warehouse(self, warehouse_id: int, status: Optional[str] = None) -> List[OrderAllocation]:
        query = self.db.query(OrderAllocation).filter(OrderAllocation.source_location_id == warehouse_id)
        if status:
            query = query.filter(OrderAllocation.status == status.upper())
        return query.all()

    def get_total_allocated_for_order_item(self, order_item_id: int) -> Decimal:
        val = (
            self.db.query(func.coalesce(func.sum(OrderAllocation.allocated_quantity), 0))
            .filter(
                OrderAllocation.order_item_id == order_item_id,
                OrderAllocation.status != "CANCELLED",
            )
            .scalar()
        )
        return Decimal(str(val))

    def get_total_dispatched_quantity(self, allocation_id: int) -> Decimal:
        val = (
            self.db.query(func.coalesce(func.sum(DispatchItem.quantity), 0))
            .filter(DispatchItem.allocation_id == allocation_id)
            .scalar()
        )
        return Decimal(str(val))

    def create(self, allocation: OrderAllocation) -> OrderAllocation:
        self.db.add(allocation)
        self.db.commit()
        self.db.refresh(allocation)
        return allocation

    def update(self, allocation: OrderAllocation) -> OrderAllocation:
        self.db.commit()
        self.db.refresh(allocation)
        return allocation
