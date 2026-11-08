from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.forecast import Forecast
from app.models.sale import Sale, SaleItem


class ForecastRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, forecast_id: int) -> Optional[Forecast]:
        return self.db.query(Forecast).filter(Forecast.forecast_id == forecast_id).first()

    def get_latest(self, shop_id: int, product_id: int, forecast_period: date) -> Optional[Forecast]:
        return (
            self.db.query(Forecast)
            .filter(
                Forecast.shop_id == shop_id,
                Forecast.product_id == product_id,
                Forecast.forecast_period == forecast_period,
            )
            .order_by(Forecast.generated_at.desc())
            .first()
        )

    def list(
        self,
        shop_id: Optional[int] = None,
        product_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Forecast]:
        query = self.db.query(Forecast)
        if shop_id:
            query = query.filter(Forecast.shop_id == shop_id)
        if product_id:
            query = query.filter(Forecast.product_id == product_id)
        if start_date:
            query = query.filter(Forecast.forecast_period >= start_date)
        if end_date:
            query = query.filter(Forecast.forecast_period <= end_date)
        return query.order_by(Forecast.forecast_period.desc(), Forecast.generated_at.desc()).offset(skip).limit(limit).all()

    def create(self, forecast: Forecast) -> Forecast:
        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)
        return forecast

    def get_historical_sales_daily(self, shop_id: int, product_id: int, days: int = 30) -> List[Decimal]:
        """Return daily sales quantities in chronological order for the last `days`."""
        since = func.now() - timedelta(days=days)
        results = (
            self.db.query(
                func.date(Sale.sale_date).label("sale_day"),
                func.coalesce(func.sum(SaleItem.quantity), 0).label("daily_qty"),
            )
            .join(SaleItem, Sale.sale_id == SaleItem.sale_id)
            .filter(
                Sale.shop_id == shop_id,
                SaleItem.product_id == product_id,
                Sale.status == "COMPLETED",
                Sale.sale_date >= since,
            )
            .group_by(func.date(Sale.sale_date))
            .order_by(func.date(Sale.sale_date).asc())
            .all()
        )
        return [Decimal(str(r.daily_qty)) for r in results]
