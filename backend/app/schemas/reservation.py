from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ReservationCreateRequest(BaseModel):
    allocation_id: int
    quantity_reserved: Decimal = Field(..., gt=0, description="Quantity to reserve (must be positive)")
    expires_in_hours: Optional[int] = Field(default=24, ge=1, le=168, description="Reservation validity duration in hours")


class ReservationResponse(BaseModel):
    reservation_id: int
    allocation_id: int
    quantity_reserved: Decimal
    reserved_at: datetime
    expires_at: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)
