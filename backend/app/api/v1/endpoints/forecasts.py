from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.forecast import (
    ForecastGenerateRequest,
    ForecastResponse,
    ReorderRecommendationResponse,
)
from app.services.forecast_service import ForecastService

router = APIRouter()


@router.get("/", response_model=List[ForecastResponse], summary="List Demand Forecasts")
def list_forecasts(
    shop_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ForecastService(db)
    return service.list(shop_id=shop_id, product_id=product_id, start_date=start_date, end_date=end_date)


@router.post("/generate", response_model=ForecastResponse, status_code=status.HTTP_201_CREATED, summary="Generate Demand Forecast")
def generate_forecast(
    req: ForecastGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ForecastService(db)
    return service.generate_forecast(req)


@router.get("/reorder-recommendation", response_model=ReorderRecommendationResponse, summary="Get Reorder Recommendation")
def get_reorder_recommendation(
    shop_id: int = Query(...),
    product_id: int = Query(...),
    period: date = Query(default_factory=date.today),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ForecastService(db)
    return service.get_reorder_recommendation(shop_id=shop_id, product_id=product_id, period=period)
