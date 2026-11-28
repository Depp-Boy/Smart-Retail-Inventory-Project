from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.forecast import Forecast
from app.models.sale import Sale, SaleItem


def _to_utc_date(dt: datetime) -> date:
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(timezone.utc).date()


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
            .order_by(Forecast.generated_at.desc(), Forecast.forecast_id.desc())
            .first()
        )

    def list(
        self,
        shop_id: Optional[int] = None,
        shop_ids: Optional[List[int]] = None,
        product_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Forecast]:
        query = self.db.query(Forecast)
        if shop_id is not None:
            query = query.filter(Forecast.shop_id == shop_id)
        if shop_ids is not None:
            if not shop_ids:
                return []
            query = query.filter(Forecast.shop_id.in_(shop_ids))
        if product_id is not None:
            query = query.filter(Forecast.product_id == product_id)
        if start_date is not None:
            query = query.filter(Forecast.forecast_period >= start_date)
        if end_date is not None:
            query = query.filter(Forecast.forecast_period <= end_date)
        return (
            query.order_by(
                Forecast.forecast_period.desc(),
                Forecast.generated_at.desc(),
                Forecast.forecast_id.desc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, forecast: Forecast) -> Forecast:
        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)
        return forecast

    def get_daily_sales_series(
        self,
        shop_id: int,
        product_id: int,
        days: int = 30,
        end_date: Optional[date] = None,
    ) -> Tuple[List[Decimal], int, Decimal, Optional[date]]:
        """
        Build a complete chronological daily sales time series of exact length `days`
        ending on `end_date` (inclusive), filling days with zero sales as Decimal('0.00').

        Includes ONLY COMPLETED sales for the specified shop and product.
        Excludes CANCELLED and REFUNDED sales.

        Returns:
            (daily_series, active_sales_days, total_sold, last_sale_date_in_window)
        """
        as_of = end_date or datetime.now(timezone.utc).date()
        start_day = as_of - timedelta(days=days - 1)

        # Fetch COMPLETED SaleItem rows for this shop & product (wide enough UTC window, exact date filter in Python)
        lower_bound = datetime(start_day.year, start_day.month, start_day.day, tzinfo=timezone.utc) - timedelta(days=1)
        upper_bound = datetime(as_of.year, as_of.month, as_of.day, 23, 59, 59, 999999, tzinfo=timezone.utc) + timedelta(days=1)

        rows = (
            self.db.query(Sale.sale_date, SaleItem.quantity)
            .join(SaleItem, Sale.sale_id == SaleItem.sale_id)
            .filter(
                Sale.shop_id == shop_id,
                SaleItem.product_id == product_id,
                Sale.status == "COMPLETED",
                Sale.sale_date >= lower_bound,
                Sale.sale_date <= upper_bound,
            )
            .all()
        )

        totals_by_day: Dict[date, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for sale_dt, qty in rows:
            if sale_dt is None:
                continue
            sale_day = _to_utc_date(sale_dt)
            if start_day <= sale_day <= as_of:
                totals_by_day[sale_day] += Decimal(str(qty))

        daily_series: List[Decimal] = []
        active_days = 0
        total_sold = Decimal("0.00")
        last_sale_day: Optional[date] = None

        for offset in range(days):
            current_day = start_day + timedelta(days=offset)
            qty = totals_by_day.get(current_day, Decimal("0.00"))
            daily_series.append(qty)
            if qty > Decimal("0.00"):
                active_days += 1
                total_sold += qty
                last_sale_day = current_day

        return daily_series, active_days, total_sold, last_sale_day

    def get_historical_sales_daily(
        self,
        shop_id: int,
        product_id: int,
        days: int = 30,
        end_date: Optional[date] = None,
    ) -> List[Decimal]:
        """Return complete zero-filled chronological daily sales quantities for the last `days`."""
        series, _, _, _ = self.get_daily_sales_series(shop_id, product_id, days=days, end_date=end_date)
        return series

    def get_earliest_completed_sale_date(
        self,
        shop_id: int,
        product_id: Optional[int] = None,
    ) -> Optional[date]:
        """Return the earliest COMPLETED sale date for a shop (optionally scoped to a product)."""
        query = self.db.query(func.min(Sale.sale_date)).filter(
            Sale.shop_id == shop_id,
            Sale.status == "COMPLETED",
        )
        if product_id is not None:
            query = query.join(SaleItem, Sale.sale_id == SaleItem.sale_id).filter(
                SaleItem.product_id == product_id
            )
        earliest_dt = query.scalar()
        if earliest_dt is None:
            return None
        if isinstance(earliest_dt, str):
            earliest_dt = datetime.fromisoformat(earliest_dt)
        return _to_utc_date(earliest_dt)
