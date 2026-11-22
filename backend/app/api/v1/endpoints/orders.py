from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.order import OrderCreateRequest, OrderResponse
from app.services.order_service import OrderService

router = APIRouter()


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, summary="Create Replenishment Order")
def create_order(
    req: OrderCreateRequest,
    current_user: User = Depends(require_roles("SHOP_OWNER", "ADMIN")),
    db: Session = Depends(get_db),
):
    """
    Create a replenishment order for a shop:
    - Initial order directed to shop's preferred warehouse.
    - Status initialized to PENDING with zero allocation.
    """
    service = OrderService(db)
    return service.create_order(current_user, req)


@router.get("/", response_model=List[OrderResponse], summary="List Orders")
def list_orders(
    shop_id: Optional[int] = None,
    order_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List orders with status filter."""
    service = OrderService(db)
    return service.list(current_user, shop_id=shop_id, status=order_status, skip=skip, limit=limit)


@router.get("/{order_id}", response_model=OrderResponse, summary="Get Order Details")
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve order details with requested and allocated quantities."""
    service = OrderService(db)
    return service.get_by_id(current_user, order_id)


@router.post("/{order_id}/cancel", response_model=OrderResponse, summary="Cancel Order")
def cancel_order(
    order_id: int,
    current_user: User = Depends(require_roles("SHOP_OWNER", "ADMIN")),
    db: Session = Depends(get_db),
):
    """Cancel a pending or processing order."""
    service = OrderService(db)
    return service.cancel_order(current_user, order_id)
