from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ForecastGenerateRequest(BaseModel):
    shop_id: int
    product_id: int
    forecast_period: date
    model_preference: Optional[str] = Field(default="AUTO", description="SMA, WMA, EMA, or AUTO")
    history_days: Optional[int] = Field(default=30, ge=7, le=365)
    alpha: Optional[float] = Field(default=0.3, ge=0.01, le=1.0)


class ForecastResponse(BaseModel):
    forecast_id: int
    shop_id: int
    product_id: int
    forecasted_demand: Decimal
    forecast_period: date
    model_used: str
    generated_at: datetime
    product_name: Optional[str] = None
    shop_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReorderRecommendationResponse(BaseModel):
    shop_id: int
    product_id: int
    product_name: str
    forecasted_demand: Decimal
    safety_stock: Decimal
    available_stock: Decimal
    incoming_stock: Decimal
    recommended_reorder_quantity: Decimal
    calculation_breakdown: str
