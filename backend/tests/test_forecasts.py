import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.models.alert import Alert
from app.models.allocation import OrderAllocation
from app.models.dispatch import Dispatch, DispatchItem
from app.models.forecast import Forecast
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.sale import Sale, SaleItem
from app.repositories.forecast_repository import ForecastRepository
from app.schemas.forecast import ForecastGenerateRequest
from app.services.forecast_service import ForecastService


def seed_sales_history(db_session, shop_id, prod_id):
    # Seed 10 days of sales history: 10, 12, 14, 16, 18, 20, 22, 24, 26, 28
    now = datetime.now(timezone.utc)
    for i in range(10):
        sale_date = now - timedelta(days=(10 - i))
        sale = Sale(shop_id=shop_id, sale_date=sale_date, total_amount=Decimal("100.00"), status="COMPLETED")
        db_session.add(sale)
        db_session.flush()

        item = SaleItem(sale_id=sale.sale_id, product_id=prod_id, quantity=Decimal(str(10 + i * 2)), unit_price=Decimal("10.00"))
        db_session.add(item)
    db_session.commit()


def _add_sale(db_session, shop_id: int, prod_id: int, qty: Decimal, days_ago: int, status_val: str = "COMPLETED"):
    sale_dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    sale = Sale(shop_id=shop_id, sale_date=sale_dt, total_amount=qty * Decimal("10.00"), status=status_val)
    db_session.add(sale)
    db_session.flush()
    db_session.add(SaleItem(sale_id=sale.sale_id, product_id=prod_id, quantity=qty, unit_price=Decimal("10.00")))
    db_session.commit()
    return sale


def test_demand_forecasting_algorithms(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id
    seed_sales_history(db_session, shop_id, prod_id)
    headers = auth_headers("shop_owner")

    # Test SMA
    sma_res = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": str(date.today()), "model_preference": "SMA"},
    )
    assert sma_res.status_code == 201
    assert "SMA" in sma_res.json()["model_used"]
    assert float(sma_res.json()["forecasted_demand"]) > 0

    # Test EMA
    ema_res = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": str(date.today()), "model_preference": "EMA", "alpha": 0.3},
    )
    assert ema_res.status_code == 201
    assert "EMA" in ema_res.json()["model_used"]


