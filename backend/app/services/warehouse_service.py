from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.location import Location
from app.models.shop_warehouse import ShopWarehouse
from app.repositories.location_repository import LocationRepository, ShopWarehouseRepository
from app.schemas.location import ShopWarehouseCreate


class WarehouseService:
    def __init__(self, db: Session):
        self.db = db
        self.loc_repo = LocationRepository(db)
        self.sw_repo = ShopWarehouseRepository(db)

    def _validate_shop_and_warehouse(self, shop_id: int, warehouse_id: int):
        if shop_id == warehouse_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shop and warehouse cannot be the same location.")
        shop = self.loc_repo.get_by_id(shop_id)
        if not shop or shop.location_type != "SHOP":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Location {shop_id} is not a valid SHOP.")
        wh = self.loc_repo.get_by_id(warehouse_id)
        if not wh or wh.location_type not in ("MAIN_WAREHOUSE", "SUB_WAREHOUSE"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Location {warehouse_id} is not a valid WAREHOUSE.")

    def add_relationship(self, shop_id: int, req: ShopWarehouseCreate) -> ShopWarehouse:
        self._validate_shop_and_warehouse(shop_id, req.warehouse_id)

        # Handle preferred warehouse exclusivity per shop
        if req.is_preferred:
            existing_preferred = self.sw_repo.get_preferred_warehouse(shop_id)
            if existing_preferred and existing_preferred.warehouse_id != req.warehouse_id:
                existing_preferred.is_preferred = False
                self.db.add(existing_preferred)

        rel = self.sw_repo.get_relationship(shop_id, req.warehouse_id)
        if rel:
            rel.is_preferred = req.is_preferred
            rel.priority = req.priority
        else:
            rel = ShopWarehouse(
                shop_id=shop_id,
                warehouse_id=req.warehouse_id,
                is_preferred=req.is_preferred,
                priority=req.priority,
            )
        return self.sw_repo.create_or_update(rel)

    def set_preferred_warehouse(self, shop_id: int, warehouse_id: int) -> ShopWarehouse:
        self._validate_shop_and_warehouse(shop_id, warehouse_id)

        # Clear existing preferred
        current_links = self.sw_repo.get_links_for_shop(shop_id)
        for link in current_links:
            if link.warehouse_id != warehouse_id and link.is_preferred:
                link.is_preferred = False
                self.db.add(link)

        target = self.sw_repo.get_relationship(shop_id, warehouse_id)
        if not target:
            target = ShopWarehouse(
                shop_id=shop_id,
                warehouse_id=warehouse_id,
                is_preferred=True,
                priority=1,
            )
        else:
            target.is_preferred = True

        return self.sw_repo.create_or_update(target)

    def get_preferred_warehouse(self, shop_id: int) -> Optional[ShopWarehouse]:
        return self.sw_repo.get_preferred_warehouse(shop_id)

    def get_alternative_warehouses(self, shop_id: int) -> List[ShopWarehouse]:
        links = self.sw_repo.get_links_for_shop(shop_id)
        return [l for l in links if not l.is_preferred]

    def list_shop_warehouses(self, shop_id: int) -> List[ShopWarehouse]:
        return self.sw_repo.get_links_for_shop(shop_id)

    def list_warehouse_shops(self, warehouse_id: int) -> List[ShopWarehouse]:
        return self.sw_repo.get_links_for_warehouse(warehouse_id)
