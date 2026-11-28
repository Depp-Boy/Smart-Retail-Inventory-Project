import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.allocation import OrderAllocation
from app.models.dispatch import Dispatch, DispatchItem
from app.models.location import Location
from app.models.order import OrderItem
from app.models.user import User
from app.models.worker_task import WorkerTask, WorkerTaskItem
from app.repositories.user_repository import UserRepository
from app.repositories.worker_task_repository import WorkerTaskRepository
from app.schemas.worker_task import WorkerCreateRequest, WorkerTaskCreateRequest
from app.services.audit_service import AuditLogService

VALID_TASK_TYPES: Set[str] = {"PICKING", "PACKING", "DISPATCH"}
VALID_TASK_PRIORITIES: Set[str] = {"LOW", "NORMAL", "HIGH"}
VALID_TASK_STATUSES: Set[str] = {"PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"}

ADMIN_ALLOWED_TASK_TRANSITIONS: Dict[str, Set[str]] = {
    "PENDING": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"PENDING", "COMPLETED", "CANCELLED"},
    "COMPLETED": {"IN_PROGRESS"},  # Administrative reopen clears completed_at
    "CANCELLED": set(),
}

WORKER_ALLOWED_TASK_TRANSITIONS: Dict[str, Set[str]] = {
    "PENDING": {"IN_PROGRESS"},
    "IN_PROGRESS": {"COMPLETED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}


class WorkerTaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkerTaskRepository(db)
        self.user_repo = UserRepository(db)

    def create_worker(self, req: WorkerCreateRequest, actor: User) -> User:
        """
        Securely create a WAREHOUSE_WORKER account.
        - ADMIN: must specify a valid warehouse location_id.
        - WAREHOUSE_MANAGER: assigned strictly to their own warehouse; overriding location_id is rejected (403).
        - SHOP_OWNER / WAREHOUSE_WORKER: forbidden (403).
        """
        if actor.role not in ("ADMIN", "WAREHOUSE_MANAGER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only warehouse managers or admins can create warehouse worker accounts.",
            )

        if actor.role == "WAREHOUSE_MANAGER":
            if actor.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse manager is not assigned to a warehouse.",
                )
            if req.location_id is not None and req.location_id != actor.location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse managers can only create workers for their own warehouse.",
                )
            target_warehouse_id = actor.location_id
        else:
            if req.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Warehouse location_id must be specified when creating a worker as ADMIN.",
                )
            target_warehouse_id = req.location_id

        normalized_email = req.email.lower().strip()
        if self.user_repo.get_by_email(normalized_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A user with email '{req.email}' is already registered.",
            )

        try:
            warehouse = (
                self.db.query(Location)
                .filter(Location.location_id == target_warehouse_id)
                .first()
            )
            if not warehouse:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Warehouse location {target_warehouse_id} not found.",
                )
            if warehouse.location_type not in ("MAIN_WAREHOUSE", "SUB_WAREHOUSE"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Location {target_warehouse_id} is not a valid warehouse.",
                )

            worker = User(
                name=req.name.strip(),
                email=normalized_email,
                password_hash=hash_password(req.password),
                role="WAREHOUSE_WORKER",
                location_id=target_warehouse_id,
                phone=req.phone.strip() if req.phone else None,
            )
            self.db.add(worker)
            self.db.commit()
            self.db.refresh(worker)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type="WORKER_CREATED",
            actor_id=actor.user_id,
            actor_role=actor.role,
            entity_type="USER",
            entity_id=worker.user_id,
            location_id=target_warehouse_id,
            details={
                "created_role": "WAREHOUSE_WORKER",
                "warehouse_id": target_warehouse_id,
            },
        )
        return worker

    def _get_task_warehouse_id(self, task: WorkerTask) -> Optional[int]:
        if task.dispatch_id is not None:
            dsp = self.db.query(Dispatch).filter(Dispatch.dispatch_id == task.dispatch_id).first()
            if dsp:
                return dsp.source_location_id
        if task.allocation_id is not None:
            alloc = self.db.query(OrderAllocation).filter(OrderAllocation.allocation_id == task.allocation_id).first()
            if alloc:
                return alloc.source_location_id
        worker = self.db.query(User).filter(User.user_id == task.assigned_worker_id).first()
        return worker.location_id if worker else None

    def _authorize_task_access(self, task: WorkerTask, actor: User, action: str = "access") -> None:
        if actor.role == "ADMIN":
            return
        if actor.role == "WAREHOUSE_WORKER":
            if task.assigned_worker_id != actor.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Workers can only {action} their own assigned tasks.",
                )
            return
        if actor.role == "WAREHOUSE_MANAGER":
            task_wh = self._get_task_warehouse_id(task)
            if actor.location_id is None or task_wh != actor.location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Managers can only {action} tasks belonging to their own warehouse.",
                )
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to {action} worker tasks.",
        )

    def create_task(self, req: WorkerTaskCreateRequest, manager: User) -> WorkerTask:
        if manager.role not in ("ADMIN", "WAREHOUSE_MANAGER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only warehouse managers or admins can create and assign tasks.",
            )

        task_type = req.task_type.strip().upper() if req.task_type else ""
        if task_type not in VALID_TASK_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task_type '{task_type}'. Must be one of: {', '.join(sorted(VALID_TASK_TYPES))}.",
            )

        priority = req.priority.strip().upper() if req.priority else "NORMAL"
        if priority not in VALID_TASK_PRIORITIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority '{priority}'. Must be one of: {', '.join(sorted(VALID_TASK_PRIORITIES))}.",
            )

        if not req.allocation_id and not req.dispatch_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task must reference at least an allocation_id or a dispatch_id.",
            )

        try:
            # 1. Validate assigned worker exists, has role WAREHOUSE_WORKER, and matches manager's warehouse
            worker = self.db.query(User).filter(User.user_id == req.assigned_worker_id).first()
            if not worker or worker.role != "WAREHOUSE_WORKER":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assigned user must be a registered WAREHOUSE_WORKER.",
                )
            if worker.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assigned worker is not associated with a warehouse.",
                )
            if manager.role == "WAREHOUSE_MANAGER":
                if manager.location_id is None or worker.location_id != manager.location_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Warehouse managers can only assign tasks to workers belonging to their own warehouse.",
                    )

            # 2. Validate referenced allocation and/or dispatch exist, are active, match warehouse, and don't contradict
            alloc: Optional[OrderAllocation] = None
            dispatch: Optional[Dispatch] = None

            if req.allocation_id is not None:
                alloc = (
                    self.db.query(OrderAllocation)
                    .filter(OrderAllocation.allocation_id == req.allocation_id)
                    .first()
                )
                if not alloc:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Referenced allocation {req.allocation_id} not found.",
                    )
                if alloc.status in ("CANCELLED", "DELIVERED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot create task for allocation in {alloc.status} status.",
                    )
                if manager.role == "WAREHOUSE_MANAGER" and alloc.source_location_id != manager.location_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Warehouse managers can only create tasks for allocations in their own warehouse.",
                    )
                if alloc.source_location_id != worker.location_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Referenced allocation warehouse does not match assigned worker's warehouse.",
                    )

            if req.dispatch_id is not None:
                dispatch = (
                    self.db.query(Dispatch)
                    .filter(Dispatch.dispatch_id == req.dispatch_id)
                    .first()
                )
                if not dispatch:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Referenced dispatch {req.dispatch_id} not found.",
                    )
                if dispatch.status in ("CANCELLED", "DELIVERED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot create task for dispatch in {dispatch.status} status.",
                    )
                if manager.role == "WAREHOUSE_MANAGER" and dispatch.source_location_id != manager.location_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Warehouse managers can only create tasks for dispatches in their own warehouse.",
                    )
                if dispatch.source_location_id != worker.location_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Referenced dispatch warehouse does not match assigned worker's warehouse.",
                    )

            # Prevent contradictory allocation + dispatch references
            matching_dispatch_item: Optional[DispatchItem] = None
            if alloc is not None and dispatch is not None:
                if alloc.source_location_id != dispatch.source_location_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Contradictory task references: allocation and dispatch belong to different warehouses.",
                    )
                matching_dispatch_item = (
                    self.db.query(DispatchItem)
                    .filter(
                        DispatchItem.dispatch_id == dispatch.dispatch_id,
                        DispatchItem.allocation_id == alloc.allocation_id,
                    )
                    .first()
                )
                if not matching_dispatch_item:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Contradictory task references: allocation is not part of the referenced dispatch.",
                    )

            # 3. Build allowed product -> max quantity map from the referenced allocation/dispatch
            allowed_qty_by_product: Dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
            if matching_dispatch_item is not None:
                allowed_qty_by_product[matching_dispatch_item.product_id] = Decimal(str(matching_dispatch_item.quantity))
            elif dispatch is not None:
                dispatch_items = (
                    self.db.query(DispatchItem)
                    .filter(DispatchItem.dispatch_id == dispatch.dispatch_id)
                    .all()
                )
                for di in dispatch_items:
                    allowed_qty_by_product[di.product_id] += Decimal(str(di.quantity))
            elif alloc is not None:
                order_item = (
                    self.db.query(OrderItem)
                    .filter(OrderItem.order_item_id == alloc.order_item_id)
                    .first()
                )
                if not order_item:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Parent order item for allocation not found.",
                    )
                allowed_qty_by_product[order_item.product_id] = Decimal(str(alloc.allocated_quantity))

            # Validate task items against referenced products and quantities (no duplicate product_id)
            seen_products: Set[int] = set()
            for item_in in req.items:
                if item_in.product_id in seen_products:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Duplicate product {item_in.product_id} in task items.",
                    )
                seen_products.add(item_in.product_id)

                qty = Decimal(str(item_in.quantity))
                if qty <= Decimal("0.00"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Task item quantity must be positive.",
                    )
                if item_in.product_id not in allowed_qty_by_product:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product {item_in.product_id} does not match the referenced allocation or dispatch.",
                    )
                max_qty = allowed_qty_by_product[item_in.product_id]
                if qty > max_qty:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Task item quantity ({qty}) exceeds referenced allocation/dispatch "
                            f"quantity ({max_qty}) for product {item_in.product_id}."
                        ),
                    )

            task_code = f"TASK-{uuid.uuid4().hex[:8].upper()}"
            task = WorkerTask(
                task_code=task_code,
                assigned_worker_id=req.assigned_worker_id,
                assigned_by_user_id=manager.user_id,
                allocation_id=req.allocation_id,
                dispatch_id=req.dispatch_id,
                task_type=task_type,
                priority=priority,
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
                    quantity=Decimal(str(item_in.quantity)),
                    completed_quantity=Decimal("0.00"),
                )
                self.db.add(task_item)

            self.db.commit()
            self.db.refresh(task)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type="WORKER_TASK_CREATED",
            actor_id=manager.user_id,
            actor_role=manager.role,
            entity_type="WORKER_TASK",
            entity_id=task.task_id,
            location_id=worker.location_id,
            details={
                "task_type": task.task_type,
                "priority": task.priority,
                "assigned_worker_id": worker.user_id,
                "allocation_id": task.allocation_id,
                "dispatch_id": task.dispatch_id,
                "status": task.status,
            },
        )

        return task

    def get_task_by_id(self, task_id: int, actor: User) -> WorkerTask:
        task = self.repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
        self._authorize_task_access(task, actor, action="view")
        return task

    def list_tasks(
        self,
        actor: User,
        status_filter: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        worker_id: Optional[int] = None,
    ) -> List[WorkerTask]:
        if status_filter:
            st_upper = status_filter.strip().upper()
            if st_upper not in VALID_TASK_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter '{st_upper}'.",
                )
            status_filter = st_upper

        if actor.role == "ADMIN":
            return self.repo.list_all(
                warehouse_id=warehouse_id,
                worker_id=worker_id,
                status=status_filter,
            )

        if actor.role == "WAREHOUSE_WORKER":
            if worker_id is not None and worker_id != actor.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workers can retrieve only their own assigned tasks.",
                )
            if warehouse_id is not None and warehouse_id != actor.location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workers cannot list tasks for another warehouse.",
                )
            return self.repo.list_by_worker(actor.user_id, status=status_filter)

        if actor.role == "WAREHOUSE_MANAGER":
            if actor.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse manager is not assigned to a warehouse.",
                )
            if warehouse_id is not None and warehouse_id != actor.location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Managers can view tasks only for their authorized warehouse.",
                )
            if worker_id is not None:
                worker = self.db.query(User).filter(User.user_id == worker_id).first()
                if not worker or worker.role != "WAREHOUSE_WORKER" or worker.location_id != actor.location_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Managers can view tasks only for workers in their own warehouse.",
                    )
            return self.repo.list_all(
                warehouse_id=actor.location_id,
                worker_id=worker_id,
                status=status_filter,
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to list worker tasks.",
        )

    def update_task_progress(
        self,
        task_id: int,
        task_item_id: int,
        completed_quantity: Decimal,
        actor: User,
    ) -> WorkerTask:
        try:
            task = self.repo.get_by_id(task_id, lock=True)
            if not task:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

            self._authorize_task_access(task, actor, action="update progress on")

            if task.status in ("CANCELLED", "COMPLETED"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot update item progress for a task in {task.status} status.",
                )

            item = self.repo.get_item(task_item_id, lock=True)
            if not item or item.task_id != task_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task item not found.")

            completed_dec = Decimal(str(completed_quantity))
            if not completed_dec.is_finite():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Completed quantity must be a finite number.",
                )
            if completed_dec < Decimal("0.00"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Completed quantity cannot be negative.",
                )
            if completed_dec > Decimal(str(item.quantity)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Completed quantity ({completed_dec}) cannot exceed assigned quantity ({item.quantity}).",
                )

            previous_status = task.status
            item.completed_quantity = completed_dec
            self.db.flush()

            # Automatically update task status based on item progress (never touches inventory!)
            task_items = (
                self.db.query(WorkerTaskItem)
                .filter(WorkerTaskItem.task_id == task.task_id)
                .all()
            )
            all_completed = len(task_items) > 0 and all(
                Decimal(str(i.completed_quantity)) >= Decimal(str(i.quantity)) for i in task_items
            )
            any_started = any(Decimal(str(i.completed_quantity)) > Decimal("0.00") for i in task_items)

            if all_completed:
                task.status = "COMPLETED"
                task.completed_at = datetime.now(timezone.utc)
            elif any_started:
                task.status = "IN_PROGRESS"
                task.completed_at = None

            task_wh_id = self._get_task_warehouse_id(task)
            self.db.commit()
            self.db.refresh(task)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type="WORKER_TASK_COMPLETED" if task.status == "COMPLETED" else "WORKER_TASK_PROGRESS_UPDATED",
            actor_id=actor.user_id,
            actor_role=actor.role,
            entity_type="WORKER_TASK",
            entity_id=task.task_id,
            location_id=task_wh_id,
            details={
                "task_item_id": task_item_id,
                "completed_quantity": str(completed_dec),
                "previous_status": previous_status,
                "new_status": task.status,
            },
        )
        return task

    def list_tasks_for_worker(self, worker_id: int, actor: User, status_filter: Optional[str] = None, **kwargs) -> List[WorkerTask]:
        # Preserve backwards-compatible `status=` keyword argument
        effective_status = kwargs.get("status", status_filter)
        if actor.role == "WAREHOUSE_WORKER":
            if actor.user_id != worker_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workers can retrieve only their own assigned tasks.",
                )
            return self.repo.list_by_worker(worker_id, status=effective_status)

        if actor.role == "WAREHOUSE_MANAGER":
            if actor.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse manager is not assigned to a warehouse.",
                )
            worker = self.db.query(User).filter(User.user_id == worker_id).first()
            if not worker:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found.")
            if worker.role != "WAREHOUSE_WORKER" or worker.location_id != actor.location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Managers can view tasks only for workers belonging to their own warehouse.",
                )
            return self.repo.list_by_worker(worker_id, status=effective_status)

        if actor.role == "ADMIN":
            return self.repo.list_by_worker(worker_id, status=effective_status)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to list worker tasks.",
        )

    def list_tasks_for_warehouse(self, warehouse_id: int, actor: User, status_filter: Optional[str] = None, **kwargs) -> List[WorkerTask]:
        effective_status = kwargs.get("status", status_filter)
        if actor.role == "ADMIN":
            return self.repo.list_by_warehouse(warehouse_id, status=effective_status)
        if actor.role == "WAREHOUSE_MANAGER":
            if actor.location_id is None or actor.location_id != warehouse_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Managers can view tasks only for their authorized warehouse.",
                )
            return self.repo.list_by_warehouse(warehouse_id, status=effective_status)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to view warehouse tasks.",
        )

    def update_task_status_controlled(self, task_id: int, new_status: str, actor: User) -> WorkerTask:
        """Controlled task status update with role, ownership, item-consistency, and state-machine enforcement."""
        target_status = new_status.strip().upper() if new_status else ""
        if target_status not in VALID_TASK_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{target_status}'. Must be one of: {', '.join(sorted(VALID_TASK_STATUSES))}",
            )

        try:
            task = self.repo.get_by_id(task_id, lock=True)
            if not task:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

            self._authorize_task_access(task, actor, action="update")

            current_status = task.status

            if actor.role == "WAREHOUSE_WORKER":
                if target_status == "CANCELLED":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Workers are not authorized to cancel tasks.",
                    )
                if current_status == "COMPLETED" and target_status == "IN_PROGRESS":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only managers or admins can reopen a completed task.",
                    )
                allowed_targets = WORKER_ALLOWED_TASK_TRANSITIONS.get(current_status, set())
                if target_status not in allowed_targets:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid task status transition from {current_status} to {target_status}.",
                    )
            else:
                # ADMIN or WAREHOUSE_MANAGER (own warehouse already verified)
                allowed_targets = ADMIN_ALLOWED_TASK_TRANSITIONS.get(current_status, set())
                if target_status not in allowed_targets:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid task status transition from {current_status} to {target_status}.",
                    )

            # Enforce item-progress consistency when marking COMPLETED
            if target_status == "COMPLETED":
                task_items = (
                    self.db.query(WorkerTaskItem)
                    .filter(WorkerTaskItem.task_id == task.task_id)
                    .all()
                )
                if task_items and any(
                    Decimal(str(i.completed_quantity)) < Decimal(str(i.quantity))
                    for i in task_items
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot mark task COMPLETED while assigned item quantities remain unfinished.",
                    )
                task.completed_at = datetime.now(timezone.utc)
            elif current_status == "COMPLETED" and target_status == "IN_PROGRESS":
                # Administrative reopen clears completed_at
                task.completed_at = None

            task_wh_id = self._get_task_warehouse_id(task)
            task.status = target_status
            self.db.commit()
            self.db.refresh(task)
        except Exception:
            self.db.rollback()
            raise

        event_name = (
            "WORKER_TASK_COMPLETED"
            if target_status == "COMPLETED"
            else "WORKER_TASK_CANCELLED"
            if target_status == "CANCELLED"
            else "WORKER_TASK_STATUS_UPDATED"
        )
        AuditLogService.log_event(
            event_type=event_name,
            actor_id=actor.user_id,
            actor_role=actor.role,
            entity_type="WORKER_TASK",
            entity_id=task.task_id,
            location_id=task_wh_id,
            details={"previous_status": current_status, "new_status": target_status},
        )

        return task
