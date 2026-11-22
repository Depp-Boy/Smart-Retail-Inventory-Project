import pytest
from decimal import Decimal
from fastapi.testclient import TestClient


def test_product_creation(client: TestClient, auth_headers):
    headers = auth_headers("admin")
    payload = {
        "product_name": "Tata Salt 1kg",
        "category": "Grains & Staples",
        "unit": "Packet",
        "price": "28.00",
        "reorder_threshold": "50.00",
        "sku": "SALT-TATA-1KG",
        "cost_price": "22.50",
        "description": "Vacuum evaporated iodized salt",
    }
    res = client.post("/api/v1/products/", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["product_name"] == "Tata Salt 1kg"
    assert data["sku"] == "SALT-TATA-1KG"
    assert float(data["price"]) == 28.00


def test_product_creation_unauthorized_role_rejected(client: TestClient, auth_headers):
    # SHOP_OWNER cannot create global products
    headers = auth_headers("shop_owner")
    payload = {
        "product_name": "Unauthorized Product",
        "unit": "Packet",
        "price": "10.00",
    }
    res = client.post("/api/v1/products/", headers=headers, json=payload)
    assert res.status_code == 403


def test_product_retrieval(client: TestClient, sample_product):
    res = client.get(f"/api/v1/products/{sample_product.product_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["product_id"] == sample_product.product_id
    assert data["sku"] == sample_product.sku


def test_product_not_found(client: TestClient):
    res = client.get("/api/v1/products/999999")
    assert res.status_code == 404


def test_product_list_and_search(client: TestClient, sample_product):
    # Search by partial SKU
    res = client.get("/api/v1/products/?search=OIL-FS")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert items[0]["sku"] == sample_product.sku

    # Filter by category
    cat_res = client.get(f"/api/v1/products/?category={sample_product.category}")
    assert cat_res.status_code == 200
    assert len(cat_res.json()) >= 1


def test_product_update(client: TestClient, auth_headers, sample_product):
    headers = auth_headers("admin")
    res = client.put(
        f"/api/v1/products/{sample_product.product_id}",
        headers=headers,
        json={"price": "155.00", "description": "Updated price after vendor revision"},
    )
    assert res.status_code == 200
    assert float(res.json()["price"]) == 155.00


def test_negative_price_rejected(client: TestClient, auth_headers):
    headers = auth_headers("admin")
    payload = {
        "product_name": "Invalid Price Product",
        "unit": "kg",
        "price": "-10.00",
    }
    res = client.post("/api/v1/products/", headers=headers, json=payload)
    assert res.status_code in (400, 422)


def test_duplicate_sku_rejected(client: TestClient, auth_headers, sample_product):
    headers = auth_headers("admin")
    payload = {
        "product_name": "Another Product With Same SKU",
        "unit": "Piece",
        "price": "50.00",
        "sku": sample_product.sku,  # Duplicate SKU
    }
    res = client.post("/api/v1/products/", headers=headers, json=payload)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]
