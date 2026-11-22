from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.forecast import Forecast
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.repositories.forecast_repository import ForecastRepository
from app.schemas.forecast import ForecastGenerateRequest, ReorderRecommendationResponse


class ForecastService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ForecastRepository(db)

    def generate_forecast(self, req: ForecastGenerateRequest) -> Forecast:
        history = self.repo.get_historical_sales_daily(req.shop_id, req.product_id, days=req.history_days)

        model_name = req.model_preference.upper() if req.model_preference else "AUTO"
        data = [float(x) for x in history]

        if not data:
            # Fallback when zero historical sales recorded
            forecast_val = Decimal("0.00")
            selected_model = "ZERO_HISTORY_BASELINE"
        elif model_name == "SMA" or (model_name == "AUTO" and len(data) < 7):
            forecast_val = Decimal(str(round(sum(data) / len(data), 2)))
            selected_model = "Simple Moving Average (SMA)"
        elif model_name == "WMA" or (model_name == "AUTO" and len(data) < 14):
            weights = list(range(1, len(data) + 1))
            weighted_sum = sum(w * val for w, val in zip(weights, data))
            forecast_val = Decimal(str(round(weighted_sum / sum(weights), 2)))
            selected_model = "Weighted Moving Average (WMA)"
        else:  # EMA
            alpha = req.alpha or 0.3
            ema = data[0]
            for val in data[1:]:
                ema = alpha * val + (1 - alpha) * ema
            forecast_val = Decimal(str(round(ema, 2)))
            selected_model = f"Exponential Smoothing (EMA, alpha={alpha})"

        forecast_val = max(Decimal("0.00"), forecast_val)

        forecast = Forecast(
            shop_id=req.shop_id,
            product_id=req.product_id,
            forecasted_demand=forecast_val,
            forecast_period=req.forecast_period,
            model_used=selected_model,
        )
        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)
        return forecast

    def get_reorder_recommendation(self, shop_id: int, product_id: int, period: date) -> ReorderRecommendationResponse:
        product = self.db.query(Product).filter(Product.product_id == product_id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

        # 1. Forecasted demand
        latest_fc = self.repo.get_latest(shop_id, product_id, period)
        if latest_fc:
            fc_demand = latest_fc.forecasted_demand
        else:
            fc = self.generate_forecast(ForecastGenerateRequest(shop_id=shop_id, product_id=product_id, forecast_period=period))
            fc_demand = fc.forecasted_demand

        # 2. Safety stock = reorder threshold
        safety_stock = product.reorder_threshold

        # 3. Available stock at shop
        inv = self.db.query(Inventory).filter_by(location_id=shop_id, product_id=product_id).first()
        available_stock = Decimal(str(inv.available_quantity)) if inv else Decimal("0.00")

        # 4. Incoming stock = pending order items
        incoming = (
            self.db.query(OrderItem)
            .join(Order, OrderItem.order_id == Order.order_id)
            .filter(
                Order.shop_id == shop_id,
                OrderItem.product_id == product_id,
                Order.status.in_(["PENDING", "PROCESSING"]),
            )
            .all()
        )
        incoming_stock = sum((it.quantity_requested - it.quantity_allocated for it in incoming), Decimal("0.00"))

        # Formula: Reorder = max(0, Forecasted + Safety - Available - Incoming)
        reorder_qty = max(Decimal("0.00"), fc_demand + safety_stock - available_stock - incoming_stock)
        breakdown = (
            f"Forecasted Demand ({fc_demand}) + Safety Stock ({safety_stock}) - "
            f"Available Stock ({available_stock}) - Incoming Stock ({incoming_stock}) = {reorder_qty}"
        )

        return ReorderRecommendationResponse(
            shop_id=shop_id,
            product_id=product.product_id,
            product_name=product.product_name,
            forecasted_demand=fc_demand,
            safety_stock=safety_stock,
            available_stock=available_stock,
            incoming_stock=incoming_stock,
            recommended_reorder_quantity=reorder_qty,
            calculation_breakdown=breakdown,
        )

    def list(
        self,
        shop_id: Optional[int] = None,
        product_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Forecast]:
        return self.repo.list(shop_id=shop_id, product_id=product_id, start_date=start_date, end_date=end_date)
