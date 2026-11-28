import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.core.security import create_access_token, hash_password
from app.models.allocation import OrderAllocation
from app.models.dispatch import Dispatch, DispatchItem
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.reservation import StockReservation
from app.models.user import User
from app.models.worker_task import WorkerTask


def setup_dispatch_order(db_session, sample_locations, sample_product):
    wh = sample_locations["warehouse"]
    shop = sample_locations["shop"]
    prod = sample_product

    # Inventory 100 units
    inv = Inventory(location_id=wh.location_id, product_id=prod.product_id, quantity=Decimal("100.00"), reserved_quantity=Decimal("0.00"))
    db_session.add(inv)

    order = Order(shop_id=shop.location_id, status="PROCESSING")
    db_session.add(order)
    db_session.commit()

    item = OrderItem(order_id=order.order_id, product_id=prod.product_id, quantity_requested=Decimal("50.00"), quantity_allocated=Decimal("50.00"))
    db_session.add(item)
    db_session.commit()

    alloc = OrderAllocation(order_item_id=item.order_item_id, source_location_id=wh.location_id, allocated_quantity=Decimal("50.00"), status="ALLOCATED")
    db_session.add(alloc)
    db_session.commit()
    db_session.refresh(alloc)

    return {"wh": wh, "shop": shop, "order": order, "item": item, "alloc": alloc, "inv": inv}


def _transition_to_delivered(client: TestClient, dsp_id: int, headers: dict):
    for st in ("PACKING", "READY", "IN_TRANSIT", "DELIVERED"):
        res = client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": st})
        assert res.status_code == 200, f"Transition to {st} failed: {res.text}"
    return res


def test_create_dispatch_with_partial_allocation(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Partial shipment: dispatch 30 out of 50 allocated
    payload = {
        "order_id": data["order"].order_id,
        "source_location_id": data["wh"].location_id,
        "tracking_reference": "TRK-BLR-001",
        "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "30.00"}],
    }
    res = client.post("/api/v1/dispatches/", headers=headers, json=payload)
    assert res.status_code == 201
    dsp = res.json()
    assert dsp["status"] == "PENDING"
    assert dsp["tracking_reference"] == "TRK-BLR-001"
    assert len(dsp["items"]) == 1


def test_exceeding_allocated_quantity_rejected(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # 1. Dispatch 40 units
    res1 = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "40.00"}]},
    )
    assert res1.status_code == 201

    # 2. Try to dispatch another 20 units (40 + 20 = 60 > 50 allocated) -> must be rejected
    res2 = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "20.00"}]},
    )
    assert res2.status_code == 400
    assert "exceeds allocated quantity" in res2.json()["detail"]


def test_order_fulfillment_calculation_upon_delivery(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Dispatch complete 50 units
    dsp_res = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "50.00"}]},
    )
    assert dsp_res.status_code == 201
    dsp_id = dsp_res.json()["dispatch_id"]

    # Controlled transitions: PENDING -> PACKING -> READY -> IN_TRANSIT -> DELIVERED
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "PACKING"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "READY"}).status_code == 200

    t_res = client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "IN_TRANSIT"})
    assert t_res.status_code == 200
    assert t_res.json()["dispatch_date"] is not None

    # Transition to DELIVERED -> checks delivered quantity satisfies quantity_requested (50 >= 50) -> FULFILLED
    d_res = client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "DELIVERED"})
    assert d_res.status_code == 200

    db_session.expire_all()
    order = db_session.query(Order).filter_by(order_id=data["order"].order_id).first()
    assert order.status == "FULFILLED"


def test_dispatch_without_reservation_with_sufficient_stock(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # No reservation exists; inventory is qty=100, reserved=0. Dispatching 50 must consume physical stock once.
    res = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={
            "order_id": data["order"].order_id,
            "source_location_id": data["wh"].location_id,
            "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "50.00"}],
        },
    )
    assert res.status_code == 201

    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 50.00
    assert float(inv.reserved_quantity) == 0.00
    alloc = db_session.query(OrderAllocation).filter_by(allocation_id=data["alloc"].allocation_id).first()
    assert alloc.status == "DISPATCHED"


