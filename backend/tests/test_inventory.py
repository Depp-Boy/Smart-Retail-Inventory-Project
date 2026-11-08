import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.models.inventory import Inventory
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
