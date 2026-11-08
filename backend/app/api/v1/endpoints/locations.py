from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.location import LocationCreate, LocationResponse, LocationUpdate
from app.services.location_service import LocationService

router = APIRouter()


@router.get("/", response_model=List[LocationResponse], summary="List Locations")
def list_locations(
    location_type: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List retail shops and warehouses with optional search and type filter."""
    service = LocationService(db)
    return service.list(location_type=location_type, search=search, skip=skip, limit=limit)


@router.get("/shops", response_model=List[LocationResponse], summary="List Shops")
def list_shops(
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all retail shop locations."""
    service = LocationService(db)
    return service.list(location_type="SHOP", search=search, skip=skip, limit=limit)


@router.get("/warehouses", response_model=List[LocationResponse], summary="List Warehouses")
def list_warehouses(
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all warehouse locations (MAIN_WAREHOUSE and SUB_WAREHOUSE)."""
    service = LocationService(db)
    return [l for l in service.list(search=search, skip=skip, limit=limit) if l.location_type in ("MAIN_WAREHOUSE", "SUB_WAREHOUSE")]


@router.get("/{location_id}", response_model=LocationResponse, summary="Get Location Details")
def get_location(location_id: int, db: Session = Depends(get_db)):
    """Retrieve details of a location by ID."""
    service = LocationService(db)
    return service.get_by_id(location_id)


@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED, summary="Create Location")
def create_location(
    req: LocationCreate,
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    """Create a new shop or warehouse (restricted to ADMIN)."""
    service = LocationService(db)
    return service.create(req)


@router.put("/{location_id}", response_model=LocationResponse, summary="Update Location")
def update_location(
    location_id: int,
    req: LocationUpdate,
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    """Update location details (restricted to ADMIN)."""
    service = LocationService(db)
    return service.update(location_id, req)