def test_reorder_recommendation_calculation(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id
    seed_sales_history(db_session, shop_id, prod_id)

    # Seed current inventory: available = 5
    inv = Inventory(location_id=shop_id, product_id=prod_id, quantity=Decimal("5.00"), reserved_quantity=Decimal("0.00"))
    db_session.add(inv)
    db_session.commit()

    headers = auth_headers("shop_owner")
    res = client.get(
        f"/api/v1/forecasts/reorder-recommendation?shop_id={shop_id}&product_id={prod_id}&period={date.today()}",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert float(data["recommended_reorder_quantity"]) >= 0
    assert "calculation_breakdown" in data


def test_historical_sales_filtering_zero_days_isolation_and_aggregation(
    client: TestClient, sample_locations, sample_product, db_session, auth_headers
):
    shop1_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id

    other_shop = Location(location_name="Other Shop", location_type="SHOP", address="MG Road")
    db_session.add(other_shop)
    db_session.commit()
    db_session.refresh(other_shop)

    # Shop 1: 2 separate completed sale items on day -2 (qty 6 + 4 = 10) and 1 completed sale on day 0 (qty 10)
    # Total completed in 10-day window = 20 across 10 calendar days -> daily avg = 2.00 (8 zero-sales days included!)
    _add_sale(db_session, shop1_id, prod_id, Decimal("6.00"), days_ago=2, status_val="COMPLETED")
    _add_sale(db_session, shop1_id, prod_id, Decimal("4.00"), days_ago=2, status_val="COMPLETED")
    _add_sale(db_session, shop1_id, prod_id, Decimal("10.00"), days_ago=0, status_val="COMPLETED")

    # Noise that MUST be excluded: CANCELLED, REFUNDED, and OTHER SHOP sales
    _add_sale(db_session, shop1_id, prod_id, Decimal("50.00"), days_ago=1, status_val="CANCELLED")
    _add_sale(db_session, shop1_id, prod_id, Decimal("40.00"), days_ago=3, status_val="REFUNDED")
    _add_sale(db_session, other_shop.location_id, prod_id, Decimal("100.00"), days_ago=1, status_val="COMPLETED")

    repo = ForecastRepository(db_session)
    series, active_days, total_sold, _ = repo.get_daily_sales_series(shop1_id, prod_id, days=10)
    assert len(series) == 10
    assert active_days == 2
    assert total_sold == Decimal("20.00")
    assert series.count(Decimal("0.00")) == 8

    # SMA over 10 days = 2.00/day -> for April (30 days) = 60.00 (NOT 10/day * 30 = 300!)
    res = client.post(
        "/api/v1/forecasts/generate",
        headers=auth_headers("shop_owner"),
        json={
            "shop_id": shop1_id,
            "product_id": prod_id,
            "forecast_period": "2026-04-01",
            "model_preference": "SMA",
            "history_days": 10,
        },
    )
    assert res.status_code == 201
    assert Decimal(str(res.json()["forecasted_demand"])) == Decimal("60.00")
    assert Decimal(str(res.json()["predicted_daily_demand"])) == Decimal("2.00")
    assert res.json()["forecast_horizon_days"] == 30


def test_forecast_algorithms_sma_wma_ema_next_month_horizon_and_persistence_dedup(
    client: TestClient, sample_locations, sample_product, db_session, auth_headers
):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id
    headers = auth_headers("shop_owner")

    # Seed exact rising daily series over 10 days: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for offset in range(10):
        qty = Decimal(str(offset + 1))
        days_ago = 9 - offset
        _add_sale(db_session, shop_id, prod_id, qty, days_ago=days_ago)

    # 1. SMA: sum=55, avg=5.50/day -> April (30 days) = 165.00; March (31 days) = 170.50
    sma_apr = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-04-01", "model_preference": "SMA", "history_days": 10},
    )
    assert sma_apr.status_code == 201
    assert Decimal(str(sma_apr.json()["forecasted_demand"])) == Decimal("165.00")

    # Repeated identical generation must NOT create a misleading duplicate row
    sma_apr_repeat = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-04-01", "model_preference": "SMA", "history_days": 10},
    )
    assert sma_apr_repeat.status_code == 201
    assert sma_apr_repeat.json()["forecast_id"] == sma_apr.json()["forecast_id"]

    sma_mar = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-03-01", "model_preference": "SMA", "history_days": 10},
    )
    assert sma_mar.status_code == 201
    assert Decimal(str(sma_mar.json()["forecasted_demand"])) == Decimal("170.50")

    # 2. WMA: weights 1..10, weighted_sum = sum(i^2) = 385, weight_total = 55 -> daily = 7.00 -> April (30 days) = 210.00
    wma_apr = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-04-01", "model_preference": "WMA", "history_days": 10},
    )
    assert wma_apr.status_code == 201
    assert "WMA" in wma_apr.json()["model_used"]
    assert Decimal(str(wma_apr.json()["forecasted_demand"])) == Decimal("210.00")

    # 3. EMA (alpha=0.5): recursive exact Decimal calculation * 30
    ema_val = Decimal("1")
    for k in range(2, 11):
        ema_val = Decimal("0.5") * Decimal(k) + Decimal("0.5") * ema_val
    expected_ema_monthly = (ema_val * Decimal("30")).quantize(Decimal("0.01"))

    ema_apr = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-04-01", "model_preference": "EMA", "alpha": 0.5, "history_days": 10},
    )
    assert ema_apr.status_code == 201
    assert "EMA" in ema_apr.json()["model_used"]
    assert Decimal(str(ema_apr.json()["forecasted_demand"])) == expected_ema_monthly

    # Historical records for April preserved (SMA, WMA, EMA = 3 distinct records), and latest is EMA
    apr_records = db_session.query(Forecast).filter_by(shop_id=shop_id, product_id=prod_id, forecast_period=date(2026, 4, 1)).all()
    assert len(apr_records) == 3
    latest = ForecastRepository(db_session).get_latest(shop_id, prod_id, date(2026, 4, 1))
    assert latest.forecast_id == ema_apr.json()["forecast_id"]


