from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.worker_task import WorkerTask, WorkerTaskItem
from app.models.user import User


class WorkerTaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, task_id: int, lock: bool = False) -> Optional[WorkerTask]:
        query = self.db.query(WorkerTask).filter(WorkerTask.task_id == task_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def get_by_code(self, task_code: str) -> Optional[WorkerTask]:
        return self.db.query(WorkerTask).filter(WorkerTask.task_code == task_code).first()

    def list_all(
        self,
        warehouse_id: Optional[int] = None,
        worker_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[WorkerTask]:
        query = self.db.query(WorkerTask)
        if warehouse_id is not None:
            query = query.join(User, WorkerTask.assigned_worker_id == User.user_id).filter(
                User.location_id == warehouse_id
            )
        if worker_id is not None:
            query = query.filter(WorkerTask.assigned_worker_id == worker_id)
        if status:
            query = query.filter(WorkerTask.status == status.strip().upper())
        return query.order_by(WorkerTask.created_at.desc(), WorkerTask.task_id.desc()).all()

    def list_by_worker(self, worker_id: int, status: Optional[str] = None) -> List[WorkerTask]:
        query = self.db.query(WorkerTask).filter(WorkerTask.assigned_worker_id == worker_id)
        if status:
            query = query.filter(WorkerTask.status == status.strip().upper())
        return query.order_by(WorkerTask.created_at.desc(), WorkerTask.task_id.desc()).all()

    def list_by_warehouse(self, warehouse_id: int, status: Optional[str] = None) -> List[WorkerTask]:
        query = (
            self.db.query(WorkerTask)
            .join(User, WorkerTask.assigned_worker_id == User.user_id)
            .filter(User.location_id == warehouse_id)
        )
        if status:
            query = query.filter(WorkerTask.status == status.strip().upper())
        return query.order_by(WorkerTask.created_at.desc(), WorkerTask.task_id.desc()).all()

    def get_item(self, task_item_id: int, lock: bool = False) -> Optional[WorkerTaskItem]:
        query = self.db.query(WorkerTaskItem).filter(WorkerTaskItem.task_item_id == task_item_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def create(self, task: WorkerTask) -> WorkerTask:
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update(self, task: WorkerTask) -> WorkerTask:
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_item(self, item: WorkerTaskItem) -> WorkerTaskItem:
        self.db.commit()
        self.db.refresh(item)
        return item
