from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.repositories.location_repository import LocationRepository
from app.schemas.location import LocationResponse, ShopWarehouseCreate, ShopWarehouseResponse
from app.services.warehouse_service import WarehouseService

router = APIRouter()


@router.get("/", response_model=List[LocationResponse], summary="List All Warehouses")
def list_all_warehouses(db: Session = Depends(get_db)):
    """List all registered warehouse locations."""
    repo = LocationRepository(db)
    main_wh = repo.list(location_type="MAIN_WAREHOUSE")
    sub_wh = repo.list(location_type="SUB_WAREHOUSE")
    return main_wh + sub_wh


@router.get("/shops/{shop_id}/warehouses", response_model=List[ShopWarehouseResponse], summary="List Warehouses for Shop")
def list_warehouses_for_shop(shop_id: int, db: Session = Depends(get_db)):
    """List all warehouses linked to a shop."""
    service = WarehouseService(db)
    return service.list_shop_warehouses(shop_id)


@router.get("/shops/{shop_id}/preferred-warehouse", response_model=ShopWarehouseResponse, summary="Get Preferred Warehouse")
def get_preferred_warehouse(shop_id: int, db: Session = Depends(get_db)):
    """Get the single preferred fulfillment warehouse for a shop."""
    service = WarehouseService(db)
    preferred = service.get_preferred_warehouse(shop_id)
    if not preferred:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No preferred warehouse set for this shop.")
    return preferred


@router.get("/shops/{shop_id}/alternative-warehouses", response_model=List[ShopWarehouseResponse], summary="Get Alternative Warehouses")
def get_alternative_warehouses(shop_id: int, db: Session = Depends(get_db)):
    """Get all non-preferred alternative warehouses linked to a shop."""
    service = WarehouseService(db)
    return service.get_alternative_warehouses(shop_id)


@router.post("/shops/{shop_id}/warehouses", response_model=ShopWarehouseResponse, status_code=status.HTTP_201_CREATED, summary="Add Warehouse Association")
def add_warehouse_link(
    shop_id: int,
    req: ShopWarehouseCreate,
    current_user: User = Depends(require_roles("ADMIN", "SHOP_OWNER")),
    db: Session = Depends(get_db),
):
    """Associate a warehouse with a shop, respecting preferred exclusivity."""
    service = WarehouseService(db)
    return service.add_relationship(shop_id, req)


@router.put("/shops/{shop_id}/preferred-warehouse/{warehouse_id}", response_model=ShopWarehouseResponse, summary="Set Preferred Warehouse")
def set_preferred_warehouse(
    shop_id: int,
    warehouse_id: int,
    current_user: User = Depends(require_roles("ADMIN", "SHOP_OWNER")),
    db: Session = Depends(get_db),
):
    """Set or switch the primary preferred warehouse for a shop."""
    service = WarehouseService(db)
    return service.set_preferred_warehouse(shop_id, warehouse_id)


@router.get("/warehouses/{warehouse_id}/shops", response_model=List[ShopWarehouseResponse], summary="List Shops for Warehouse")
def list_shops_for_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    """List all shops fulfilled by a warehouse."""
    service = WarehouseService(db)
    return service.list_warehouse_shops(warehouse_id)
