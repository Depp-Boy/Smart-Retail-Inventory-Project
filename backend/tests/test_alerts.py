import pytest
from fastapi.testclient import TestClient


def test_create_and_retrieve_alerts(client: TestClient, sample_locations, sample_product, sample_users, auth_headers):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id
    owner = sample_users["shop_owner"]
    headers = auth_headers("shop_owner")

    # 1. Create alert
    payload = {
        "location_id": shop_id,
        "product_id": prod_id,
        "alert_type": "LOW_STOCK",
        "message": "Stock of sunflower oil has dropped below reorder threshold (20 units).",
        "user_id": owner.user_id,
    }
    create_res = client.post("/api/v1/alerts/", headers=headers, json=payload)
    assert create_res.status_code == 201
    alert_id = create_res.json()["alert_id"]
    assert create_res.json()["status"] == "UNREAD"

    # 2. Mark as read
    read_res = client.patch(f"/api/v1/alerts/{alert_id}/read", headers=headers)
    assert read_res.status_code == 200
    assert read_res.json()["status"] == "READ"

    # 3. Dismiss alert
    dismiss_res = client.patch(f"/api/v1/alerts/{alert_id}/dismiss", headers=headers)
    assert dismiss_res.status_code == 200
    assert dismiss_res.json()["status"] == "DISMISSED"
