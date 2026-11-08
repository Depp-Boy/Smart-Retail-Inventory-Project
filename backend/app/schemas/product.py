from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    product_name: str = Field(..., min_length=2, max_length=255)
    unit: str = Field(..., min_length=1, max_length=50)
    price: Decimal = Field(..., ge=0, description="Price must be non-negative")
    category: Optional[str] = None
    reorder_threshold: Decimal = Field(default=Decimal("0.00"), ge=0)
    sku: Optional[str] = None
    cost_price: Optional[Decimal] = Field(default=None, ge=0)
    description: Optional[str] = None
    storage_conditions: Optional[str] = None


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    unit: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, ge=0)
    category: Optional[str] = None
    reorder_threshold: Optional[Decimal] = Field(default=None, ge=0)
    sku: Optional[str] = None
    cost_price: Optional[Decimal] = Field(default=None, ge=0)
    description: Optional[str] = None
    storage_conditions: Optional[str] = None


class ProductResponse(BaseModel):
    product_id: int
    product_name: str
    category: Optional[str]
    unit: str
    price: Decimal
    reorder_threshold: Decimal
    sku: Optional[str]
    cost_price: Optional[Decimal]
    description: Optional[str]
    storage_conditions: Optional[str]

    model_config = ConfigDict(from_attributes=True)
