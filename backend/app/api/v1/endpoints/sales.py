from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.sale import SaleCreateRequest, SaleResponse
from app.services.sale_service import SaleService

router = APIRouter()


@router.post("/", response_model=SaleResponse, status_code=status.HTTP_201_CREATED, summary="Record POS Sale")
def record_sale(
    req: SaleCreateRequest,
    current_user: User = Depends(require_roles("SHOP_OWNER", "ADMIN")),
    db: Session = Depends(get_db),
):
    """
    Record a retail sale:
    - Validates stock availability with row-level locks.
    - Atomically updates inventory.
    - Server calculates subtotal and total based on validated monetary values.
    """
    service = SaleService(db)
    return service.record_sale(current_user, req)


@router.get("/", response_model=List[SaleResponse], summary="List Sales")
def list_sales(
    shop_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_roles("SHOP_OWNER", "ADMIN")),
    db: Session = Depends(get_db),
):
    """List sales history for the authenticated shop."""
    service = SaleService(db)
    return service.list(current_user, shop_id=shop_id, skip=skip, limit=limit)


@router.get("/{sale_id}", response_model=SaleResponse, summary="Get Sale Details")
def get_sale(
    sale_id: int,
    current_user: User = Depends(require_roles("SHOP_OWNER", "ADMIN")),
    db: Session = Depends(get_db),
):
    """Retrieve full sale details with line items."""
    service = SaleService(db)
    return service.get_by_id(current_user, sale_id)


@router.post("/{sale_id}/cancel", response_model=SaleResponse, summary="Cancel Sale")
def cancel_sale(
    sale_id: int,
    current_user: User = Depends(require_roles("SHOP_OWNER", "ADMIN")),
    db: Session = Depends(get_db),
):
    """Cancel sale and idempotently restore inventory stock."""
    service = SaleService(db)
    return service.cancel_or_refund_sale(current_user, sale_id, "CANCELLED")


@router.post("/{sale_id}/refund", response_model=SaleResponse, summary="Refund Sale")
def refund_sale(
    sale_id: int,
    current_user: User = Depends(require_roles("SHOP_OWNER", "ADMIN")),
    db: Session = Depends(get_db),
):
    """Refund sale and idempotently restore inventory stock."""
    service = SaleService(db)
    return service.cancel_or_refund_sale(current_user, sale_id, "REFUNDED")