def test_auto_selection_zero_history_and_validation_errors(
    client: TestClient, sample_locations, sample_product, sample_users, db_session, auth_headers
):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id
    headers = auth_headers("shop_owner")

    # 0 sales -> ZERO_HISTORY_BASELINE with 0.00 demand
    zero_res = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-04-01", "model_preference": "AUTO"},
    )
    assert zero_res.status_code == 201
    assert zero_res.json()["model_used"] == "ZERO_HISTORY_BASELINE"
    assert Decimal(str(zero_res.json()["forecasted_demand"])) == Decimal("0.00")

    # 4 active sales days (< 7) -> AUTO chooses SMA
    for d in range(4):
        _add_sale(db_session, shop_id, prod_id, Decimal("5.00"), days_ago=d)
    auto_sma = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-05-01", "model_preference": "AUTO", "history_days": 30},
    )
    assert auto_sma.status_code == 201
    assert "SMA" in auto_sma.json()["model_used"]

    # Add 6 more active days (total 10 active days, 7..13) -> AUTO chooses WMA
    for d in range(4, 10):
        _add_sale(db_session, shop_id, prod_id, Decimal("5.00"), days_ago=d)
    auto_wma = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-06-01", "model_preference": "AUTO", "history_days": 30},
    )
    assert auto_wma.status_code == 201
    assert "WMA" in auto_wma.json()["model_used"]

    # Add 6 more active days (total 16 active days >= 14) -> AUTO chooses EMA
    for d in range(10, 16):
        _add_sale(db_session, shop_id, prod_id, Decimal("5.00"), days_ago=d)
    auto_ema = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-07-01", "model_preference": "AUTO", "history_days": 30},
    )
    assert auto_ema.status_code == 201
    assert "EMA" in auto_ema.json()["model_used"]

    # Invalid algorithm -> 400
    assert client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-04-01", "model_preference": "DEEP_AI"},
    ).status_code == 400

    # Invalid alpha -> 422 over HTTP, 400 in service
    assert client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-04-01", "model_preference": "EMA", "alpha": 0.0},
    ).status_code == 422
    assert client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-04-01", "model_preference": "EMA", "alpha": 1.5},
    ).status_code == 422

    svc = ForecastService(db_session)
    bad_alpha_req = ForecastGenerateRequest.model_construct(
        shop_id=shop_id, product_id=prod_id, forecast_period=date(2026, 4, 1),
        model_preference="EMA", history_days=30, alpha=-0.2, forecast_days=None,
    )
    with pytest.raises(HTTPException) as exc:
        svc.generate_forecast(bad_alpha_req, actor=sample_users["shop_owner"])
    assert exc.value.status_code == 400

    # Non-negative forecast guarantee even with negative synthetic input
    daily, monthly, _ = svc._compute_daily_and_monthly_demand([Decimal("-5.00")], 1, "SMA", 0.3, 30)
    assert daily >= Decimal("0.00")
    assert monthly >= Decimal("0.00")


