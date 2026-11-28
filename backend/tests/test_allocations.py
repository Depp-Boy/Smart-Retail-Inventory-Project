import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.order import Order, OrderItem
from app.models.reservation import StockReservation
from app.models.shop_warehouse import ShopWarehouse
from app.services.allocation_service import AllocationService


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


def test_auto_allocation_respects_preferred_and_priority(db_session, sample_locations, sample_product, sample_users):
    data = setup_order_and_warehouses(db_session, sample_locations, sample_product)
    # WH1 is preferred (priority 1, stock 60), WH2 is priority 2 (stock 50).
    # Add WH3 with priority 3 (stock 40) and WH2_higher with priority 1 (not preferred, stock 25),
    # plus an unassociated warehouse with stock 100 that must be ignored.
    wh_alt_high = Location(location_name="Alt High Priority WH", location_type="SUB_WAREHOUSE", address="Zone A")
    wh_alt_low = Location(location_name="Alt Low Priority WH", location_type="SUB_WAREHOUSE", address="Zone C")
    wh_unlinked = Location(location_name="Unlinked WH", location_type="MAIN_WAREHOUSE", address="Far Away")
    db_session.add_all([wh_alt_high, wh_alt_low, wh_unlinked])
    db_session.commit()

    db_session.add_all([
        ShopWarehouse(shop_id=data["shop"].location_id, warehouse_id=wh_alt_high.location_id, is_preferred=False, priority=1),
        ShopWarehouse(shop_id=data["shop"].location_id, warehouse_id=wh_alt_low.location_id, is_preferred=False, priority=3),
        Inventory(location_id=wh_alt_high.location_id, product_id=sample_product.product_id, quantity=Decimal("25.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=wh_alt_low.location_id, product_id=sample_product.product_id, quantity=Decimal("40.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=wh_unlinked.location_id, product_id=sample_product.product_id, quantity=Decimal("100.00"), reserved_quantity=Decimal("0.00")),
    ])
    db_session.commit()

    # Order item requests 100: should take 60 from preferred WH1, 25 from alt priority=1, 15 from alt priority=2 (WH2)
    service = AllocationService(db_session)
    allocs = service.auto_allocate_order_item(data["item"].order_item_id, auto_reserve=True, actor=sample_users["admin"])

    assert len(allocs) == 3
    assert [(a.source_location_id, float(a.allocated_quantity)) for a in allocs] == [
        (data["wh1"].location_id, 60.00),
        (wh_alt_high.location_id, 25.00),
        (data["wh2"].location_id, 15.00),
    ]

    db_session.expire_all()
    item = db_session.query(OrderItem).filter_by(order_item_id=data["item"].order_item_id).first()
    assert float(item.quantity_allocated) == 100.00
    assert float(db_session.query(Inventory).filter_by(location_id=wh_unlinked.location_id).first().reserved_quantity) == 0.00


def test_cancel_allocation_after_partial_dispatch_rejected(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_order_and_warehouses(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Allocate 50 units from WH1 with auto_reserve=True (inv: qty=60, reserved=50)
    alloc_res = client.post(
        "/api/v1/allocations/",
        headers=headers,
        json={
            "order_item_id": data["item"].order_item_id,
            "source_location_id": data["wh1"].location_id,
            "allocated_quantity": "50.00",
            "auto_reserve": True,
        },
    )
    assert alloc_res.status_code == 201
    alloc_id = alloc_res.json()["allocation_id"]

    # Partial dispatch of 20 units -> inv becomes qty=40, reserved=30; allocation remains RESERVED
    dsp_res = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={
            "order_id": data["order"].order_id,
            "source_location_id": data["wh1"].location_id,
            "items": [{"allocation_id": alloc_id, "product_id": sample_product.product_id, "quantity": "20.00"}],
        },
    )
    assert dsp_res.status_code == 201

    # Attempting to cancel allocation after partial dispatch must be rejected
    cancel_res = client.post(f"/api/v1/allocations/{alloc_id}/cancel", headers=headers)
    assert cancel_res.status_code == 400
    assert "already been dispatched" in cancel_res.json()["detail"]

    # Verify inventory, reservation, and order_item state are preserved untouched
    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh1"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 40.00
    assert float(inv.reserved_quantity) == 30.00
    item = db_session.query(OrderItem).filter_by(order_item_id=data["item"].order_item_id).first()
    assert float(item.quantity_allocated) == 50.00
    active_res = db_session.query(StockReservation).filter_by(allocation_id=alloc_id, status="ACTIVE").all()
    assert len(active_res) == 1
    assert float(active_res[0].quantity_reserved) == 30.00


def test_cancel_allocation_releases_only_active_reservations_and_rejects_inconsistent_stock(
    client: TestClient, sample_locations, sample_product, db_session, auth_headers
):
    data = setup_order_and_warehouses(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Allocate 40 units without auto_reserve
    alloc_res = client.post(
        "/api/v1/allocations/",
        headers=headers,
        json={
            "order_item_id": data["item"].order_item_id,
            "source_location_id": data["wh1"].location_id,
            "allocated_quantity": "40.00",
            "auto_reserve": False,
        },
    )
    assert alloc_res.status_code == 201
    alloc_id = alloc_res.json()["allocation_id"]

    # Create two reservations: 15 (to confirm) and 25 (kept active)
    r1 = client.post("/api/v1/reservations/", headers=headers, json={"allocation_id": alloc_id, "quantity_reserved": "15.00"})
    assert r1.status_code == 201
    r2 = client.post("/api/v1/reservations/", headers=headers, json={"allocation_id": alloc_id, "quantity_reserved": "25.00"})
    assert r2.status_code == 201

    # Confirm r1 -> inv qty: 60->45, reserved: 40->25
    confirm_res = client.post(f"/api/v1/reservations/{r1.json()['reservation_id']}/confirm", headers=headers)
    assert confirm_res.status_code == 200

    # Simulate corrupted inventory where reserved_quantity < active reservation (10 < 25)
    inv = db_session.query(Inventory).filter_by(location_id=data["wh1"].location_id, product_id=sample_product.product_id).first()
    inv.reserved_quantity = Decimal("10.00")
    db_session.commit()

    # Must reject with 409 rather than clamping to zero
    bad_cancel = client.post(f"/api/v1/allocations/{alloc_id}/cancel", headers=headers)
    assert bad_cancel.status_code == 409

    # Restore consistent reserved_quantity=25 and cancel -> only ACTIVE r2 (25) is released; CONFIRMED r1 stays CONFIRMED
    inv = db_session.query(Inventory).filter_by(location_id=data["wh1"].location_id, product_id=sample_product.product_id).first()
    inv.reserved_quantity = Decimal("25.00")
    db_session.commit()

    ok_cancel = client.post(f"/api/v1/allocations/{alloc_id}/cancel", headers=headers)
    assert ok_cancel.status_code == 200
    assert ok_cancel.json()["status"] == "CANCELLED"

    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh1"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 45.00
    assert float(inv.reserved_quantity) == 0.00
    res_map = {
        r.reservation_id: r.status
        for r in db_session.query(StockReservation).filter_by(allocation_id=alloc_id).all()
    }
    assert res_map[r1.json()["reservation_id"]] == "CONFIRMED"
    assert res_map[r2.json()["reservation_id"]] == "RELEASED"
