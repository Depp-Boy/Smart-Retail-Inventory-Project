from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.sale import Sale


class SaleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, sale_id: int) -> Optional[Sale]:
        return self.db.query(Sale).filter(Sale.sale_id == sale_id).first()

    def list(self, shop_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> List[Sale]:
        query = self.db.query(Sale)
        if shop_id:
            query = query.filter(Sale.shop_id == shop_id)
        return query.order_by(Sale.sale_date.desc()).offset(skip).limit(limit).all()

    def create(self, sale: Sale) -> Sale:
        self.db.add(sale)
        self.db.commit()
        self.db.refresh(sale)
        return sale

    def update(self, sale: Sale) -> Sale:
        self.db.commit()
        self.db.refresh(sale)
        return sale
