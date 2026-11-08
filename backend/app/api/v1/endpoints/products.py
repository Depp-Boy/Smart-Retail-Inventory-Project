from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter()


@router.get("/", response_model=List[ProductResponse], summary="List Products")
def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List products with optional search and category filter."""
    service = ProductService(db)
    return service.list(category=category, search=search, skip=skip, limit=limit)


@router.get("/{product_id}", response_model=ProductResponse, summary="Get Product by ID")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieve product details by ID."""
    service = ProductService(db)
    return service.get_by_id(product_id)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, summary="Create Product")
def create_product(
    req: ProductCreate,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    """Create a new product (restricted to ADMIN and WAREHOUSE_MANAGER)."""
    service = ProductService(db)
    return service.create(req)


@router.put("/{product_id}", response_model=ProductResponse, summary="Update Product")
def update_product(
    product_id: int,
    req: ProductUpdate,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    """Update product details (restricted to ADMIN and WAREHOUSE_MANAGER)."""
    service = ProductService(db)
    return service.update(product_id, req)
