import pytest
from decimal import Decimal
from fastapi.testclient import TestClient


def test_create_order_with_multiple_items(client: TestClient, sample_locations, sample_product, auth_headers, db_session):
    shop_id = sample_locations["shop"].location_id
    headers = auth_headers("shop_owner")

    payload = {
        "shop_id": shop_id,
        "items": [
            {"product_id": sample_product.product_id, "quantity_requested": "25.00"}
        ],
    }
    res = client.post("/api/v1/orders/", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["shop_id"] == shop_id
    assert data["status"] == "PENDING"
    assert len(data["items"]) == 1
    assert float(data["items"][0]["quantity_requested"]) == 25.00
    assert float(data["items"][0]["quantity_allocated"]) == 0.00  # Starts with 0 allocation


def test_order_retrieval_and_listing(client: TestClient, sample_locations, sample_product, auth_headers):
    shop_id = sample_locations["shop"].location_id
    headers = auth_headers("shop_owner")

    # Create an order first
    create_res = client.post(
        "/api/v1/orders/",
        headers=headers,
        json={"shop_id": shop_id, "items": [{"product_id": sample_product.product_id, "quantity_requested": "15.00"}]},
    )
    assert create_res.status_code == 201

    res = client.get("/api/v1/orders/?status=PENDING", headers=headers)
    assert res.status_code == 200
    orders = res.json()
    assert len(orders) >= 1
    order_id = orders[0]["order_id"]

    # Retrieve order by ID
    detail_res = client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["order_id"] == order_id


def test_order_cancellation(client: TestClient, sample_locations, sample_product, auth_headers):
    shop_id = sample_locations["shop"].location_id
    headers = auth_headers("shop_owner")

    # Create order
    create_res = client.post(
        "/api/v1/orders/",
        headers=headers,
        json={"shop_id": shop_id, "items": [{"product_id": sample_product.product_id, "quantity_requested": "10.00"}]},
    )
    order_id = create_res.json()["order_id"]

    # Cancel order
    cancel_res = client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Cannot cancel already cancelled order
    repeat_res = client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert repeat_res.status_code == 400
