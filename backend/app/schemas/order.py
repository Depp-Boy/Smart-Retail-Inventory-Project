from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    product_id: int
    quantity_requested: Decimal = Field(..., gt=0, description="Requested quantity must be greater than zero")


class OrderCreateRequest(BaseModel):
    shop_id: Optional[int] = Field(default=None, description="Shop location ID (inferred from user if omitted)")
    items: List[OrderItemCreate] = Field(..., min_length=1, description="List of products to reorder")
    expected_delivery: Optional[datetime] = None


class OrderItemResponse(BaseModel):
    order_item_id: int
    order_id: int
    product_id: int
    quantity_requested: Decimal
    quantity_allocated: Decimal
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    order_id: int
    shop_id: int
    order_date: datetime
    status: str
    total_amount: Decimal
    expected_delivery: Optional[datetime] = None
    preferred_warehouse_id: Optional[int] = None
    items: List[OrderItemResponse] = []

    model_config = ConfigDict(from_attributes=True)

