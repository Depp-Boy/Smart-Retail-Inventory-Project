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
    alpha: Optional[float] = Field(default=0.3, gt=0.0, le=1.0)
    forecast_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=366,
        description="Optional forecast horizon in days (defaults to actual days in forecast_period's month)",
    )


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
    forecast_horizon_days: Optional[int] = None
    predicted_daily_demand: Optional[Decimal] = None
    available_stock: Optional[Decimal] = None
    in_transit_stock: Optional[Decimal] = None
    recommended_reorder_quantity: Optional[Decimal] = None
    stock_health_status: Optional[str] = None

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
    forecast_period: Optional[date] = None
    model_used: Optional[str] = None
    in_transit_stock: Optional[Decimal] = None
    stock_health_status: str = "HEALTHY"
    is_slow_moving: bool = False
    is_dead_stock: bool = False
    is_increasing_demand: bool = False
    is_approaching_stockout: bool = False


class StockHealthResponse(BaseModel):
    shop_id: int
    product_id: int
    product_name: str
    history_days: int
    total_units_sold: Decimal
    active_sales_days: int
    average_daily_sales: Decimal
    available_stock: Decimal
    in_transit_stock: Decimal
    forecasted_monthly_demand: Decimal
    recommended_reorder_quantity: Decimal
    stock_health_status: str
    is_slow_moving: bool
    is_dead_stock: bool
    is_increasing_demand: bool
    is_approaching_stockout: bool
    has_sufficient_history: bool