def test_replenishment_with_stock_reserves_in_transit_and_excluded_dispatches(
    client: TestClient, sample_locations, sample_product, sample_users, db_session, auth_headers
):
    shop_id = sample_locations["shop"].location_id
    wh1_id = sample_locations["warehouse"].location_id
    prod_id = sample_product.product_id  # reorder_threshold (safety_stock) = 20.00
    headers = auth_headers("shop_owner")

    wh2 = Location(location_name="Backup Hub", location_type="SUB_WAREHOUSE", address="Backup Rd")
    db_session.add(wh2)
    db_session.commit()
    db_session.refresh(wh2)

    # Seed constant 4 units/day for 10 days -> April (30 days) predicted_monthly_demand = 120.00
    for d in range(10):
        _add_sale(db_session, shop_id, prod_id, Decimal("4.00"), days_ago=d)

    # Generate SMA forecast explicitly for April -> 120.00
    fc = client.post(
        "/api/v1/forecasts/generate",
        headers=headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-04-01", "model_preference": "SMA", "history_days": 10},
    )
    assert fc.status_code == 201
    assert Decimal(str(fc.json()["forecasted_demand"])) == Decimal("120.00")

    # 1. Zero stock, no dispatches -> 120 + 20 - 0 - 0 = 140.00
    r_zero = client.get(f"/api/v1/forecasts/reorder-recommendation?shop_id={shop_id}&product_id={prod_id}&period=2026-04-01", headers=headers)
    assert r_zero.status_code == 200
    assert Decimal(str(r_zero.json()["recommended_reorder_quantity"])) == Decimal("140.00")

    # 2. Physical=50, Reserved=15 -> Available=35 -> 120 + 20 - 35 - 0 = 105.00
    inv = Inventory(location_id=shop_id, product_id=prod_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("15.00"))
    db_session.add(inv)
    db_session.commit()

    r_res = client.get(f"/api/v1/forecasts/reorder-recommendation?shop_id={shop_id}&product_id={prod_id}&period=2026-04-01", headers=headers)
    assert Decimal(str(r_res.json()["available_stock"])) == Decimal("35.00")
    assert Decimal(str(r_res.json()["recommended_reorder_quantity"])) == Decimal("105.00")

    # 3. Add undispatched allocation, PENDING dispatch, CANCELLED dispatch, DELIVERED dispatch -> NONE count as in-transit!
    order = Order(shop_id=shop_id, status="PROCESSING")
    db_session.add(order)
    db_session.flush()
    oi = OrderItem(order_id=order.order_id, product_id=prod_id, quantity_requested=Decimal("200.00"), quantity_allocated=Decimal("120.00"))
    db_session.add(oi)
    db_session.flush()
    alloc_wh1 = OrderAllocation(order_item_id=oi.order_item_id, source_location_id=wh1_id, allocated_quantity=Decimal("80.00"), status="ALLOCATED")
    alloc_wh2 = OrderAllocation(order_item_id=oi.order_item_id, source_location_id=wh2.location_id, allocated_quantity=Decimal("40.00"), status="ALLOCATED")
    db_session.add_all([alloc_wh1, alloc_wh2])
    db_session.flush()

    for code, st, qty in [
        ("DSP-PEND-1", "PENDING", Decimal("10.00")),
        ("DSP-CANC-1", "CANCELLED", Decimal("25.00")),
        ("DSP-DELV-1", "DELIVERED", Decimal("40.00")),
    ]:
        dsp = Dispatch(dispatch_code=code, order_id=order.order_id, source_location_id=wh1_id, created_by_user_id=sample_users["manager"].user_id, status=st)
        db_session.add(dsp)
        db_session.flush()
        db_session.add(DispatchItem(dispatch_id=dsp.dispatch_id, allocation_id=alloc_wh1.allocation_id, product_id=prod_id, quantity=qty))
    db_session.commit()

    r_excl = client.get(f"/api/v1/forecasts/reorder-recommendation?shop_id={shop_id}&product_id={prod_id}&period=2026-04-01", headers=headers)
    assert Decimal(str(r_excl.json()["incoming_stock"])) == Decimal("0.00")
    assert Decimal(str(r_excl.json()["recommended_reorder_quantity"])) == Decimal("105.00")

    # 4. Add TWO genuinely IN_TRANSIT dispatches across WH1 (20) and WH2 (15) -> incoming = 35 -> 120 + 20 - 35 - 35 = 70.00
    d_t1 = Dispatch(dispatch_code="DSP-TR-1", order_id=order.order_id, source_location_id=wh1_id, created_by_user_id=sample_users["manager"].user_id, status="IN_TRANSIT")
    d_t2 = Dispatch(dispatch_code="DSP-TR-2", order_id=order.order_id, source_location_id=wh2.location_id, created_by_user_id=sample_users["admin"].user_id, status="IN_TRANSIT")
    db_session.add_all([d_t1, d_t2])
    db_session.flush()
    db_session.add_all([
        DispatchItem(dispatch_id=d_t1.dispatch_id, allocation_id=alloc_wh1.allocation_id, product_id=prod_id, quantity=Decimal("20.00")),
        DispatchItem(dispatch_id=d_t2.dispatch_id, allocation_id=alloc_wh2.allocation_id, product_id=prod_id, quantity=Decimal("15.00")),
    ])
    db_session.commit()

    r_transit = client.get(f"/api/v1/forecasts/reorder-recommendation?shop_id={shop_id}&product_id={prod_id}&period=2026-04-01", headers=headers)
    assert Decimal(str(r_transit.json()["incoming_stock"])) == Decimal("35.00")
    assert Decimal(str(r_transit.json()["in_transit_stock"])) == Decimal("35.00")
    assert Decimal(str(r_transit.json()["recommended_reorder_quantity"])) == Decimal("70.00")

    # 5. Excess stock (available = 200) -> recommended_reorder_quantity = 0.00
    inv.quantity = Decimal("215.00")
    inv.reserved_quantity = Decimal("15.00")
    db_session.commit()

    r_excess = client.get(f"/api/v1/forecasts/reorder-recommendation?shop_id={shop_id}&product_id={prod_id}&period=2026-04-01", headers=headers)
    assert Decimal(str(r_excess.json()["recommended_reorder_quantity"])) == Decimal("0.00")


