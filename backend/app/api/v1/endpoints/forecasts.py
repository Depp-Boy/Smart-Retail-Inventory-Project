from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.forecast import (
    ForecastGenerateRequest,
    ForecastResponse,
    ReorderRecommendationResponse,
    StockHealthResponse,
)
from app.services.forecast_service import ForecastService

router = APIRouter()


@router.get("/", response_model=List[ForecastResponse], summary="List Demand Forecasts")
def list_forecasts(
    shop_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ForecastService(db)
    return service.list(
        shop_id=shop_id,
        product_id=product_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
        actor=current_user,
    )


@router.post("/generate", response_model=ForecastResponse, status_code=status.HTTP_201_CREATED, summary="Generate Demand Forecast")
def generate_forecast(
    req: ForecastGenerateRequest,
    current_user: User = Depends(require_roles("SHOP_OWNER", "ADMIN")),
    db: Session = Depends(get_db),
):
    service = ForecastService(db)
    return service.generate_forecast(req, actor=current_user)


@router.get("/reorder-recommendation", response_model=ReorderRecommendationResponse, summary="Get Reorder Recommendation")
def get_reorder_recommendation(
    shop_id: int = Query(...),
    product_id: int = Query(...),
    period: date = Query(default_factory=date.today),
    history_days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ForecastService(db)
    return service.get_reorder_recommendation(
        shop_id=shop_id,
        product_id=product_id,
        period=period,
        actor=current_user,
        history_days=history_days,
    )


@router.get("/stock-health", response_model=StockHealthResponse, summary="Evaluate Product Stock Health")
def get_stock_health(
    shop_id: int = Query(...),
    product_id: int = Query(...),
    history_days: int = Query(30, ge=7, le=365),
    period: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ForecastService(db)
    return service.evaluate_stock_health(
        shop_id=shop_id,
        product_id=product_id,
        history_days=history_days,
        period=period,
        actor=current_user,
    )
