import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.core.security import create_access_token, hash_password
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.product import Product
from app.models.user import User
from app.services.inventory_service import InventoryService


def test_inventory_retrieval_and_available_calculation(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id

    # Seed inventory: 100 physical, 15 reserved -> 85 available
    inv = Inventory(
        location_id=shop_id,
        product_id=prod_id,
        quantity=Decimal("100.00"),
        reserved_quantity=Decimal("15.00"),
    )
    db_session.add(inv)
    db_session.commit()

    headers = auth_headers("shop_owner")
    res = client.get(f"/api/v1/inventory/locations/{shop_id}", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    record = items[0]
    assert float(record["quantity"]) == 100.00
    assert float(record["reserved_quantity"]) == 15.00
    assert float(record["available_quantity"]) == 85.00  # Formula: quantity - reserved_quantity


def test_inventory_summary_kpis(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    headers = auth_headers("shop_owner")

    res = client.get(f"/api/v1/inventory/locations/{shop_id}/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_products_count" in data
    assert "total_physical_quantity" in data
    assert "total_reserved_quantity" in data
    assert "total_available_quantity" in data
    assert "low_stock_count" in data
    assert "out_of_stock_count" in data


def test_low_stock_filtering(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    # Reorder threshold for sample_product is 20.00. Set quantity to 15.00 (low stock)
    inv = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=sample_product.product_id).first()
    if inv:
        inv.quantity = Decimal("15.00")
    else:
        inv = Inventory(location_id=shop_id, product_id=sample_product.product_id, quantity=Decimal("15.00"), reserved_quantity=Decimal("0.00"))
        db_session.add(inv)
    db_session.commit()

    headers = auth_headers("shop_owner")
    res = client.get(f"/api/v1/inventory/locations/{shop_id}?low_stock=true", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["product_id"] == sample_product.product_id


def test_controlled_stock_adjustment_rules(db_session, sample_locations, sample_product):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id
    service = InventoryService(db_session)

    # Adding 50 units
    inv = service.adjust_stock_controlled(shop_id, prod_id, Decimal("50.00"))
    assert inv.quantity == Decimal("50.00")

    # Cannot deduct below zero
    with pytest.raises(Exception):
        service.adjust_stock_controlled(shop_id, prod_id, Decimal("-100.00"))


def test_low_stock_and_out_of_stock_use_available_quantity(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    wh_id = sample_locations["warehouse"].location_id
    prod_a = sample_product  # reorder_threshold = 20.00
    prod_b = Product(product_name="Basmati Rice 5kg", category="Grains", unit="Bag", price=Decimal("520.00"), reorder_threshold=Decimal("10.00"), sku="RICE-5KG")
    prod_c = Product(product_name="Tata Salt 1kg", category="Essentials", unit="Pack", price=Decimal("28.00"), reorder_threshold=Decimal("10.00"), sku="SALT-1KG")
    db_session.add_all([prod_b, prod_c])
    db_session.commit()
    db_session.refresh(prod_b)
    db_session.refresh(prod_c)

    # Prod A: physical=50 > threshold(20), BUT reserved=40 -> available=10 <= 20 (LOW STOCK!)
    # Prod B: physical=30 > threshold(10), BUT reserved=30 -> available=0 <= 0 (OUT OF STOCK & LOW STOCK!)
    # Prod C: physical=40, reserved=5 -> available=35 > 10 (HEALTHY!)
    db_session.add_all([
        Inventory(location_id=wh_id, product_id=prod_a.product_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("40.00")),
        Inventory(location_id=wh_id, product_id=prod_b.product_id, quantity=Decimal("30.00"), reserved_quantity=Decimal("30.00")),
        Inventory(location_id=wh_id, product_id=prod_c.product_id, quantity=Decimal("40.00"), reserved_quantity=Decimal("5.00")),
    ])
    db_session.commit()

    headers = auth_headers("manager")

    low_res = client.get(f"/api/v1/inventory/locations/{wh_id}?low_stock=true", headers=headers)
    assert low_res.status_code == 200
    low_ids = {item["product_id"] for item in low_res.json()}
    assert low_ids == {prod_a.product_id, prod_b.product_id}

    oos_res = client.get(f"/api/v1/inventory/locations/{wh_id}?out_of_stock=true", headers=headers)
    assert oos_res.status_code == 200
    oos_ids = {item["product_id"] for item in oos_res.json()}
    assert oos_ids == {prod_b.product_id}

    summary_res = client.get(f"/api/v1/inventory/locations/{wh_id}/summary", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_products_count"] == 3
    assert float(summary["total_physical_quantity"]) == 120.00
    assert float(summary["total_reserved_quantity"]) == 75.00
    assert float(summary["total_available_quantity"]) == 45.00
    assert summary["low_stock_count"] == 2
    assert summary["out_of_stock_count"] == 1


def test_inventory_listing_search_and_pagination(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    wh_id = sample_locations["warehouse"].location_id
    p2 = Product(product_name="Aashirvaad Atta 5kg", category="Flour", unit="Bag", price=Decimal("260.00"), reorder_threshold=Decimal("10.00"), sku="ATTA-5KG")
    p3 = Product(product_name="Amul Butter 500g", category="Dairy", unit="Box", price=Decimal("285.00"), reorder_threshold=Decimal("10.00"), sku="BUTTER-500G")
    db_session.add_all([p2, p3])
    db_session.commit()

    db_session.add_all([
        Inventory(location_id=wh_id, product_id=sample_product.product_id, quantity=Decimal("30.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=wh_id, product_id=p2.product_id, quantity=Decimal("40.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=wh_id, product_id=p3.product_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00")),
    ])
    db_session.commit()

    headers = auth_headers("manager")

    # Search by product name / SKU
    search_res = client.get(f"/api/v1/inventory/locations/{wh_id}?search=ATTA-5KG", headers=headers)
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1
    assert search_res.json()[0]["product_id"] == p2.product_id

    # Pagination
    page1 = client.get(f"/api/v1/inventory/locations/{wh_id}?skip=0&limit=2", headers=headers)
    page2 = client.get(f"/api/v1/inventory/locations/{wh_id}?skip=2&limit=2", headers=headers)
    assert page1.status_code == 200 and len(page1.json()) == 2
    assert page2.status_code == 200 and len(page2.json()) == 1


def test_adjustment_cannot_go_below_reserved_validates_delta_and_avoids_duplicates(
    client: TestClient, sample_locations, sample_product, db_session, auth_headers
):
    wh_id = sample_locations["warehouse"].location_id
    prod_id = sample_product.product_id
    headers = auth_headers("manager")

    # Seed physical=50, reserved=30
    db_session.add(Inventory(location_id=wh_id, product_id=prod_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("30.00")))
    db_session.commit()

    # Zero adjustment rejected
    zero_res = client.post(f"/api/v1/inventory/locations/{wh_id}/adjust", headers=headers, json={"product_id": prod_id, "delta": "0.00"})
    assert zero_res.status_code == 400

    # Adjustment reducing physical below reserved (50 - 25 = 25 < 30) rejected
    below_res = client.post(f"/api/v1/inventory/locations/{wh_id}/adjust", headers=headers, json={"product_id": prod_id, "delta": "-25.00"})
    assert below_res.status_code == 400
    assert "reserved quantity" in below_res.json()["detail"].lower()

    # Adjustment reducing physical below zero rejected
    below_zero = client.post(f"/api/v1/inventory/locations/{wh_id}/adjust", headers=headers, json={"product_id": prod_id, "delta": "-60.00"})
    assert below_zero.status_code == 400

    # Valid negative adjustment down to reserved boundary (50 - 20 = 30 == reserved) succeeds
    exact_res = client.post(f"/api/v1/inventory/locations/{wh_id}/adjust", headers=headers, json={"product_id": prod_id, "delta": "-20.00"})
    assert exact_res.status_code == 200
    assert float(exact_res.json()["quantity"]) == 30.00
    assert float(exact_res.json()["available_quantity"]) == 0.00

    # Repeated positive adjustments update existing row without creating duplicates
    assert client.post(f"/api/v1/inventory/locations/{wh_id}/adjust", headers=headers, json={"product_id": prod_id, "delta": "15.00"}).status_code == 200
    assert client.post(f"/api/v1/inventory/locations/{wh_id}/adjust", headers=headers, json={"product_id": prod_id, "delta": "5.00"}).status_code == 200

    db_session.expire_all()
    rows = db_session.query(Inventory).filter_by(location_id=wh_id, product_id=prod_id).all()
    assert len(rows) == 1
    assert float(rows[0].quantity) == 50.00
    assert float(rows[0].reserved_quantity) == 30.00

    # Non-existent product returns 404
    assert client.post(f"/api/v1/inventory/locations/{wh_id}/adjust", headers=headers, json={"product_id": 999999, "delta": "5.00"}).status_code == 404


def test_inventory_authorization_across_roles_and_locations(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    wh1_id = sample_locations["warehouse"].location_id
    shop1_id = sample_locations["shop"].location_id

    wh2 = Location(location_name="South Warehouse", location_type="SUB_WAREHOUSE", address="Hosur Rd")
    shop2 = Location(location_name="Jayanagar Store", location_type="SHOP", address="4th Block Jayanagar")
    db_session.add_all([wh2, shop2])
    db_session.commit()
    db_session.refresh(wh2)
    db_session.refresh(shop2)

    db_session.add_all([
        Inventory(location_id=wh1_id, product_id=sample_product.product_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=wh2.location_id, product_id=sample_product.product_id, quantity=Decimal("60.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=shop1_id, product_id=sample_product.product_id, quantity=Decimal("25.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=shop2.location_id, product_id=sample_product.product_id, quantity=Decimal("35.00"), reserved_quantity=Decimal("0.00")),
    ])
    db_session.commit()

    shop_headers = auth_headers("shop_owner")
    mgr_headers = auth_headers("manager")
    worker_headers = auth_headers("worker")
    admin_headers = auth_headers("admin")

    # SHOP_OWNER: allowed for shop1, forbidden for shop2 and wh1
    assert client.get(f"/api/v1/inventory/locations/{shop1_id}", headers=shop_headers).status_code == 200
    assert client.post(f"/api/v1/inventory/locations/{shop1_id}/adjust", headers=shop_headers, json={"product_id": sample_product.product_id, "delta": "5.00"}).status_code == 200
    assert client.get(f"/api/v1/inventory/locations/{shop2.location_id}", headers=shop_headers).status_code == 403
    assert client.get(f"/api/v1/inventory/locations/{shop2.location_id}/summary", headers=shop_headers).status_code == 403
    assert client.post(f"/api/v1/inventory/locations/{shop2.location_id}/adjust", headers=shop_headers, json={"product_id": sample_product.product_id, "delta": "5.00"}).status_code == 403
    assert client.get(f"/api/v1/inventory/?location_id={wh1_id}", headers=shop_headers).status_code == 403

    # WAREHOUSE_MANAGER: allowed for wh1, forbidden for wh2 and shop1
    assert client.get(f"/api/v1/inventory/locations/{wh1_id}", headers=mgr_headers).status_code == 200
    assert client.post(f"/api/v1/inventory/locations/{wh1_id}/adjust", headers=mgr_headers, json={"product_id": sample_product.product_id, "delta": "10.00"}).status_code == 200
    assert client.get(f"/api/v1/inventory/locations/{wh2.location_id}", headers=mgr_headers).status_code == 403
    assert client.get(f"/api/v1/inventory/locations/{wh2.location_id}/summary", headers=mgr_headers).status_code == 403
    assert client.post(f"/api/v1/inventory/locations/{wh2.location_id}/adjust", headers=mgr_headers, json={"product_id": sample_product.product_id, "delta": "10.00"}).status_code == 403
    assert client.post(f"/api/v1/inventory/locations/{shop1_id}/adjust", headers=mgr_headers, json={"product_id": sample_product.product_id, "delta": "5.00"}).status_code == 403

    # WAREHOUSE_WORKER: can view own warehouse, forbidden from other warehouses and forbidden from adjusting stock
    assert client.get(f"/api/v1/inventory/locations/{wh1_id}", headers=worker_headers).status_code == 200
    assert client.get(f"/api/v1/inventory/locations/{wh2.location_id}", headers=worker_headers).status_code == 403
    assert client.post(f"/api/v1/inventory/locations/{wh1_id}/adjust", headers=worker_headers, json={"product_id": sample_product.product_id, "delta": "5.00"}).status_code == 403

    # ADMIN: unrestricted access across all locations
    assert client.get(f"/api/v1/inventory/locations/{wh2.location_id}", headers=admin_headers).status_code == 200
    assert client.get(f"/api/v1/inventory/locations/{shop2.location_id}/summary", headers=admin_headers).status_code == 200
    assert client.post(f"/api/v1/inventory/locations/{wh2.location_id}/adjust", headers=admin_headers, json={"product_id": sample_product.product_id, "delta": "10.00"}).status_code == 200


def test_inventory_summary_and_listing_reflect_sales_immediately(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id  # reorder_threshold = 20.00
    db_session.add(Inventory(location_id=shop_id, product_id=prod_id, quantity=Decimal("25.00"), reserved_quantity=Decimal("0.00")))
    db_session.commit()

    headers = auth_headers("shop_owner")

    # Initially healthy (25 > 20)
    s0 = client.get(f"/api/v1/inventory/locations/{shop_id}/summary", headers=headers).json()
    assert float(s0["total_available_quantity"]) == 25.00
    assert s0["low_stock_count"] == 0
    assert s0["out_of_stock_count"] == 0

    # Sell 10 -> drops to 15 (low stock)
    assert client.post("/api/v1/sales/", headers=headers, json={"items": [{"product_id": prod_id, "quantity": "10.00"}]}).status_code == 201
    s1 = client.get(f"/api/v1/inventory/locations/{shop_id}/summary", headers=headers).json()
    assert float(s1["total_physical_quantity"]) == 15.00
    assert float(s1["total_available_quantity"]) == 15.00
    assert s1["low_stock_count"] == 1
    assert s1["out_of_stock_count"] == 0
    assert len(client.get(f"/api/v1/inventory/locations/{shop_id}?low_stock=true", headers=headers).json()) == 1

    # Sell remaining 15 -> drops to 0 (out of stock)
    sale2 = client.post("/api/v1/sales/", headers=headers, json={"items": [{"product_id": prod_id, "quantity": "15.00"}]})
    assert sale2.status_code == 201
    s2 = client.get(f"/api/v1/inventory/locations/{shop_id}/summary", headers=headers).json()
    assert float(s2["total_physical_quantity"]) == 0.00
    assert float(s2["total_available_quantity"]) == 0.00
    assert s2["low_stock_count"] == 1
    assert s2["out_of_stock_count"] == 1
    assert len(client.get(f"/api/v1/inventory/locations/{shop_id}?out_of_stock=true", headers=headers).json()) == 1

    # Cancel second sale -> immediately restored to 15 (no longer out of stock)
    assert client.post(f"/api/v1/sales/{sale2.json()['sale_id']}/cancel", headers=headers).status_code == 200
    s3 = client.get(f"/api/v1/inventory/locations/{shop_id}/summary", headers=headers).json()
    assert float(s3["total_physical_quantity"]) == 15.00
    assert float(s3["total_available_quantity"]) == 15.00
    assert s3["low_stock_count"] == 1
    assert s3["out_of_stock_count"] == 0