def test_dispatch_without_sufficient_stock_rolls_back(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Case 1: Physical stock (20) < requested unreserved dispatch (30)
    data["inv"].quantity = Decimal("20.00")
    data["inv"].reserved_quantity = Decimal("0.00")
    db_session.commit()

    res1 = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={
            "order_id": data["order"].order_id,
            "source_location_id": data["wh"].location_id,
            "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "30.00"}],
        },
    )
    assert res1.status_code == 400
    assert db_session.query(Dispatch).count() == 0

    # Case 2: Physical stock is 50, but 40 is reserved by another order (available unreserved = 10 < 20)
    data["inv"].quantity = Decimal("50.00")
    data["inv"].reserved_quantity = Decimal("40.00")
    db_session.commit()

    res2 = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={
            "order_id": data["order"].order_id,
            "source_location_id": data["wh"].location_id,
            "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "20.00"}],
        },
    )
    assert res2.status_code == 400
    assert "Insufficient available unreserved stock" in res2.json()["detail"]

    # Verify rollback: no dispatch created and inventory untouched
    db_session.expire_all()
    assert db_session.query(Dispatch).count() == 0
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 50.00
    assert float(inv.reserved_quantity) == 40.00

    # Case 3: Multi-item rollback when item 1 succeeds and item 2 fails insufficient stock
    prod2 = Product(product_name="Sugar 1kg", category="Grocery", unit="Pack", price=Decimal("50.00"), reorder_threshold=Decimal("5.00"), sku="SUG-1KG")
    db_session.add(prod2)
    db_session.commit()
    db_session.add(Inventory(location_id=data["wh"].location_id, product_id=prod2.product_id, quantity=Decimal("5.00"), reserved_quantity=Decimal("0.00")))
    item2 = OrderItem(order_id=data["order"].order_id, product_id=prod2.product_id, quantity_requested=Decimal("20.00"), quantity_allocated=Decimal("20.00"))
    db_session.add(item2)
    db_session.commit()
    alloc2 = OrderAllocation(order_item_id=item2.order_item_id, source_location_id=data["wh"].location_id, allocated_quantity=Decimal("20.00"), status="ALLOCATED")
    db_session.add(alloc2)
    data["inv"].quantity = Decimal("100.00")
    data["inv"].reserved_quantity = Decimal("0.00")
    db_session.commit()

    res3 = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={
            "order_id": data["order"].order_id,
            "source_location_id": data["wh"].location_id,
            "items": [
                {"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "10.00"},
                {"allocation_id": alloc2.allocation_id, "product_id": prod2.product_id, "quantity": "15.00"},
            ],
        },
    )
    assert res3.status_code == 400

    db_session.expire_all()
    assert db_session.query(Dispatch).count() == 0
    assert db_session.query(DispatchItem).count() == 0
    inv1 = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv1.quantity) == 100.00


def test_dispatch_with_incorrect_product_rejected(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    wrong_prod = Product(product_name="Wrong Product", category="Other", unit="Unit", price=Decimal("10.00"), reorder_threshold=Decimal("5.00"), sku="WRONG-1")
    db_session.add(wrong_prod)
    db_session.commit()

    res = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={
            "order_id": data["order"].order_id,
            "source_location_id": data["wh"].location_id,
            "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": wrong_prod.product_id, "quantity": "10.00"}],
        },
    )
    assert res.status_code == 400
    assert "does not match allocation" in res.json()["detail"]
    assert db_session.query(Dispatch).count() == 0


def test_dispatch_with_allocation_from_another_order_rejected(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    other_order = Order(shop_id=data["shop"].location_id, status="PROCESSING")
    db_session.add(other_order)
    db_session.commit()

    res = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={
            "order_id": other_order.order_id,
            "source_location_id": data["wh"].location_id,
            "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "10.00"}],
        },
    )
    assert res.status_code == 400
    assert "does not belong to order" in res.json()["detail"]
    assert db_session.query(Dispatch).count() == 0


def test_partial_dispatch_with_active_reservation(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Reserve full 50 units on allocation (inv: qty=100, reserved=50)
    res_create = client.post(
        "/api/v1/reservations/",
        headers=headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "50.00"},
    )
    assert res_create.status_code == 201

    # Partial dispatch of 20 units
    dsp_res = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={
            "order_id": data["order"].order_id,
            "source_location_id": data["wh"].location_id,
            "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "20.00"}],
        },
    )
    assert dsp_res.status_code == 201

    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 80.00
    assert float(inv.reserved_quantity) == 30.00

    # Allocation must NOT be marked DISPATCHED yet; it remains RESERVED because 30 reserved units remain
    alloc = db_session.query(OrderAllocation).filter_by(allocation_id=data["alloc"].allocation_id).first()
    assert alloc.status == "RESERVED"

    # Active reservation holds 30, confirmed reservation records consumed 20
    reservations = db_session.query(StockReservation).filter_by(allocation_id=data["alloc"].allocation_id).all()
    active_list = [r for r in reservations if r.status == "ACTIVE"]
    confirmed_list = [r for r in reservations if r.status == "CONFIRMED"]
    assert len(active_list) == 1
    assert float(active_list[0].quantity_reserved) == 30.00
    assert sum(float(r.quantity_reserved) for r in confirmed_list) == 20.00


