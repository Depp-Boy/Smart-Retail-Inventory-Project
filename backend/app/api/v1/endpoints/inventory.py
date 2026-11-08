from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.inventory import InventoryResponse, InventorySummaryResponse
from app.services.inventory_service import InventoryService

router = APIRouter()


@router.get("/", response_model=List[InventoryResponse], summary="List All Inventory")
def list_all_inventory(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List inventory records across locations."""
    repo = InventoryRepository(db)
    return repo.list_all(skip=skip, limit=limit)


@router.get("/locations/{location_id}", response_model=List[InventoryResponse], summary="View Location Inventory")
def view_location_inventory(
    location_id: int,
    low_stock: bool = Query(False, description="Filter items at or below reorder threshold"),
    out_of_stock: bool = Query(False, description="Filter items with zero or negative available stock"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    View stock levels for a specific shop or warehouse.
    Controlled read-only endpoint — stock adjustments occur only via transactional operations.
    """
    service = InventoryService(db)
    return service.list_by_location(
        location_id=location_id,
        low_stock_only=low_stock,
        out_of_stock_only=out_of_stock,
        skip=skip,
        limit=limit,
    )


@router.get("/locations/{location_id}/summary", response_model=InventorySummaryResponse, summary="Location Inventory Summary")
def get_inventory_summary(
    location_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate KPI summary for stock levels, reserves, low-stock, and stockouts."""
    service = InventoryService(db)
    return service.get_summary(location_id)
