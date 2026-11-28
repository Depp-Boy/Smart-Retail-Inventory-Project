import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Set, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.dispatch import Dispatch, DispatchItem
from app.models.forecast import Forecast
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.order import Order
from app.models.product import Product
from app.models.shop_warehouse import ShopWarehouse
from app.models.user import User
from app.repositories.forecast_repository import ForecastRepository
from app.schemas.forecast import (
    ForecastGenerateRequest,
    ForecastResponse,
    ReorderRecommendationResponse,
    StockHealthResponse,
)
from app.services.audit_service import AuditLogService

TWO_PLACES = Decimal("0.01")
VALID_FORECAST_MODELS: Set[str] = {"SMA", "WMA", "EMA", "AUTO"}


@dataclass
class StockHealthMetrics:
    history_days: int
    total_units_sold: Decimal
    active_sales_days: int
    average_daily_sales: Decimal
    available_stock: Decimal
    physical_stock: Decimal
    in_transit_stock: Decimal
    has_sufficient_history: bool
    is_dead_stock: bool
    is_slow_moving: bool
    is_increasing_demand: bool
    is_approaching_stockout: bool
    stock_health_status: str


class ForecastService:
    """
    Statistical demand forecasting (SMA, WMA, EMA, AUTO), monthly replenishment planning,
    and stock-health classification (slow-moving, dead-stock, increasing demand, stockout risk).
    """

    # Centralized, configurable stock-health & forecasting thresholds
    DEFAULT_HISTORY_DAYS: int = 30
    MIN_HISTORY_DAYS: int = 7
    MAX_HISTORY_DAYS: int = 365
    MIN_ACTIVE_DAYS_FOR_WMA: int = 7
    MIN_ACTIVE_DAYS_FOR_EMA: int = 14
    MIN_ACTIVE_DAYS_FOR_TREND: int = 3
    DEAD_STOCK_INACTIVITY_DAYS: int = 30
    SLOW_MOVING_MAX_DAILY_AVG: Decimal = Decimal("0.50")
    INCREASING_DEMAND_GROWTH_RATIO: Decimal = Decimal("1.25")
    STOCKOUT_DAYS_COVER_THRESHOLD: Decimal = Decimal("7.00")

    def __init__(self, db: Session):
        self.db = db
        self.repo = ForecastRepository(db)

    # ------------------------------------------------------------------
    # Authorization helpers
    # ------------------------------------------------------------------
    def _get_associated_shop_ids_for_warehouse(self, warehouse_id: int) -> List[int]:
        rows = (
            self.db.query(ShopWarehouse.shop_id)
            .filter(ShopWarehouse.warehouse_id == warehouse_id)
            .all()
        )
        return [r.shop_id for r in rows]

    def _authorize_forecast_write(self, actor: Optional[User], shop_id: int) -> None:
        if actor is None or actor.role == "ADMIN":
            return
        if actor.role == "SHOP_OWNER":
            if actor.location_id is None or actor.location_id != shop_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Shop owners can only generate forecasts for their own shop.",
                )
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to generate forecasts.",
        )

    def _authorize_forecast_read(self, actor: Optional[User], shop_id: int) -> None:
        if actor is None or actor.role == "ADMIN":
            return
        if actor.role == "SHOP_OWNER":
            if actor.location_id is None or actor.location_id != shop_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Shop owners can only access forecasts for their own shop.",
                )
            return
        if actor.role == "WAREHOUSE_MANAGER":
            if actor.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse manager is not assigned to a warehouse.",
                )
            associated_shops = self._get_associated_shop_ids_for_warehouse(actor.location_id)
            if shop_id not in associated_shops:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse managers cannot access forecasts for unassociated shops.",
                )
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to access forecasts.",
        )

    # ------------------------------------------------------------------
    # Validation & Stock / In-Transit helpers
    # ------------------------------------------------------------------
    def _validate_shop_and_product(self, shop_id: int, product_id: int) -> Tuple[Location, Product]:
        shop = self.db.query(Location).filter(Location.location_id == shop_id).first()
        if not shop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shop location {shop_id} not found.")
        if shop.location_type != "SHOP":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Location {shop_id} is not a SHOP; demand forecasts apply to shop locations.",
            )

        product = self.db.query(Product).filter(Product.product_id == product_id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found.")

        return shop, product

    def _get_shop_inventory_quantities(self, shop_id: int, product_id: int) -> Tuple[Decimal, Decimal, Decimal]:
        """Return (physical_stock, reserved_stock, available_stock) using exact Decimal arithmetic."""
        inv = (
            self.db.query(Inventory)
            .filter(Inventory.location_id == shop_id, Inventory.product_id == product_id)
            .first()
        )
        if not inv:
            return Decimal("0.00"), Decimal("0.00"), Decimal("0.00")
        phys = Decimal(str(inv.quantity)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        res = Decimal(str(inv.reserved_quantity)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        avail = max(Decimal("0.00"), phys - res).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        return phys, res, avail

    def get_in_transit_stock(self, shop_id: int, product_id: int) -> Decimal:
        """
        Sum quantities from DispatchItems belonging exclusively to IN_TRANSIT dispatches
        for orders belonging to `shop_id`. Excludes undispatched allocations, PENDING/PACKING/READY
        dispatches, CANCELLED dispatches, and already DELIVERED dispatches.
        """
        val = (
            self.db.query(func.coalesce(func.sum(DispatchItem.quantity), 0))
            .join(Dispatch, DispatchItem.dispatch_id == Dispatch.dispatch_id)
            .join(Order, Dispatch.order_id == Order.order_id)
            .filter(
                Order.shop_id == shop_id,
                DispatchItem.product_id == product_id,
                Dispatch.status == "IN_TRANSIT",
            )
            .scalar()
        )
        return Decimal(str(val)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    @staticmethod
    def _resolve_horizon_days(forecast_period: date, forecast_days: Optional[int] = None) -> int:
        if forecast_days is not None:
            if forecast_days < 1 or forecast_days > 366:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="forecast_days must be between 1 and 366.",
                )
            return forecast_days
        return calendar.monthrange(forecast_period.year, forecast_period.month)[1]

    # ------------------------------------------------------------------
    # Statistical forecasting algorithms (exact Decimal arithmetic)
    # ------------------------------------------------------------------
    def _compute_daily_and_monthly_demand(
        self,
        daily_series: List[Decimal],
        active_sales_days: int,
        model_preference: str,
        alpha: float,
        horizon_days: int,
    ) -> Tuple[Decimal, Decimal, str]:
        """
        Compute deterministic (predicted_daily_demand, predicted_monthly_demand, model_used).
        """
        n = len(daily_series)
        if n == 0 or active_sales_days == 0:
            zero = Decimal("0.00")
            if model_preference == "SMA":
                return zero, zero, "Simple Moving Average (SMA)"
            if model_preference == "WMA":
                return zero, zero, "Weighted Moving Average (WMA)"
            if model_preference == "EMA":
                return zero, zero, f"Exponential Smoothing (EMA, alpha={alpha})"
            return zero, zero, "ZERO_HISTORY_BASELINE"

        # Choose algorithm deterministically
        if model_preference == "AUTO":
            if active_sales_days < self.MIN_ACTIVE_DAYS_FOR_WMA:
                chosen = "SMA"
            elif active_sales_days < self.MIN_ACTIVE_DAYS_FOR_EMA:
                chosen = "WMA"
            else:
                chosen = "EMA"
        else:
            chosen = model_preference

        if chosen == "SMA":
            daily_demand = sum(daily_series, Decimal("0.00")) / Decimal(n)
            model_used = "Simple Moving Average (SMA)"
        elif chosen == "WMA":
            weight_total = Decimal(n * (n + 1) // 2)
            weighted_sum = sum(
                (Decimal(idx) * val for idx, val in enumerate(daily_series, start=1)),
                Decimal("0.00"),
            )
            daily_demand = weighted_sum / weight_total
            model_used = "Weighted Moving Average (WMA)"
        else:  # EMA
            alpha_dec = Decimal(str(alpha))
            one_minus_alpha = Decimal("1") - alpha_dec
            ema = daily_series[0]
            for val in daily_series[1:]:
                ema = (alpha_dec * val) + (one_minus_alpha * ema)
            daily_demand = ema
            model_used = f"Exponential Smoothing (EMA, alpha={alpha})"

        daily_demand = max(Decimal("0.00"), daily_demand)
        monthly_demand = max(
            Decimal("0.00"),
            (daily_demand * Decimal(horizon_days)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        )
        daily_demand_rounded = daily_demand.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        return daily_demand_rounded, monthly_demand, model_used

    # ------------------------------------------------------------------
    # Stock-health analysis & deduplicated alerts
    # ------------------------------------------------------------------
    def _compute_stock_health(
        self,
        shop_id: int,
        product: Product,
        daily_series: List[Decimal],
        active_sales_days: int,
        total_sold: Decimal,
        predicted_daily_demand: Decimal,
        as_of_date: date,
    ) -> StockHealthMetrics:
        history_days = len(daily_series)
        avg_daily = (
            (total_sold / Decimal(history_days)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if history_days > 0
            else Decimal("0.00")
        )
        phys_stock, _, avail_stock = self._get_shop_inventory_quantities(shop_id, product.product_id)
        in_transit = self.get_in_transit_stock(shop_id, product.product_id)
        safety_stock = Decimal(str(product.reorder_threshold)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        # Determine whether there is enough historical observation to classify dead stock
        earliest_shop_sale = self.repo.get_earliest_completed_sale_date(shop_id)
        earliest_prod_sale = self.repo.get_earliest_completed_sale_date(shop_id, product_id=product.product_id)
        observation_span_days = 0
        if earliest_shop_sale is not None:
            observation_span_days = max(observation_span_days, (as_of_date - earliest_shop_sale).days + 1)
        if earliest_prod_sale is not None:
            observation_span_days = max(observation_span_days, (as_of_date - earliest_prod_sale).days + 1)

        has_sufficient_inactivity_history = (
            history_days >= self.DEAD_STOCK_INACTIVITY_DAYS
            and observation_span_days >= self.DEAD_STOCK_INACTIVITY_DAYS
        )
        has_sufficient_history = active_sales_days >= self.MIN_ACTIVE_DAYS_FOR_TREND or has_sufficient_inactivity_history

        # 1. Dead stock: substantial inventory on hand, zero sales over inactivity window, sufficient history
        is_dead_stock = (
            phys_stock > Decimal("0.00")
            and total_sold == Decimal("0.00")
            and has_sufficient_inactivity_history
        )

        # 2. Slow-moving: positive stock, some sales, but low average daily turnover
        is_slow_moving = (
            not is_dead_stock
            and phys_stock > Decimal("0.00")
            and total_sold > Decimal("0.00")
            and avg_daily <= self.SLOW_MOVING_MAX_DAILY_AVG
        )

        # 3. Increasing demand: recent half significantly exceeds earlier half
        is_increasing_demand = False
        if active_sales_days >= self.MIN_ACTIVE_DAYS_FOR_TREND and history_days >= 4:
            mid = history_days // 2
            first_half = daily_series[:mid]
            second_half = daily_series[mid:]
            first_avg = sum(first_half, Decimal("0.00")) / Decimal(len(first_half))
            second_avg = sum(second_half, Decimal("0.00")) / Decimal(len(second_half))
            if first_avg > Decimal("0.00") and second_avg >= first_avg * self.INCREASING_DEMAND_GROWTH_RATIO:
                is_increasing_demand = True

        # 4. Approaching stockout: active forecasted demand with low available + in-transit cover
        is_approaching_stockout = False
        if predicted_daily_demand > Decimal("0.00"):
            effective_cover = avail_stock + in_transit
            threshold_cover = predicted_daily_demand * self.STOCKOUT_DAYS_COVER_THRESHOLD
            if effective_cover <= threshold_cover or avail_stock <= safety_stock:
                is_approaching_stockout = True

        if is_dead_stock:
            health_status = "DEAD_STOCK"
        elif is_approaching_stockout:
            health_status = "APPROACHING_STOCKOUT"
        elif is_slow_moving:
            health_status = "SLOW_MOVING"
        elif is_increasing_demand:
            health_status = "INCREASING_DEMAND"
        elif total_sold == Decimal("0.00"):
            health_status = "INSUFFICIENT_HISTORY"
        else:
            health_status = "HEALTHY"

        return StockHealthMetrics(
            history_days=history_days,
            total_units_sold=total_sold.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
            active_sales_days=active_sales_days,
            average_daily_sales=avg_daily,
            available_stock=avail_stock,
            physical_stock=phys_stock,
            in_transit_stock=in_transit,
            has_sufficient_history=has_sufficient_history,
            is_dead_stock=is_dead_stock,
            is_slow_moving=is_slow_moving,
            is_increasing_demand=is_increasing_demand,
            is_approaching_stockout=is_approaching_stockout,
            stock_health_status=health_status,
        )

    def _ensure_stock_health_alerts(self, shop_id: int, product: Product, health: StockHealthMetrics) -> None:
        """Create UNREAD stock-health alerts without generating duplicates."""
        alerts_to_ensure: List[Tuple[str, str]] = []
        if health.is_dead_stock:
            alerts_to_ensure.append((
                "DEAD_STOCK",
                (
                    f"Dead stock detected for '{product.product_name}': "
                    f"{health.physical_stock} units on hand with 0 sales over the last {health.history_days} days."
                ),
            ))
        elif health.is_slow_moving:
            alerts_to_ensure.append((
                "SLOW_MOVING",
                (
                    f"Slow-moving stock detected for '{product.product_name}': "
                    f"average {health.average_daily_sales} units/day with {health.available_stock} units available."
                ),
            ))
        if health.is_approaching_stockout:
            alerts_to_ensure.append((
                "STOCKOUT_RISK",
                (
                    f"Stockout risk for '{product.product_name}': "
                    f"available ({health.available_stock}) + in-transit ({health.in_transit_stock}) is low relative to projected demand."
                ),
            ))

        for alert_type, message in alerts_to_ensure:
            existing = (
                self.db.query(Alert)
                .filter(
                    Alert.location_id == shop_id,
                    Alert.product_id == product.product_id,
                    Alert.alert_type == alert_type,
                    Alert.status == "UNREAD",
                )
                .first()
            )
            if not existing:
                self.db.add(
                    Alert(
                        location_id=shop_id,
                        product_id=product.product_id,
                        alert_type=alert_type,
                        message=message,
                        status="UNREAD",
                    )
                )

    # ------------------------------------------------------------------
    # Public Service API
    # ------------------------------------------------------------------
    def generate_forecast(
        self,
        req: ForecastGenerateRequest,
        actor: Optional[User] = None,
    ) -> ForecastResponse:
        self._authorize_forecast_write(actor, req.shop_id)

        model_name = req.model_preference.strip().upper() if req.model_preference else "AUTO"
        if model_name not in VALID_FORECAST_MODELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model_preference '{model_name}'. Must be one of: {', '.join(sorted(VALID_FORECAST_MODELS))}.",
            )

        history_days = req.history_days if req.history_days is not None else self.DEFAULT_HISTORY_DAYS
        if history_days < self.MIN_HISTORY_DAYS or history_days > self.MAX_HISTORY_DAYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"history_days must be between {self.MIN_HISTORY_DAYS} and {self.MAX_HISTORY_DAYS}.",
            )

        alpha = req.alpha if req.alpha is not None else 0.3
        if alpha <= 0.0 or alpha > 1.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="EMA alpha must be greater than 0 and at most 1.0.",
            )

        horizon_days = self._resolve_horizon_days(req.forecast_period, req.forecast_days)

        try:
            shop, product = self._validate_shop_and_product(req.shop_id, req.product_id)

            as_of_date = datetime.now(timezone.utc).date()
            daily_series, active_days, total_sold, _ = self.repo.get_daily_sales_series(
                req.shop_id,
                req.product_id,
                days=history_days,
                end_date=as_of_date,
            )

            daily_demand, monthly_demand, selected_model = self._compute_daily_and_monthly_demand(
                daily_series=daily_series,
                active_sales_days=active_days,
                model_preference=model_name,
                alpha=alpha,
                horizon_days=horizon_days,
            )

            health = self._compute_stock_health(
                shop_id=req.shop_id,
                product=product,
                daily_series=daily_series,
                active_sales_days=active_days,
                total_sold=total_sold,
                predicted_daily_demand=daily_demand,
                as_of_date=as_of_date,
            )
            self._ensure_stock_health_alerts(req.shop_id, product, health)

            # Avoid misleading duplicate records when latest persisted forecast for this period is identical;
            # otherwise preserve historical forecast records with a strictly monotonic generated_at.
            created_new_forecast = False
            latest_existing = self.repo.get_latest(req.shop_id, req.product_id, req.forecast_period)
            if (
                latest_existing is not None
                and Decimal(str(latest_existing.forecasted_demand)).quantize(TWO_PLACES) == monthly_demand
                and latest_existing.model_used == selected_model
            ):
                forecast = latest_existing
                self.db.commit()
                self.db.refresh(forecast)
            else:
                gen_at = datetime.now(timezone.utc)
                if latest_existing is not None and latest_existing.generated_at is not None:
                    prev_ts = latest_existing.generated_at
                    if prev_ts.tzinfo is None:
                        prev_ts = prev_ts.replace(tzinfo=timezone.utc)
                    if gen_at <= prev_ts:
                        gen_at = prev_ts + timedelta(microseconds=1)

                forecast = Forecast(
                    shop_id=req.shop_id,
                    product_id=req.product_id,
                    forecasted_demand=monthly_demand,
                    forecast_period=req.forecast_period,
                    model_used=selected_model,
                    generated_at=gen_at,
                )
                self.db.add(forecast)
                self.db.commit()
                self.db.refresh(forecast)
                created_new_forecast = True
        except Exception:
            self.db.rollback()
            raise

        if created_new_forecast:
            AuditLogService.log_event(
                event_type="FORECAST_GENERATED",
                actor_id=actor.user_id if actor else None,
                actor_role=actor.role if actor else None,
                entity_type="FORECAST",
                entity_id=forecast.forecast_id,
                location_id=req.shop_id,
                details={
                    "product_id": req.product_id,
                    "forecast_period": req.forecast_period.isoformat(),
                    "model_used": forecast.model_used,
                    "forecasted_demand": str(forecast.forecasted_demand),
                    "horizon_days": horizon_days,
                },
            )

        safety_stock = Decimal(str(product.reorder_threshold)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        recommended_qty = max(
            Decimal("0.00"),
            monthly_demand + safety_stock - health.available_stock - health.in_transit_stock,
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        return ForecastResponse(
            forecast_id=forecast.forecast_id,
            shop_id=forecast.shop_id,
            product_id=forecast.product_id,
            forecasted_demand=Decimal(str(forecast.forecasted_demand)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
            forecast_period=forecast.forecast_period,
            model_used=forecast.model_used,
            generated_at=forecast.generated_at,
            product_name=product.product_name,
            shop_name=shop.location_name,
            forecast_horizon_days=horizon_days,
            predicted_daily_demand=daily_demand,
            available_stock=health.available_stock,
            in_transit_stock=health.in_transit_stock,
            recommended_reorder_quantity=recommended_qty,
            stock_health_status=health.stock_health_status,
        )

    def get_reorder_recommendation(
        self,
        shop_id: int,
        product_id: int,
        period: date,
        actor: Optional[User] = None,
        history_days: int = DEFAULT_HISTORY_DAYS,
    ) -> ReorderRecommendationResponse:
        self._authorize_forecast_read(actor, shop_id)
        if history_days < self.MIN_HISTORY_DAYS or history_days > self.MAX_HISTORY_DAYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"history_days must be between {self.MIN_HISTORY_DAYS} and {self.MAX_HISTORY_DAYS}.",
            )

        shop, product = self._validate_shop_and_product(shop_id, product_id)
        horizon_days = self._resolve_horizon_days(period)
        as_of_date = datetime.now(timezone.utc).date()

        daily_series, active_days, total_sold, _ = self.repo.get_daily_sales_series(
            shop_id,
            product_id,
            days=history_days,
            end_date=as_of_date,
        )

        # 1. Use latest persisted forecast for this period if available; otherwise compute (and persist if authorized)
        latest_fc = self.repo.get_latest(shop_id, product_id, period)
        if latest_fc is not None:
            fc_demand = Decimal(str(latest_fc.forecasted_demand)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            model_used = latest_fc.model_used
            predicted_daily = (
                (fc_demand / Decimal(horizon_days)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                if horizon_days > 0
                else Decimal("0.00")
            )
        else:
            predicted_daily, fc_demand, model_used = self._compute_daily_and_monthly_demand(
                daily_series=daily_series,
                active_sales_days=active_days,
                model_preference="AUTO",
                alpha=0.3,
                horizon_days=horizon_days,
            )
            # Persist automatically when caller is allowed to write forecasts (SHOP_OWNER / ADMIN / internal)
            if actor is None or actor.role in ("ADMIN", "SHOP_OWNER"):
                try:
                    fc = Forecast(
                        shop_id=shop_id,
                        product_id=product_id,
                        forecasted_demand=fc_demand,
                        forecast_period=period,
                        model_used=model_used,
                        generated_at=datetime.now(timezone.utc),
                    )
                    self.db.add(fc)
                    self.db.commit()
                except Exception:
                    self.db.rollback()
                    raise

        # 2. Safety stock = product reorder threshold
        safety_stock = Decimal(str(product.reorder_threshold)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        # 3. Stock health, available stock, and genuinely IN_TRANSIT stock
        health = self._compute_stock_health(
            shop_id=shop_id,
            product=product,
            daily_series=daily_series,
            active_sales_days=active_days,
            total_sold=total_sold,
            predicted_daily_demand=predicted_daily,
            as_of_date=as_of_date,
        )
        try:
            self._ensure_stock_health_alerts(shop_id, product, health)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        available_stock = health.available_stock
        in_transit_stock = health.in_transit_stock

        # 4. Replenishment formula: max(0, predicted_monthly_demand + safety_stock - available_stock - in_transit_stock)
        reorder_qty = max(
            Decimal("0.00"),
            fc_demand + safety_stock - available_stock - in_transit_stock,
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        breakdown = (
            f"Forecasted Monthly Demand ({fc_demand}) + Safety Stock ({safety_stock}) - "
            f"Available Stock ({available_stock}) - In-Transit Stock ({in_transit_stock}) = {reorder_qty}"
        )

        AuditLogService.log_event(
            event_type="REPLENISHMENT_RECOMMENDED",
            actor_id=actor.user_id if actor else None,
            actor_role=actor.role if actor else None,
            entity_type="FORECAST",
            entity_id=product.product_id,
            location_id=shop_id,
            details={
                "product_id": product.product_id,
                "forecast_period": period.isoformat(),
                "forecasted_demand": str(fc_demand),
                "available_stock": str(available_stock),
                "in_transit_stock": str(in_transit_stock),
                "recommended_reorder_quantity": str(reorder_qty),
                "stock_health_status": health.stock_health_status,
            },
        )

        return ReorderRecommendationResponse(
            shop_id=shop_id,
            product_id=product.product_id,
            product_name=product.product_name,
            forecasted_demand=fc_demand,
            safety_stock=safety_stock,
            available_stock=available_stock,
            incoming_stock=in_transit_stock,
            in_transit_stock=in_transit_stock,
            recommended_reorder_quantity=reorder_qty,
            calculation_breakdown=breakdown,
            forecast_period=period,
            model_used=model_used,
            stock_health_status=health.stock_health_status,
            is_slow_moving=health.is_slow_moving,
            is_dead_stock=health.is_dead_stock,
            is_increasing_demand=health.is_increasing_demand,
            is_approaching_stockout=health.is_approaching_stockout,
        )

    def evaluate_stock_health(
        self,
        shop_id: int,
        product_id: int,
        history_days: int = DEFAULT_HISTORY_DAYS,
        period: Optional[date] = None,
        actor: Optional[User] = None,
    ) -> StockHealthResponse:
        self._authorize_forecast_read(actor, shop_id)
        if history_days < self.MIN_HISTORY_DAYS or history_days > self.MAX_HISTORY_DAYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"history_days must be between {self.MIN_HISTORY_DAYS} and {self.MAX_HISTORY_DAYS}.",
            )

        _, product = self._validate_shop_and_product(shop_id, product_id)
        as_of_date = datetime.now(timezone.utc).date()
        target_period = period or as_of_date
        horizon_days = self._resolve_horizon_days(target_period)

        daily_series, active_days, total_sold, _ = self.repo.get_daily_sales_series(
            shop_id,
            product_id,
            days=history_days,
            end_date=as_of_date,
        )
        predicted_daily, predicted_monthly, _ = self._compute_daily_and_monthly_demand(
            daily_series=daily_series,
            active_sales_days=active_days,
            model_preference="AUTO",
            alpha=0.3,
            horizon_days=horizon_days,
        )
        health = self._compute_stock_health(
            shop_id=shop_id,
            product=product,
            daily_series=daily_series,
            active_sales_days=active_days,
            total_sold=total_sold,
            predicted_daily_demand=predicted_daily,
            as_of_date=as_of_date,
        )
        try:
            self._ensure_stock_health_alerts(shop_id, product, health)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        safety_stock = Decimal(str(product.reorder_threshold)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        recommended_qty = max(
            Decimal("0.00"),
            predicted_monthly + safety_stock - health.available_stock - health.in_transit_stock,
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        return StockHealthResponse(
            shop_id=shop_id,
            product_id=product.product_id,
            product_name=product.product_name,
            history_days=health.history_days,
            total_units_sold=health.total_units_sold,
            active_sales_days=health.active_sales_days,
            average_daily_sales=health.average_daily_sales,
            available_stock=health.available_stock,
            in_transit_stock=health.in_transit_stock,
            forecasted_monthly_demand=predicted_monthly,
            recommended_reorder_quantity=recommended_qty,
            stock_health_status=health.stock_health_status,
            is_slow_moving=health.is_slow_moving,
            is_dead_stock=health.is_dead_stock,
            is_increasing_demand=health.is_increasing_demand,
            is_approaching_stockout=health.is_approaching_stockout,
            has_sufficient_history=health.has_sufficient_history,
        )

    def list(
        self,
        shop_id: Optional[int] = None,
        product_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
        actor: Optional[User] = None,
    ) -> List[ForecastResponse]:
        if start_date is not None and end_date is not None and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be after end_date.",
            )

        scoped_shop_ids: Optional[List[int]] = None
        if actor is not None and actor.role != "ADMIN":
            if actor.role == "SHOP_OWNER":
                if actor.location_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Shop owner is not assigned to a shop.",
                    )
                if shop_id is not None and shop_id != actor.location_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Shop owners can only list forecasts for their own shop.",
                    )
                shop_id = actor.location_id
            elif actor.role == "WAREHOUSE_MANAGER":
                if actor.location_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Warehouse manager is not assigned to a warehouse.",
                    )
                associated_shops = self._get_associated_shop_ids_for_warehouse(actor.location_id)
                if shop_id is not None:
                    if shop_id not in associated_shops:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Warehouse managers cannot access forecasts for unassociated shops.",
                        )
                else:
                    scoped_shop_ids = associated_shops
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{actor.role}' is not authorized to list forecasts.",
                )

        forecasts = self.repo.list(
            shop_id=shop_id,
            shop_ids=scoped_shop_ids,
            product_id=product_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit,
        )

        # Enrich responses with shop/product names and live stock/in-transit snapshots
        responses: List[ForecastResponse] = []
        for fc in forecasts:
            product = fc.product or self.db.query(Product).filter(Product.product_id == fc.product_id).first()
            shop = fc.shop or self.db.query(Location).filter(Location.location_id == fc.shop_id).first()
            _, _, avail = self._get_shop_inventory_quantities(fc.shop_id, fc.product_id)
            in_transit = self.get_in_transit_stock(fc.shop_id, fc.product_id)
            horizon_days = self._resolve_horizon_days(fc.forecast_period)
            fc_demand = Decimal(str(fc.forecasted_demand)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            daily_est = (fc_demand / Decimal(horizon_days)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            safety = Decimal(str(product.reorder_threshold)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP) if product else Decimal("0.00")
            rec_qty = max(Decimal("0.00"), fc_demand + safety - avail - in_transit).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

            responses.append(
                ForecastResponse(
                    forecast_id=fc.forecast_id,
                    shop_id=fc.shop_id,
                    product_id=fc.product_id,
                    forecasted_demand=fc_demand,
                    forecast_period=fc.forecast_period,
                    model_used=fc.model_used,
                    generated_at=fc.generated_at,
                    product_name=product.product_name if product else None,
                    shop_name=shop.location_name if shop else None,
                    forecast_horizon_days=horizon_days,
                    predicted_daily_demand=daily_est,
                    available_stock=avail,
                    in_transit_stock=in_transit,
                    recommended_reorder_quantity=rec_qty,
                )
            )
        return responses