def test_multiple_partial_dispatches_completing_one_allocation(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Reserve 50 units (inv: qty=100, reserved=50)
    assert client.post(
        "/api/v1/reservations/",
        headers=headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "50.00"},
    ).status_code == 201

    # Partial dispatch 1: 20 units -> inv(80, 30), alloc=RESERVED
    assert client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "20.00"}]},
    ).status_code == 201

    # Partial dispatch 2: 15 units -> inv(65, 15), alloc=RESERVED
    assert client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "15.00"}]},
    ).status_code == 201

    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 65.00
    assert float(inv.reserved_quantity) == 15.00
    assert db_session.query(OrderAllocation).filter_by(allocation_id=data["alloc"].allocation_id).first().status == "RESERVED"

    # Partial dispatch 3: final 15 units -> inv(50, 0), alloc=DISPATCHED
    assert client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "15.00"}]},
    ).status_code == 201

    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 50.00
    assert float(inv.reserved_quantity) == 0.00
    assert db_session.query(OrderAllocation).filter_by(allocation_id=data["alloc"].allocation_id).first().status == "DISPATCHED"

    reservations = db_session.query(StockReservation).filter_by(allocation_id=data["alloc"].allocation_id).all()
    assert all(r.status == "CONFIRMED" for r in reservations)
    assert sum(float(r.quantity_reserved) for r in reservations) == 50.00

    # Further dispatch on closed allocation must be rejected
    res_extra = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "1.00"}]},
    )
    assert res_extra.status_code == 400


def test_partial_and_full_delivery(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Create two partial dispatches: D1 = 20 units, D2 = 30 units (total 50 = requested 50)
    d1 = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "20.00"}]},
    )
    d2 = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "30.00"}]},
    )
    assert d1.status_code == 201 and d2.status_code == 201
    d1_id = d1.json()["dispatch_id"]
    d2_id = d2.json()["dispatch_id"]

    # After creating both dispatches, inventory quantity is 50 (100 - 20 - 30)
    db_session.expire_all()
    inv_after_dispatch = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv_after_dispatch.quantity) == 50.00

    # Move D2 only to IN_TRANSIT (NOT delivered), and move D1 to DELIVERED
    for st in ("PACKING", "READY", "IN_TRANSIT"):
        assert client.patch(f"/api/v1/dispatches/{d2_id}/status", headers=headers, json={"status": st}).status_code == 200
    _transition_to_delivered(client, d1_id, headers)

    # Only D1 (20) is DELIVERED -> Order MUST be PARTIALLY_FULFILLED; allocation stays DISPATCHED; stock NOT deducted again
    db_session.expire_all()
    order = db_session.query(Order).filter_by(order_id=data["order"].order_id).first()
    assert order.status == "PARTIALLY_FULFILLED"
    alloc = db_session.query(OrderAllocation).filter_by(allocation_id=data["alloc"].allocation_id).first()
    assert alloc.status == "DISPATCHED"
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 50.00

    # Now deliver D2 (30) -> total delivered = 50 == requested -> Order FULFILLED, allocation DELIVERED, stock unchanged
    assert client.patch(f"/api/v1/dispatches/{d2_id}/status", headers=headers, json={"status": "DELIVERED"}).status_code == 200

    db_session.expire_all()
    order = db_session.query(Order).filter_by(order_id=data["order"].order_id).first()
    assert order.status == "FULFILLED"
    alloc = db_session.query(OrderAllocation).filter_by(allocation_id=data["alloc"].allocation_id).first()
    assert alloc.status == "DELIVERED"
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 50.00


def test_repeated_delivery_and_status_updates_do_not_duplicate_stock_ops(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    dsp = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "50.00"}]},
    )
    dsp_id = dsp.json()["dispatch_id"]

    # Repeated PACKING rejected
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "PACKING"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "PACKING"}).status_code == 400

    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "READY"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "IN_TRANSIT"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "DELIVERED"}).status_code == 200

    # Repeated DELIVERED rejected and inventory remains unchanged (50.00)
    repeat_del = client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "DELIVERED"})
    assert repeat_del.status_code == 400

    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 50.00
    assert float(inv.reserved_quantity) == 0.00
    assert db_session.query(Order).filter_by(order_id=data["order"].order_id).first().status == "FULFILLED"


