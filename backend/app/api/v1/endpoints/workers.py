from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import UserProfileResponse
from app.schemas.worker_task import WorkerTaskResponse
from app.services.worker_task_service import WorkerTaskService

router = APIRouter()


@router.get("/", response_model=List[UserProfileResponse], summary="List Warehouse Workers")
def list_workers(
    warehouse_id: Optional[int] = Query(None, description="Filter workers by warehouse location"),
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(User.role == "WAREHOUSE_WORKER")
    if warehouse_id:
        query = query.filter(User.location_id == warehouse_id)
    return query.all()


@router.get("/{worker_id}/tasks", response_model=List[WorkerTaskResponse], summary="List Tasks for Worker")
def list_worker_tasks(
    worker_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkerTaskService(db)
    return service.list_tasks_for_worker(worker_id, actor=current_user, status=status_filter)


@router.get("/warehouse/{warehouse_id}/tasks", response_model=List[WorkerTaskResponse], summary="List Tasks for Warehouse")
def list_warehouse_tasks(
    warehouse_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    service = WorkerTaskService(db)
    return service.list_tasks_for_warehouse(warehouse_id, actor=current_user, status=status_filter)
