from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class StockTransferCreateRequest(BaseModel):
    source_location_id: int
    destination_location_id: int
    product_id: int
    quantity: Decimal = Field(..., gt=0, description="Transfer quantity must be greater than zero")


class StockTransferStatusUpdate(BaseModel):
    status: str = Field(..., description="IN_TRANSIT, COMPLETED, CANCELLED")


class StockTransferResponse(BaseModel):
    transfer_id: int
    source_location_id: int
    destination_location_id: int
    product_id: int
    quantity: Decimal
    transfer_date: datetime
    status: str
    source_location_name: Optional[str] = None
    destination_location_name: Optional[str] = None
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
