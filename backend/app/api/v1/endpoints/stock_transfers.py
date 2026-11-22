from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.stock_transfer import (
    StockTransferCreateRequest,
    StockTransferResponse,
    StockTransferStatusUpdate,
)
from app.services.stock_transfer_service import StockTransferService

router = APIRouter()


@router.get("/", response_model=List[StockTransferResponse], summary="List Stock Transfers")
def list_stock_transfers(
    source_location_id: Optional[int] = Query(None),
    destination_location_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = StockTransferService(db)
    return service.list(
        source_id=source_location_id,
        destination_id=destination_location_id,
        status=status_filter,
    )


@router.post("/", response_model=StockTransferResponse, status_code=status.HTTP_201_CREATED, summary="Create Stock Transfer")
def create_stock_transfer(
    req: StockTransferCreateRequest,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER", "SHOP_OWNER")),
    db: Session = Depends(get_db),
):
    service = StockTransferService(db)
    return service.create_transfer(req, actor=current_user)


@router.get("/{transfer_id}", response_model=StockTransferResponse, summary="Get Stock Transfer Detail")
def get_stock_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = StockTransferService(db)
    tr = service.repo.get_by_id(transfer_id)
    if not tr:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found.")
    return tr


@router.patch("/{transfer_id}/status", response_model=StockTransferResponse, summary="Update Stock Transfer Status")
def update_transfer_status(
    transfer_id: int,
    req: StockTransferStatusUpdate,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    service = StockTransferService(db)
    return service.update_status(transfer_id, req, actor=current_user)
