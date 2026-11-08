from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.allocation import (
    AllocationCreateRequest,
    AllocationResponse,
    OrderAllocationSummaryResponse,
)
from app.services.allocation_service import AllocationService

router = APIRouter()


@router.get("/", summary="Allocations Module Status")
def allocations_status():
    return {"module": "allocations", "status": "active", "version": "v1"}


@router.post("/", response_model=AllocationResponse, status_code=status.HTTP_201_CREATED, summary="Allocate Order Item")
def allocate_order_item(
    req: AllocationCreateRequest,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER", "SHOP_OWNER")),
    db: Session = Depends(get_db),
):
    service = AllocationService(db)
    return service.allocate_order_item(req, actor=current_user)


@router.post("/{allocation_id}/cancel", response_model=AllocationResponse, summary="Cancel Allocation")
def cancel_allocation(
    allocation_id: int,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    service = AllocationService(db)
    return service.cancel_allocation(allocation_id, actor=current_user)


@router.get("/order/{order_id}", response_model=List[AllocationResponse], summary="List Allocations for Order")
def list_allocations_by_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AllocationService(db)
    return service.list_by_order(order_id)


@router.get("/warehouse/{warehouse_id}", response_model=List[AllocationResponse], summary="List Allocations for Warehouse")
def list_allocations_by_warehouse(
    warehouse_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    service = AllocationService(db)
    return service.list_by_warehouse(warehouse_id, status=status_filter)


@router.get("/order/{order_id}/summary", response_model=OrderAllocationSummaryResponse, summary="Order Allocation Summary")
def get_order_allocation_summary(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AllocationService(db)
    return service.get_order_summary(order_id)
