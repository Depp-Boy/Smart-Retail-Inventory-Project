from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
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
        search: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = 50,
    ) -> List[Inventory]:
        query = (
            self.db.query(Inventory)
            .options(joinedload(Inventory.product))
            .filter(Inventory.location_id == location_id)
        )
        needs_product_join = low_stock_only or bool(search and search.strip())
        if needs_product_join:
            query = query.join(Product, Inventory.product_id == Product.product_id)

        if low_stock_only:
            query = query.filter(
                (Inventory.quantity - Inventory.reserved_quantity) <= Product.reorder_threshold
            )
        if out_of_stock_only:
            query = query.filter((Inventory.quantity - Inventory.reserved_quantity) <= 0)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Product.product_name.ilike(pattern),
                    Product.sku.ilike(pattern),
                    Product.category.ilike(pattern),
                )
            )

        query = query.order_by(Inventory.inventory_id.asc()).offset(skip)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def list_by_product(self, product_id: int) -> List[Inventory]:
        return self.db.query(Inventory).filter(Inventory.product_id == product_id).all()

    def list_all(
        self,
        location_id: Optional[int] = None,
        low_stock_only: bool = False,
        out_of_stock_only: bool = False,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Inventory]:
        query = self.db.query(Inventory).options(joinedload(Inventory.product))
        if location_id is not None:
            query = query.filter(Inventory.location_id == location_id)

        needs_product_join = low_stock_only or bool(search and search.strip())
        if needs_product_join:
            query = query.join(Product, Inventory.product_id == Product.product_id)

        if low_stock_only:
            query = query.filter(
                (Inventory.quantity - Inventory.reserved_quantity) <= Product.reorder_threshold
            )
        if out_of_stock_only:
            query = query.filter((Inventory.quantity - Inventory.reserved_quantity) <= 0)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Product.product_name.ilike(pattern),
                    Product.sku.ilike(pattern),
                    Product.category.ilike(pattern),
                )
            )

        return query.order_by(Inventory.inventory_id.asc()).offset(skip).limit(limit).all()

    def upsert(self, inventory: Inventory) -> Inventory:
        self.db.add(inventory)
        self.db.commit()
        self.db.refresh(inventory)
        return inventory