def test_invalid_dispatch_transitions_and_pre_transit_cancellation(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Dispatch 1: test invalid jumps and transit cancellation rejection
    d1 = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "20.00"}]},
    )
    d1_id = d1.json()["dispatch_id"]

    # Invalid jumps from PENDING
    assert client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "READY"}).status_code == 400
    assert client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "IN_TRANSIT"}).status_code == 400
    assert client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "DELIVERED"}).status_code == 400

    # Valid PENDING -> PACKING; invalid backward PACKING -> PENDING and jump PACKING -> IN_TRANSIT
    assert client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "PACKING"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "PENDING"}).status_code == 400
    assert client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "IN_TRANSIT"}).status_code == 400

    # Valid PACKING -> READY; invalid jump READY -> DELIVERED
    assert client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "READY"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "DELIVERED"}).status_code == 400

    # Valid READY -> IN_TRANSIT; cancellation in IN_TRANSIT MUST be rejected with 409
    assert client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "IN_TRANSIT"}).status_code == 200
    cancel_transit = client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "CANCELLED"})
    assert cancel_transit.status_code == 409

    # Valid IN_TRANSIT -> DELIVERED; cancellation in DELIVERED MUST be rejected with 409
    assert client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "DELIVERED"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{d1_id}/status", headers=headers, json={"status": "CANCELLED"}).status_code == 409

    # Dispatch 2: cancellation BEFORE transit (READY -> CANCELLED) is allowed and restores physical stock
    d2 = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "30.00"}]},
    )
    assert d2.status_code == 201
    d2_id = d2.json()["dispatch_id"]
    assert client.patch(f"/api/v1/dispatches/{d2_id}/status", headers=headers, json={"status": "PACKING"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{d2_id}/status", headers=headers, json={"status": "READY"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{d2_id}/status", headers=headers, json={"status": "CANCELLED"}).status_code == 200

    # Cannot transition out of CANCELLED
    assert client.patch(f"/api/v1/dispatches/{d2_id}/status", headers=headers, json={"status": "PACKING"}).status_code == 400

    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    # 100 - 20 (D1) - 30 (D2) + 30 (D2 cancelled) = 80
    assert float(inv.quantity) == 80.00


def test_cross_warehouse_and_worker_dispatch_authorization(client: TestClient, sample_locations, sample_product, sample_users, db_session, auth_headers):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)

    # Create second warehouse, its manager, and its worker
    wh2 = Location(location_name="West Hub", location_type="SUB_WAREHOUSE", address="West Zone")
    db_session.add(wh2)
    db_session.commit()
    db_session.refresh(wh2)

    mgr2 = User(
        name="Manager 2",
        email="mgr2_dsp@test.com",
        password_hash=hash_password("mgr2"),
        role="WAREHOUSE_MANAGER",
        location_id=wh2.location_id,
    )
    worker2 = User(
        name="Worker 2",
        email="worker2_dsp@test.com",
        password_hash=hash_password("worker2"),
        role="WAREHOUSE_WORKER",
        location_id=wh2.location_id,
    )
    db_session.add_all([mgr2, worker2])
    db_session.commit()
    db_session.refresh(mgr2)
    db_session.refresh(worker2)

    mgr1_headers = auth_headers("manager")
    worker1_headers = auth_headers("worker")
    admin_headers = auth_headers("admin")
    mgr2_headers = {"Authorization": f"Bearer {create_access_token(data={'sub': str(mgr2.user_id), 'email': mgr2.email, 'role': mgr2.role})}"}
    worker2_headers = {"Authorization": f"Bearer {create_access_token(data={'sub': str(worker2.user_id), 'email': worker2.email, 'role': worker2.role})}"}

    # Manager 2 cannot create dispatch for WH1
    assert client.post(
        "/api/v1/dispatches/",
        headers=mgr2_headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "20.00"}]},
    ).status_code == 403

    # Manager 1 creates dispatch for WH1
    dsp = client.post(
        "/api/v1/dispatches/",
        headers=mgr1_headers,
        json={"order_id": data["order"].order_id, "source_location_id": data["wh"].location_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "20.00"}]},
    )
    assert dsp.status_code == 201
    dsp_id = dsp.json()["dispatch_id"]

    # Manager 2 cannot list WH1 dispatches, get WH1 dispatch, or update WH1 dispatch
    assert client.get(f"/api/v1/dispatches/?warehouse_id={data['wh'].location_id}", headers=mgr2_headers).status_code == 403
    assert client.get(f"/api/v1/dispatches/{dsp_id}", headers=mgr2_headers).status_code == 403
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=mgr2_headers, json={"status": "PACKING"}).status_code == 403

    # Worker 1 (in WH1) WITHOUT an assigned task cannot access or update this dispatch
    assert client.get(f"/api/v1/dispatches/{dsp_id}", headers=worker1_headers).status_code == 403
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker1_headers, json={"status": "PACKING"}).status_code == 403

    # Worker 1 with a CANCELLED DISPATCH task still cannot update the dispatch
    cancelled_task = WorkerTask(
        task_code="TASK-CANCELLED-1",
        assigned_worker_id=sample_users["worker"].user_id,
        assigned_by_user_id=sample_users["manager"].user_id,
        dispatch_id=dsp_id,
        task_type="DISPATCH",
        priority="NORMAL",
        status="CANCELLED",
    )
    # Worker 1 with only a PACKING task (not a DISPATCH task) cannot update dispatch status
    packing_task = WorkerTask(
        task_code="TASK-PACK-ONLY-1",
        assigned_worker_id=sample_users["worker"].user_id,
        assigned_by_user_id=sample_users["manager"].user_id,
        dispatch_id=dsp_id,
        task_type="PACKING",
        priority="NORMAL",
        status="IN_PROGRESS",
    )
    db_session.add_all([cancelled_task, packing_task])
    db_session.commit()
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker1_headers, json={"status": "PACKING"}).status_code == 403

    # Assign a valid DISPATCH task to Worker 1 -> can move PENDING -> PACKING -> READY -> IN_TRANSIT, cannot CANCEL or DELIVER
    valid_task = WorkerTask(
        task_code="TASK-DSP-VALID-1",
        assigned_worker_id=sample_users["worker"].user_id,
        assigned_by_user_id=sample_users["manager"].user_id,
        dispatch_id=dsp_id,
        task_type="DISPATCH",
        priority="HIGH",
        status="IN_PROGRESS",
    )
    db_session.add(valid_task)
    db_session.commit()

    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker1_headers, json={"status": "PACKING"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker1_headers, json={"status": "CANCELLED"}).status_code == 403
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker1_headers, json={"status": "READY"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker1_headers, json={"status": "IN_TRANSIT"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker1_headers, json={"status": "DELIVERED"}).status_code == 403

    # Worker 2 (other warehouse) is forbidden
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker2_headers, json={"status": "DELIVERED"}).status_code == 403

    # Admin retains unrestricted access across warehouses
    assert client.get(f"/api/v1/dispatches/{dsp_id}", headers=admin_headers).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=admin_headers, json={"status": "DELIVERED"}).status_code == 200


