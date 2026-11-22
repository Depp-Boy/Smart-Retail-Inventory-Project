from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.product import Product


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Optional[Product]:
        return self.db.query(Product).filter(Product.product_id == product_id).first()

    def get_by_sku(self, sku: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.sku == sku).first()

    def list(self, category: Optional[str] = None, search: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[Product]:
        query = self.db.query(Product)
        if category:
            query = query.filter(Product.category == category)
        if search:
            query = query.filter(
                (Product.product_name.ilike(f"%{search}%")) | (Product.sku.ilike(f"%{search}%"))
            )
        return query.offset(skip).limit(limit).all()

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update(self, product: Product) -> Product:
        self.db.commit()
        self.db.refresh(product)
        return product
