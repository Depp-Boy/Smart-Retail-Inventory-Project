from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.inventory import Inventory
from app.models.product import Product


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, location_id: int, product_id: int, lock: bool = False) -> Optional[Inventory]:
        query = self.db.query(Inventory).filter(
            Inventory.location_id == location_id,
            Inventory.product_id == product_id,
        )
        if lock:
            query = query.with_for_update()
        return query.first()

    def list_by_location(
        self,
        location_id: int,
        low_stock_only: bool = False,
        out_of_stock_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Inventory]:
        query = self.db.query(Inventory).filter(Inventory.location_id == location_id)
        if low_stock_only:
            query = query.join(Product, Inventory.product_id == Product.product_id).filter(
                Inventory.quantity <= Product.reorder_threshold
            )
        if out_of_stock_only:
            query = query.filter((Inventory.quantity - Inventory.reserved_quantity) <= 0)
        return query.offset(skip).limit(limit).all()

    def list_by_product(self, product_id: int) -> List[Inventory]:
        return self.db.query(Inventory).filter(Inventory.product_id == product_id).all()

    def list_all(self, skip: int = 0, limit: int = 50) -> List[Inventory]:
        return self.db.query(Inventory).offset(skip).limit(limit).all()

    def upsert(self, inventory: Inventory) -> Inventory:
        self.db.add(inventory)
        self.db.commit()
        self.db.refresh(inventory)
        return inventory

