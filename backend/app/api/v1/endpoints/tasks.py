from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.worker_task import (
    WorkerTaskCreateRequest,
    WorkerTaskProgressUpdate,
    WorkerTaskResponse,
    WorkerTaskStatusUpdate,
)
from app.services.worker_task_service import WorkerTaskService

router = APIRouter()


@router.post("/", response_model=WorkerTaskResponse, status_code=status.HTTP_201_CREATED, summary="Create & Assign Worker Task")
def create_task(
    req: WorkerTaskCreateRequest,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    service = WorkerTaskService(db)
    return service.create_task(req, manager=current_user)


@router.get("/", response_model=List[WorkerTaskResponse], summary="List Tasks for Current User")
def list_my_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    warehouse_id: Optional[int] = Query(None),
    worker_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkerTaskService(db)
    return service.list_tasks(
        actor=current_user,
        status_filter=status_filter,
        warehouse_id=warehouse_id,
        worker_id=worker_id,
    )


@router.get("/{task_id}", response_model=WorkerTaskResponse, summary="Get Task Detail")
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkerTaskService(db)
    return service.get_task_by_id(task_id, actor=current_user)


@router.patch("/{task_id}/items/{task_item_id}/progress", response_model=WorkerTaskResponse, summary="Update Task Item Progress")
def update_task_progress(
    task_id: int,
    task_item_id: int,
    req: WorkerTaskProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkerTaskService(db)
    return service.update_task_progress(task_id, task_item_id, req.completed_quantity, actor=current_user)


@router.patch("/{task_id}/status", response_model=WorkerTaskResponse, summary="Update Task Status")
def update_task_status(
    task_id: int,
    req: WorkerTaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the status of a worker task with ownership, warehouse, and transition validation."""
    service = WorkerTaskService(db)
    return service.update_task_status_controlled(task_id, req.status, actor=current_user)
