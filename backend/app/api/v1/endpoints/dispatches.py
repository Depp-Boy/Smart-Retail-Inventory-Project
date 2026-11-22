from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.dispatch import DispatchCreateRequest, DispatchResponse, DispatchStatusUpdate
from app.services.dispatch_service import DispatchService

router = APIRouter()


@router.get("/", response_model=List[DispatchResponse], summary="List Dispatches")
def list_dispatches(
    warehouse_id: Optional[int] = Query(None),
    order_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = DispatchService(db)
    if order_id:
        return service.list_by_order(order_id)
    if warehouse_id:
        return service.list_by_warehouse(warehouse_id, status=status_filter)
    if current_user.location_id:
        return service.list_by_warehouse(current_user.location_id, status=status_filter)
    return []


@router.post("/", response_model=DispatchResponse, status_code=status.HTTP_201_CREATED, summary="Create Dispatch")
def create_dispatch(
    req: DispatchCreateRequest,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    service = DispatchService(db)
    return service.create_dispatch(req, actor=current_user)


@router.get("/{dispatch_id}", response_model=DispatchResponse, summary="Get Dispatch Details")
def get_dispatch(
    dispatch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = DispatchService(db)
    dsp = service.repo.get_by_id(dispatch_id)
    if not dsp:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found.")
    return dsp


@router.patch("/{dispatch_id}/status", response_model=DispatchResponse, summary="Update Dispatch Status")
def update_dispatch_status(
    dispatch_id: int,
    req: DispatchStatusUpdate,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER", "WAREHOUSE_WORKER")),
    db: Session = Depends(get_db),
):
    service = DispatchService(db)
    return service.update_status(dispatch_id, req, actor=current_user)