def test_stock_health_dead_slow_increasing_zero_inventory_and_alert_dedup(
    client: TestClient, sample_locations, sample_product, db_session, auth_headers
):
    shop_id = sample_locations["shop"].location_id
    headers = auth_headers("shop_owner")

    p_dead = sample_product
    p_zero = Product(product_name="Zero Inv Item", category="Misc", unit="Unit", price=Decimal("50.00"), reorder_threshold=Decimal("5.00"), sku="ZERO-1")
    p_slow = Product(product_name="Slow Spice", category="Spices", unit="Pack", price=Decimal("60.00"), reorder_threshold=Decimal("5.00"), sku="SLOW-1")
    p_grow = Product(product_name="Trending Juice", category="Beverages", unit="Bottle", price=Decimal("80.00"), reorder_threshold=Decimal("15.00"), sku="GROW-1")
    db_session.add_all([p_zero, p_slow, p_grow])
    db_session.commit()

    # Establish >30 days of shop sales history using an older sale (35 days ago)
    _add_sale(db_session, shop_id, p_slow.product_id, Decimal("2.00"), days_ago=35)

    # Seed inventories
    db_session.add_all([
        Inventory(location_id=shop_id, product_id=p_dead.product_id, quantity=Decimal("40.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=shop_id, product_id=p_zero.product_id, quantity=Decimal("0.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=shop_id, product_id=p_slow.product_id, quantity=Decimal("30.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=shop_id, product_id=p_grow.product_id, quantity=Decimal("10.00"), reserved_quantity=Decimal("0.00")),
    ])
    db_session.commit()

    # Slow product: 3 units over 30 days -> 0.10/day <= 0.50
    _add_sale(db_session, shop_id, p_slow.product_id, Decimal("3.00"), days_ago=5)

    # Increasing demand + stockout risk: earlier half 2/day, recent half 8/day
    for d in range(15, 30):
        _add_sale(db_session, shop_id, p_grow.product_id, Decimal("2.00"), days_ago=d)
    for d in range(0, 15):
        _add_sale(db_session, shop_id, p_grow.product_id, Decimal("8.00"), days_ago=d)

    # 1. Dead stock detected & alert deduplicated across repeated calls
    h_dead1 = client.get(f"/api/v1/forecasts/stock-health?shop_id={shop_id}&product_id={p_dead.product_id}&history_days=30", headers=headers)
    h_dead2 = client.get(f"/api/v1/forecasts/stock-health?shop_id={shop_id}&product_id={p_dead.product_id}&history_days=30", headers=headers)
    assert h_dead1.status_code == 200 and h_dead2.status_code == 200
    assert h_dead1.json()["is_dead_stock"] is True
    assert h_dead1.json()["stock_health_status"] == "DEAD_STOCK"
    dead_alerts = db_session.query(Alert).filter_by(location_id=shop_id, product_id=p_dead.product_id, alert_type="DEAD_STOCK").all()
    assert len(dead_alerts) == 1  # No duplicate alert created

    # 2. Zero-inventory product is NOT falsely flagged as dead stock
    h_zero = client.get(f"/api/v1/forecasts/stock-health?shop_id={shop_id}&product_id={p_zero.product_id}&history_days=30", headers=headers)
    assert h_zero.status_code == 200
    assert h_zero.json()["is_dead_stock"] is False

    # 3. Slow-moving product detected
    h_slow = client.get(f"/api/v1/forecasts/stock-health?shop_id={shop_id}&product_id={p_slow.product_id}&history_days=30", headers=headers)
    assert h_slow.status_code == 200
    assert h_slow.json()["is_slow_moving"] is True
    assert h_slow.json()["stock_health_status"] == "SLOW_MOVING"

    # 4. Increasing demand & approaching stockout detected
    h_grow = client.get(f"/api/v1/forecasts/stock-health?shop_id={shop_id}&product_id={p_grow.product_id}&history_days=30", headers=headers)
    assert h_grow.status_code == 200
    assert h_grow.json()["is_increasing_demand"] is True
    assert h_grow.json()["is_approaching_stockout"] is True

    # 5. Brand-new shop with insufficient history is NOT flagged as dead stock
    new_shop = Location(location_name="Brand New Shop", location_type="SHOP", address="New Street")
    db_session.add(new_shop)
    db_session.commit()
    db_session.add(Inventory(location_id=new_shop.location_id, product_id=p_dead.product_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00")))
    db_session.commit()

    h_new = client.get(
        f"/api/v1/forecasts/stock-health?shop_id={new_shop.location_id}&product_id={p_dead.product_id}&history_days=30",
        headers=auth_headers("admin"),
    )
    assert h_new.status_code == 200
    assert h_new.json()["has_sufficient_history"] is False
    assert h_new.json()["is_dead_stock"] is False
    assert h_new.json()["stock_health_status"] == "INSUFFICIENT_HISTORY"


def test_forecast_authorization_across_roles_and_shops(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop1_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id

    unlinked_shop = Location(location_name="Unlinked Shop 2", location_type="SHOP", address="Far Road")
    db_session.add(unlinked_shop)
    db_session.commit()
    db_session.refresh(unlinked_shop)

    shop1_h = auth_headers("shop_owner")
    mgr_h = auth_headers("manager")
    worker_h = auth_headers("worker")
    admin_h = auth_headers("admin")

    # Shop 1 owner cannot generate, list, or view recommendations/health for Shop 2
    assert client.post(
        "/api/v1/forecasts/generate",
        headers=shop1_h,
        json={"shop_id": unlinked_shop.location_id, "product_id": prod_id, "forecast_period": "2026-04-01"},
    ).status_code == 403
    assert client.get(f"/api/v1/forecasts/?shop_id={unlinked_shop.location_id}", headers=shop1_h).status_code == 403
    assert client.get(f"/api/v1/forecasts/reorder-recommendation?shop_id={unlinked_shop.location_id}&product_id={prod_id}", headers=shop1_h).status_code == 403
    assert client.get(f"/api/v1/forecasts/stock-health?shop_id={unlinked_shop.location_id}&product_id={prod_id}", headers=shop1_h).status_code == 403

    # Warehouse worker cannot generate or read forecasts
    assert client.post(
        "/api/v1/forecasts/generate",
        headers=worker_h,
        json={"shop_id": shop1_id, "product_id": prod_id, "forecast_period": "2026-04-01"},
    ).status_code == 403
    assert client.get("/api/v1/forecasts/", headers=worker_h).status_code == 403
    assert client.get(f"/api/v1/forecasts/reorder-recommendation?shop_id={shop1_id}&product_id={prod_id}", headers=worker_h).status_code == 403

    # Warehouse manager cannot generate forecasts or read unassociated shop forecasts
    assert client.post(
        "/api/v1/forecasts/generate",
        headers=mgr_h,
        json={"shop_id": shop1_id, "product_id": prod_id, "forecast_period": "2026-04-01"},
    ).status_code == 403
    assert client.get(f"/api/v1/forecasts/?shop_id={unlinked_shop.location_id}", headers=mgr_h).status_code == 403
    assert client.get(f"/api/v1/forecasts/reorder-recommendation?shop_id={unlinked_shop.location_id}&product_id={prod_id}", headers=mgr_h).status_code == 403

    # Warehouse manager CAN read associated Shop 1's forecasts/recommendations
    assert client.get(f"/api/v1/forecasts/?shop_id={shop1_id}", headers=mgr_h).status_code == 200
    assert client.get(f"/api/v1/forecasts/reorder-recommendation?shop_id={shop1_id}&product_id={prod_id}", headers=mgr_h).status_code == 200

    # Admin can generate and read across both shops
    assert client.post(
        "/api/v1/forecasts/generate",
        headers=admin_h,
        json={"shop_id": unlinked_shop.location_id, "product_id": prod_id, "forecast_period": "2026-04-01"},
    ).status_code == 201
    assert client.get(f"/api/v1/forecasts/reorder-recommendation?shop_id={unlinked_shop.location_id}&product_id={prod_id}", headers=admin_h).status_code == 200
