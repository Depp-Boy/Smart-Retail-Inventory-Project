from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.location import Location
from app.models.shop_warehouse import ShopWarehouse


class LocationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, location_id: int) -> Optional[Location]:
        return self.db.query(Location).filter(Location.location_id == location_id).first()

    def list(self, location_type: Optional[str] = None, search: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[Location]:
        query = self.db.query(Location)
        if location_type:
            query = query.filter(Location.location_type == location_type.upper())
        if search:
            query = query.filter(Location.location_name.ilike(f"%{search}%"))
        return query.offset(skip).limit(limit).all()

    def create(self, location: Location) -> Location:
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location

    def update(self, location: Location) -> Location:
        self.db.commit()
        self.db.refresh(location)
        return location


class ShopWarehouseRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_links_for_shop(self, shop_id: int) -> List[ShopWarehouse]:
        return self.db.query(ShopWarehouse).filter(ShopWarehouse.shop_id == shop_id).all()

    def get_links_for_warehouse(self, warehouse_id: int) -> List[ShopWarehouse]:
        return self.db.query(ShopWarehouse).filter(ShopWarehouse.warehouse_id == warehouse_id).all()

    def get_preferred_warehouse(self, shop_id: int) -> Optional[ShopWarehouse]:
        return (
            self.db.query(ShopWarehouse)
            .filter(ShopWarehouse.shop_id == shop_id, ShopWarehouse.is_preferred.is_(True))
            .first()
        )

    def get_relationship(self, shop_id: int, warehouse_id: int) -> Optional[ShopWarehouse]:
        return (
            self.db.query(ShopWarehouse)
            .filter(ShopWarehouse.shop_id == shop_id, ShopWarehouse.warehouse_id == warehouse_id)
            .first()
        )

    def create_or_update(self, link: ShopWarehouse) -> ShopWarehouse:
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def delete(self, link: ShopWarehouse) -> None:
        self.db.delete(link)
        self.db.commit()
