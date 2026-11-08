from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.product import ProductResponse


class InventoryResponse(BaseModel):
    inventory_id: int
    location_id: int
    product_id: int
    quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: float
    last_updated: datetime
    product: Optional[ProductResponse] = None

    model_config = ConfigDict(from_attributes=True)


class InventorySummaryResponse(BaseModel):
    location_id: int
    total_products_count: int
    total_physical_quantity: Decimal
    total_reserved_quantity: Decimal
    total_available_quantity: float
    low_stock_count: int
    out_of_stock_count: int
