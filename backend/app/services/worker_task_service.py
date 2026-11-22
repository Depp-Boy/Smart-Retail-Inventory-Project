import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.worker_task import WorkerTask, WorkerTaskItem
from app.repositories.worker_task_repository import WorkerTaskRepository
from app.schemas.worker_task import WorkerTaskCreateRequest
from app.services.audit_service import AuditLogService


class WorkerTaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkerTaskRepository(db)

    def create_task(self, req: WorkerTaskCreateRequest, manager: User) -> WorkerTask:
        if manager.role not in ("ADMIN", "WAREHOUSE_MANAGER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only warehouse managers or admins can create and assign tasks.",
            )

        worker = self.db.query(User).filter(User.user_id == req.assigned_worker_id).first()
        if not worker or worker.role != "WAREHOUSE_WORKER":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user must be a registered WAREHOUSE_WORKER.",
            )

        if not req.allocation_id and not req.dispatch_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task must reference at least an allocation_id or a dispatch_id.",
            )

        task_code = f"TASK-{uuid.uuid4().hex[:8].upper()}"
        task = WorkerTask(
            task_code=task_code,
            assigned_worker_id=req.assigned_worker_id,
            assigned_by_user_id=manager.user_id,
            allocation_id=req.allocation_id,
            dispatch_id=req.dispatch_id,
            task_type=req.task_type.upper(),
            priority=req.priority.upper() if req.priority else "NORMAL",
            status="PENDING",
            due_at=req.due_at,
            instructions=req.instructions,
        )
        self.db.add(task)
        self.db.flush()

        for item_in in req.items:
            task_item = WorkerTaskItem(
                task_id=task.task_id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                completed_quantity=Decimal("0.00"),
            )
            self.db.add(task_item)

        self.db.commit()
        self.db.refresh(task)

        AuditLogService.log_event(
            event_type="WORKER_TASK_CREATED",
            actor_id=manager.user_id,
            entity_type="worker_tasks",
            entity_id=task.task_id,
            details={"task_type": task.task_type, "assigned_to": worker.user_id},
        )

        return task

    def update_task_progress(
        self,
        task_id: int,
        task_item_id: int,
        completed_quantity: Decimal,
        actor: User,
    ) -> WorkerTask:
        task = self.repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        # Worker isolation: Worker can only update their own task
        if actor.role == "WAREHOUSE_WORKER" and task.assigned_worker_id != actor.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workers cannot modify another worker's tasks.",
            )

        item = self.repo.get_item(task_item_id)
        if not item or item.task_id != task_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task item not found.")

        if completed_quantity > item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Completed quantity ({completed_quantity}) cannot exceed assigned quantity ({item.quantity}).",
            )
        if completed_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Completed quantity cannot be negative.",
            )

        item.completed_quantity = completed_quantity
        self.db.flush()

        # Update overall task status
        all_completed = all(i.completed_quantity >= i.quantity for i in task.items)
        if all_completed and len(task.items) > 0:
            task.status = "COMPLETED"
            task.completed_at = datetime.now(timezone.utc)
        elif any(i.completed_quantity > 0 for i in task.items):
            task.status = "IN_PROGRESS"

        self.db.commit()
        self.db.refresh(task)
        return task

    def list_tasks_for_worker(self, worker_id: int, actor: User, status: Optional[str] = None) -> List[WorkerTask]:
        if actor.role == "WAREHOUSE_WORKER" and actor.user_id != worker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workers can retrieve only their own assigned tasks.",
            )
        return self.repo.list_by_worker(worker_id, status=status)

    def list_tasks_for_warehouse(self, warehouse_id: int, actor: User, status: Optional[str] = None) -> List[WorkerTask]:
        if actor.role == "WAREHOUSE_MANAGER" and actor.location_id != warehouse_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can view tasks only for their authorized warehouse.",
            )
        return self.repo.list_by_warehouse(warehouse_id, status=status)

    def update_task_status_controlled(self, task_id: int, new_status: str, actor: User) -> WorkerTask:
        """Controlled task status update with worker authorization enforcement."""
        task = self.repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        # Worker isolation: workers can only update their own tasks
        if actor.role == "WAREHOUSE_WORKER" and task.assigned_worker_id != actor.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workers can only update their own assigned tasks.",
            )

        valid_statuses = {"PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"}
        new_status = new_status.upper()
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{new_status}'. Must be one of: {', '.join(sorted(valid_statuses))}",
            )

        task.status = new_status
        if new_status == "COMPLETED":
            task.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task

