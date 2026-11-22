from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AllocationCreateRequest(BaseModel):
    order_item_id: int
    source_location_id: int = Field(..., description="Warehouse location ID")
    allocated_quantity: Decimal = Field(..., gt=0, description="Quantity to allocate from this warehouse")
    auto_reserve: bool = Field(default=True, description="Automatically create active stock reservation")


class AllocationResponse(BaseModel):
    allocation_id: int
    order_item_id: int
    source_location_id: int
    allocated_quantity: Decimal
    status: str
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    source_location_name: Optional[str] = None
    dispatched_quantity: Decimal = Decimal("0.00")

    model_config = ConfigDict(from_attributes=True)


class OrderAllocationSummaryResponse(BaseModel):
    order_id: int
    order_status: str
    allocations: List[AllocationResponse] = []
    unallocated_items: List[dict] = []
