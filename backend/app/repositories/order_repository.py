from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.order import Order


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, order_id: int) -> Optional[Order]:
        return self.db.query(Order).filter(Order.order_id == order_id).first()

    def list(self, shop_id: Optional[int] = None, status: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[Order]:
        query = self.db.query(Order)
        if shop_id:
            query = query.filter(Order.shop_id == shop_id)
        if status:
            query = query.filter(Order.status == status.upper())
        return query.order_by(Order.order_date.desc()).offset(skip).limit(limit).all()

    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def update(self, order: Order) -> Order:
        self.db.commit()
        self.db.refresh(order)
        return order
