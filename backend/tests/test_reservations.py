import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.models.allocation import OrderAllocation
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem


def setup_reservation_fixture(db_session, sample_locations, sample_product):
    wh = sample_locations["warehouse"]
    shop = sample_locations["shop"]
    prod = sample_product

    inv = Inventory(location_id=wh.location_id, product_id=prod.product_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00"))
    db_session.add(inv)

    order = Order(shop_id=shop.location_id, status="PENDING")
    db_session.add(order)
    db_session.commit()

    item = OrderItem(order_id=order.order_id, product_id=prod.product_id, quantity_requested=Decimal("20.00"), quantity_allocated=Decimal("20.00"))
    db_session.add(item)
    db_session.commit()

    alloc = OrderAllocation(order_item_id=item.order_item_id, source_location_id=wh.location_id, allocated_quantity=Decimal("20.00"), status="ALLOCATED")
    db_session.add(alloc)
    db_session.commit()
    db_session.refresh(alloc)

    return {"wh": wh, "alloc": alloc, "inv": inv}


def test_create_reservation_increases_reserved_quantity(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_reservation_fixture(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    payload = {"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "15.00"}
    res = client.post("/api/v1/reservations/", headers=headers, json=payload)
    assert res.status_code == 201
    assert res.json()["status"] == "ACTIVE"

    # Rule 1: physical quantity unchanged (50), reserved_quantity increased (15)
    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 50.00
    assert float(inv.reserved_quantity) == 15.00


def test_insufficient_stock_reservation_rejected(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_reservation_fixture(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Available is 50, trying to reserve 55
    res = client.post(
        "/api/v1/reservations/",
        headers=headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "55.00"},
    )
    assert res.status_code == 400
    assert "Insufficient available stock" in res.json()["detail"]


def test_release_reservation_restores_reserved_quantity(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_reservation_fixture(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    create_res = client.post("/api/v1/reservations/", headers=headers, json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "20.00"})
    res_id = create_res.json()["reservation_id"]

    release_res = client.post(f"/api/v1/reservations/{res_id}/release", headers=headers)
    assert release_res.status_code == 200
    assert release_res.json()["status"] == "RELEASED"

    # Reserved quantity decremented back to 0 exactly once
    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.reserved_quantity) == 0.00

    # Idempotent rejection: Cannot release an already released reservation
    repeat_res = client.post(f"/api/v1/reservations/{res_id}/release", headers=headers)
    assert repeat_res.status_code == 400


def test_confirm_reservation_consumes_stock_and_reserve(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_reservation_fixture(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    create_res = client.post("/api/v1/reservations/", headers=headers, json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "10.00"})
    res_id = create_res.json()["reservation_id"]

    # Confirm reservation -> consumes stock: quantity 50 -> 40, reserved 10 -> 0
    confirm_res = client.post(f"/api/v1/reservations/{res_id}/confirm", headers=headers)
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "CONFIRMED"

    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 40.00
    assert float(inv.reserved_quantity) == 0.00
