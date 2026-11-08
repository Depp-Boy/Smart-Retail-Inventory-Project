from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: Decimal = Field(..., gt=0, description="Quantity sold must be greater than zero")
    unit_price: Optional[Decimal] = Field(default=None, ge=0)


class SaleCreateRequest(BaseModel):
    shop_id: Optional[int] = Field(default=None, description="Shop location ID (inferred from user if omitted)")
    items: List[SaleItemCreate] = Field(..., min_length=1, description="List of items sold")
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    payment_method: Optional[str] = Field(default="CASH", description="CASH, UPI, CARD, OTHER")
    tax_amount: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, description="Validated tax amount")
    discount_amount: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, description="Validated discount amount")


class SaleItemResponse(BaseModel):
    sale_item_id: int
    sale_id: int
    product_id: int
    quantity: Decimal
    unit_price: Decimal
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SaleResponse(BaseModel):
    sale_id: int
    shop_id: int
    sale_date: datetime
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    status: str
    payment_method: Optional[str]
    customer_name: Optional[str]
    customer_phone: Optional[str]
    items: List[SaleItemResponse] = []

    model_config = ConfigDict(from_attributes=True)

