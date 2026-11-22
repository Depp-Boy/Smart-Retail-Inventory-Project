from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProductRepository(db)

    def create(self, req: ProductCreate) -> Product:
        if req.price < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Price cannot be negative.")
        if req.cost_price is not None and req.cost_price < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cost price cannot be negative.")
        if req.reorder_threshold < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reorder threshold cannot be negative.")

        if req.sku:
            existing = self.repo.get_by_sku(req.sku.strip())
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product with SKU '{req.sku}' already exists.")

        product = Product(
            product_name=req.product_name.strip(),
            category=req.category.strip() if req.category else None,
            unit=req.unit.strip(),
            price=req.price,
            reorder_threshold=req.reorder_threshold,
            sku=req.sku.strip() if req.sku else None,
            cost_price=req.cost_price,
            description=req.description.strip() if req.description else None,
            storage_conditions=req.storage_conditions.strip() if req.storage_conditions else None,
        )
        return self.repo.create(product)

    def get_by_id(self, product_id: int) -> Product:
        p = self.repo.get_by_id(product_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found.")
        return p

    def list(self, category: Optional[str] = None, search: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[Product]:
        return self.repo.list(category=category, search=search, skip=skip, limit=limit)

    def update(self, product_id: int, req: ProductUpdate) -> Product:
        p = self.get_by_id(product_id)
        if req.price is not None:
            if req.price < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Price cannot be negative.")
            p.price = req.price
        if req.cost_price is not None:
            if req.cost_price < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cost price cannot be negative.")
            p.cost_price = req.cost_price
        if req.reorder_threshold is not None:
            if req.reorder_threshold < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reorder threshold cannot be negative.")
            p.reorder_threshold = req.reorder_threshold
        if req.sku is not None:
            sku_val = req.sku.strip() if req.sku else None
            if sku_val and sku_val != p.sku:
                existing = self.repo.get_by_sku(sku_val)
                if existing:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"SKU '{sku_val}' is already in use.")
            p.sku = sku_val
        if req.product_name is not None:
            p.product_name = req.product_name.strip()
        if req.category is not None:
            p.category = req.category.strip() if req.category else None
        if req.unit is not None:
            p.unit = req.unit.strip()
        if req.description is not None:
            p.description = req.description.strip() if req.description else None
        if req.storage_conditions is not None:
            p.storage_conditions = req.storage_conditions.strip() if req.storage_conditions else None
        return self.repo.update(p)
