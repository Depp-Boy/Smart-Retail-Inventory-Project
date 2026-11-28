from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class WorkerCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=50)
    location_id: Optional[int] = Field(
        default=None,
        description="Warehouse location ID (required for ADMIN; automatically assigned from manager's warehouse for WAREHOUSE_MANAGER)",
    )


class WorkerTaskItemCreate(BaseModel):
    product_id: int
    quantity: Decimal = Field(..., gt=0)


class WorkerTaskItemResponse(BaseModel):
    task_item_id: int
    task_id: int
    product_id: int
    quantity: Decimal
    completed_quantity: Decimal
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorkerTaskCreateRequest(BaseModel):
    assigned_worker_id: int
    task_type: str = Field(..., description="PICKING, PACKING, or DISPATCH")
    priority: Optional[str] = Field(default="NORMAL", description="LOW, NORMAL, HIGH")
    allocation_id: Optional[int] = None
    dispatch_id: Optional[int] = None
    due_at: Optional[datetime] = None
    instructions: Optional[str] = None
    items: List[WorkerTaskItemCreate] = []


class WorkerTaskResponse(BaseModel):
    task_id: int
    task_code: str
    assigned_worker_id: int
    assigned_by_user_id: int
    allocation_id: Optional[int] = None
    dispatch_id: Optional[int] = None
    task_type: str
    priority: str
    status: str
    due_at: Optional[datetime] = None
    instructions: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    worker_name: Optional[str] = None
    items: List[WorkerTaskItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class WorkerTaskProgressUpdate(BaseModel):
    completed_quantity: Decimal = Field(..., ge=0, description="Cumulative completed quantity")


class WorkerTaskStatusUpdate(BaseModel):
    status: str = Field(..., description="PENDING, IN_PROGRESS, COMPLETED, CANCELLED")