def test_delivery_credits_destination_shop_inventory_exactly_once_and_supports_partial_deliveries(
    client: TestClient, sample_locations, sample_product, db_session, auth_headers
):
    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    shop_id = data["shop"].location_id
    wh_id = data["wh"].location_id
    prod_id = sample_product.product_id
    headers = auth_headers("manager")

    # Seed existing shop inventory: 10 units
    db_session.add(Inventory(location_id=shop_id, product_id=prod_id, quantity=Decimal("10.00"), reserved_quantity=Decimal("0.00")))
    db_session.commit()

    # Create two partial dispatches (20 + 30 = 50); warehouse stock drops 100 -> 50; shop stock stays 10
    d1 = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": wh_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": prod_id, "quantity": "20.00"}]},
    ).json()["dispatch_id"]
    d2 = client.post(
        "/api/v1/dispatches/",
        headers=headers,
        json={"order_id": data["order"].order_id, "source_location_id": wh_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": prod_id, "quantity": "30.00"}]},
    ).json()["dispatch_id"]

    # Move D2 to IN_TRANSIT -> shop inventory still 10 (not yet delivered)
    for st in ("PACKING", "READY", "IN_TRANSIT"):
        assert client.patch(f"/api/v1/dispatches/{d2}/status", headers=headers, json={"status": st}).status_code == 200
    db_session.expire_all()
    assert float(db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first().quantity) == 10.00

    # Deliver D1 (20) -> shop credited 10 -> 30; warehouse unchanged at 50; order PARTIALLY_FULFILLED
    _transition_to_delivered(client, d1, headers)
    db_session.expire_all()
    assert float(db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first().quantity) == 30.00
    assert float(db_session.query(Inventory).filter_by(location_id=wh_id, product_id=prod_id).first().quantity) == 50.00
    assert db_session.query(Order).filter_by(order_id=data["order"].order_id).first().status == "PARTIALLY_FULFILLED"

    # Deliver D2 (30) -> shop credited 30 -> 60; warehouse unchanged at 50; order FULFILLED
    assert client.patch(f"/api/v1/dispatches/{d2}/status", headers=headers, json={"status": "DELIVERED"}).status_code == 200
    db_session.expire_all()
    shop_rows = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).all()
    assert len(shop_rows) == 1
    assert float(shop_rows[0].quantity) == 60.00
    assert float(db_session.query(Inventory).filter_by(location_id=wh_id, product_id=prod_id).first().quantity) == 50.00
    assert db_session.query(Order).filter_by(order_id=data["order"].order_id).first().status == "FULFILLED"

    # Repeated DELIVERED attempt rejected and does NOT credit shop inventory twice
    assert client.patch(f"/api/v1/dispatches/{d2}/status", headers=headers, json={"status": "DELIVERED"}).status_code == 400
    db_session.expire_all()
    assert float(db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first().quantity) == 60.00


