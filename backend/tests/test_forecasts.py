import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from app.models.inventory import Inventory
from app.models.sale import Sale, SaleItem


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
