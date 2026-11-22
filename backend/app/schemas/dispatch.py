from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DispatchItemCreate(BaseModel):
    allocation_id: int
    product_id: int
    quantity: Decimal = Field(..., gt=0)


class DispatchItemResponse(BaseModel):
    dispatch_item_id: int
    dispatch_id: int
    allocation_id: int
    product_id: int
    quantity: Decimal
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DispatchCreateRequest(BaseModel):
    order_id: int
    source_location_id: int = Field(..., description="Warehouse dispatching the goods")
    items: List[DispatchItemCreate] = Field(..., min_length=1)
    tracking_reference: Optional[str] = None
    notes: Optional[str] = None


class DispatchStatusUpdate(BaseModel):
    status: str = Field(..., description="PENDING, PACKING, READY, IN_TRANSIT, DELIVERED, CANCELLED")
    tracking_reference: Optional[str] = None
    notes: Optional[str] = None


class DispatchResponse(BaseModel):
    dispatch_id: int
    dispatch_code: str
    order_id: int
    source_location_id: int
    created_by_user_id: int
    status: str
    dispatch_date: Optional[datetime] = None
    tracking_reference: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    source_location_name: Optional[str] = None
    items: List[DispatchItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