def test_delivery_creates_missing_shop_inventory_and_syncs_with_forecasting(
    client: TestClient, sample_locations, sample_product, db_session, auth_headers
):
    from datetime import datetime, timedelta, timezone
    from app.models.sale import Sale, SaleItem

    data = setup_dispatch_order(db_session, sample_locations, sample_product)
    shop_id = data["shop"].location_id
    wh_id = data["wh"].location_id
    prod_id = sample_product.product_id
    mgr_headers = auth_headers("manager")
    shop_headers = auth_headers("shop_owner")

    # Seed 10 days of 4/day sales -> April (30 days) SMA demand = 120.00; safety stock = 20.00
    now = datetime.now(timezone.utc)
    for d in range(10):
        s = Sale(shop_id=shop_id, sale_date=now - timedelta(days=d), total_amount=Decimal("40.00"), status="COMPLETED")
        db_session.add(s)
        db_session.flush()
        db_session.add(SaleItem(sale_id=s.sale_id, product_id=prod_id, quantity=Decimal("4.00"), unit_price=Decimal("10.00")))
    db_session.commit()

    assert client.post(
        "/api/v1/forecasts/generate",
        headers=shop_headers,
        json={"shop_id": shop_id, "product_id": prod_id, "forecast_period": "2026-04-01", "model_preference": "SMA", "history_days": 10},
    ).status_code == 201

    # Dispatch 25 units and move to IN_TRANSIT (shop has NO inventory row yet)
    dsp_id = client.post(
        "/api/v1/dispatches/",
        headers=mgr_headers,
        json={"order_id": data["order"].order_id, "source_location_id": wh_id, "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": prod_id, "quantity": "25.00"}]},
    ).json()["dispatch_id"]
    for st in ("PACKING", "READY", "IN_TRANSIT"):
        assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=mgr_headers, json={"status": st}).status_code == 200

    # While IN_TRANSIT: available=0, in_transit=25 -> reorder = 120 + 20 - 0 - 25 = 115.00
    rec_before = client.get(
        f"/api/v1/forecasts/reorder-recommendation?shop_id={shop_id}&product_id={prod_id}&period=2026-04-01",
        headers=shop_headers,
    ).json()
    assert Decimal(str(rec_before["available_stock"])) == Decimal("0.00")
    assert Decimal(str(rec_before["in_transit_stock"])) == Decimal("25.00")
    assert Decimal(str(rec_before["recommended_reorder_quantity"])) == Decimal("115.00")

    # Deliver dispatch -> shop inventory row created with 25.00; in_transit drops to 0.00; reorder stays 115.00 (no disappearing or double-counted stock!)
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=mgr_headers, json={"status": "DELIVERED"}).status_code == 200

    rec_after = client.get(
        f"/api/v1/forecasts/reorder-recommendation?shop_id={shop_id}&product_id={prod_id}&period=2026-04-01",
        headers=shop_headers,
    ).json()
    assert Decimal(str(rec_after["available_stock"])) == Decimal("25.00")
    assert Decimal(str(rec_after["in_transit_stock"])) == Decimal("0.00")
    assert Decimal(str(rec_after["recommended_reorder_quantity"])) == Decimal("115.00")
