from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    location_name: str = Field(..., min_length=2, max_length=255)
    location_type: str = Field(..., description="MAIN_WAREHOUSE, SUB_WAREHOUSE, or SHOP")
    address: str = Field(..., min_length=3)
    parent_location_id: Optional[int] = None


class LocationUpdate(BaseModel):
    location_name: Optional[str] = None
    location_type: Optional[str] = None
    address: Optional[str] = None
    parent_location_id: Optional[int] = None


class LocationResponse(BaseModel):
    location_id: int
    location_name: str
    location_type: str
    address: str
    parent_location_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ShopWarehouseCreate(BaseModel):
    warehouse_id: int
    is_preferred: bool = False
    priority: int = 1


class ShopWarehouseResponse(BaseModel):
    relationship_id: int
    shop_id: int
    warehouse_id: int
    is_preferred: bool
    priority: int
    warehouse: Optional[LocationResponse] = None

    model_config = ConfigDict(from_attributes=True)

