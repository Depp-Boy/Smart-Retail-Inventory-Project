from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AlertCreateRequest(BaseModel):
    location_id: int
    alert_type: str = Field(..., description="LOW_STOCK, ORDER_NOTIFICATION, DISPATCH_NOTIFICATION, TASK_ASSIGNED")
    message: str = Field(..., min_length=3)
    product_id: Optional[int] = None
    user_id: Optional[int] = None


class AlertStatusUpdate(BaseModel):
    status: str = Field(..., description="READ, DISMISSED")


class AlertResponse(BaseModel):
    alert_id: int
    location_id: int
    product_id: Optional[int] = None
    alert_type: str
    message: str
    created_at: datetime
    status: str
    user_id: Optional[int] = None
    location_name: Optional[str] = None
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
