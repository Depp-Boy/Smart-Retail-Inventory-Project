import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.order import Order, OrderItem
from app.models.shop_warehouse import ShopWarehouse


def setup_order_and_warehouses(db_session, sample_locations, sample_product):
    wh1 = sample_locations["warehouse"]
    shop = sample_locations["shop"]
    prod = sample_product

    # Create secondary warehouse
    wh2 = Location(
        location_name="Whitefield Regional Warehouse",
        location_type="SUB_WAREHOUSE",
        address="Whitefield Tech Zone, Bengaluru",
    )
    db_session.add(wh2)
    db_session.commit()
    db_session.refresh(wh2)

    # Link wh2 to shop as alternative warehouse
    link2 = ShopWarehouse(shop_id=shop.location_id, warehouse_id=wh2.location_id, is_preferred=False, priority=2)
    db_session.add(link2)

    # Seed stock: WH1 = 60 units, WH2 = 50 units
    inv1 = Inventory(location_id=wh1.location_id, product_id=prod.product_id, quantity=Decimal("60.00"), reserved_quantity=Decimal("0.00"))
    inv2 = Inventory(location_id=wh2.location_id, product_id=prod.product_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00"))
    db_session.add_all([inv1, inv2])

    # Create Order requesting 100 units
    order = Order(shop_id=shop.location_id, status="PENDING", total_amount=Decimal("14500.00"))
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    item = OrderItem(order_id=order.order_id, product_id=prod.product_id, quantity_requested=Decimal("100.00"), quantity_allocated=Decimal("0.00"))
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    return {"wh1": wh1, "wh2": wh2, "shop": shop, "order": order, "item": item, "inv1": inv1, "inv2": inv2}


def test_successful_allocation_and_auto_reservation(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_order_and_warehouses(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Allocate 60 units from WH1 with auto_reserve=True
    payload = {
        "order_item_id": data["item"].order_item_id,
        "source_location_id": data["wh1"].location_id,
        "allocated_quantity": "60.00",
        "auto_reserve": True,
    }
    res = client.post("/api/v1/allocations/", headers=headers, json=payload)
    assert res.status_code == 201
    alloc = res.json()
    assert alloc["status"] == "RESERVED"
    assert float(alloc["allocated_quantity"]) == 60.00

    # Verify inventory reserved_quantity increased by 60
    db_session.expire_all()
    check_inv = db_session.query(Inventory).filter_by(location_id=data["wh1"].location_id, product_id=sample_product.product_id).first()
    assert float(check_inv.reserved_quantity) == 60.00
    assert float(check_inv.quantity) == 60.00


def test_partial_allocation_and_multiple_warehouses(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_order_and_warehouses(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # 1. Allocate 60 units from WH1
    res1 = client.post(
        "/api/v1/allocations/",
        headers=headers,
        json={"order_item_id": data["item"].order_item_id, "source_location_id": data["wh1"].location_id, "allocated_quantity": "60.00"},
    )
    assert res1.status_code == 201

    # 2. Allocate remaining 40 units from WH2
    res2 = client.post(
        "/api/v1/allocations/",
        headers=headers,
        json={"order_item_id": data["item"].order_item_id, "source_location_id": data["wh2"].location_id, "allocated_quantity": "40.00"},
    )
    assert res2.status_code == 201

    # Verify total allocated quantity equals 100 on order item
    db_session.expire_all()
    item = db_session.query(OrderItem).filter_by(order_item_id=data["item"].order_item_id).first()
    assert float(item.quantity_allocated) == 100.00


def test_over_allocation_rejected(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_order_and_warehouses(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Requests 100, attempting to allocate 105 must be rejected
    res = client.post(
        "/api/v1/allocations/",
        headers=headers,
        json={"order_item_id": data["item"].order_item_id, "source_location_id": data["wh1"].location_id, "allocated_quantity": "105.00"},
    )
    assert res.status_code == 400
    assert "Over-allocation rejected" in res.json()["detail"]


def test_unassociated_warehouse_allocation_rejected(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_order_and_warehouses(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Unlinked rogue warehouse
    unlinked_wh = Location(location_name="Rogue DC", location_type="MAIN_WAREHOUSE", address="Elsewhere")
    db_session.add(unlinked_wh)
    db_session.commit()

    res = client.post(
        "/api/v1/allocations/",
        headers=headers,
        json={"order_item_id": data["item"].order_item_id, "source_location_id": unlinked_wh.location_id, "allocated_quantity": "10.00"},
    )
    assert res.status_code == 400
    assert "not associated with shop" in res.json()["detail"]


def test_cancel_allocation_reverts_state(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_order_and_warehouses(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    alloc_res = client.post(
        "/api/v1/allocations/",
        headers=headers,
        json={"order_item_id": data["item"].order_item_id, "source_location_id": data["wh1"].location_id, "allocated_quantity": "30.00"},
    )
    alloc_id = alloc_res.json()["allocation_id"]

    # Cancel allocation
    cancel_res = client.post(f"/api/v1/allocations/{alloc_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Verify inventory reservation was released back
    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh1"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.reserved_quantity) == 0.00
