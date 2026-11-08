from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.inventory import Inventory
from app.models.product import Product
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.inventory import InventorySummaryResponse


class InventoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InventoryRepository(db)

    def list_by_location(
        self,
        location_id: int,
        low_stock_only: bool = False,
        out_of_stock_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Inventory]:
        return self.repo.list_by_location(
            location_id=location_id,
            low_stock_only=low_stock_only,
            out_of_stock_only=out_of_stock_only,
            skip=skip,
            limit=limit,
        )

    def get_summary(self, location_id: int) -> InventorySummaryResponse:
        records = self.repo.list_by_location(location_id=location_id, skip=0, limit=10000)
        total_items = len(records)
        total_phys = sum(r.quantity for r in records) if records else Decimal("0.00")
        total_res = sum(r.reserved_quantity for r in records) if records else Decimal("0.00")
        total_avail = float(total_phys - total_res)

        low_stock_count = 0
        out_of_stock_count = 0

        for r in records:
            avail = float(r.quantity - r.reserved_quantity)
            if avail <= 0:
                out_of_stock_count += 1
            if r.product and r.quantity <= r.product.reorder_threshold:
                low_stock_count += 1

        return InventorySummaryResponse(
            location_id=location_id,
            total_products_count=total_items,
            total_physical_quantity=total_phys,
            total_reserved_quantity=total_res,
            total_available_quantity=total_avail,
            low_stock_count=low_stock_count,
            out_of_stock_count=out_of_stock_count,
        )

    def adjust_stock_controlled(
        self,
        location_id: int,
        product_id: int,
        delta: Decimal,
    ) -> Inventory:
        """
        Controlled transactional stock adjustment with row-level locking.
        Internal service method — never exposed as unrestricted direct API.
        """
        inv = self.repo.get(location_id=location_id, product_id=product_id, lock=True)
        if not inv:
            if delta < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deduct stock for non-existent inventory item.")
            inv = Inventory(
                location_id=location_id,
                product_id=product_id,
                quantity=delta,
                reserved_quantity=Decimal("0.00"),
            )
        else:
            new_qty = inv.quantity + delta
            if new_qty < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Physical quantity cannot become negative.")
            if new_qty < inv.reserved_quantity:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Physical quantity cannot be less than reserved quantity.")
            inv.quantity = new_qty

        return self.repo.upsert(inv)
