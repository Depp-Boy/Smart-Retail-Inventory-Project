import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from app.core.security import create_access_token, hash_password
from app.models.allocation import OrderAllocation
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.order import Order, OrderItem
from app.models.reservation import StockReservation
from app.models.user import User


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

    return {"wh": wh, "shop": shop, "order": order, "item": item, "alloc": alloc, "inv": inv}


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


def test_reservation_quantity_exceeding_allocation_rejected(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_reservation_fixture(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Inventory available is 50, allocation is only 20 -> reserving 25 must be rejected
    res_over = client.post(
        "/api/v1/reservations/",
        headers=headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "25.00"},
    )
    assert res_over.status_code == 400
    assert "exceeds remaining allocation" in res_over.json()["detail"]

    # Reserve 12 (valid)
    r1 = client.post(
        "/api/v1/reservations/",
        headers=headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "12.00"},
    )
    assert r1.status_code == 201

    # Trying to reserve another 10 (12 + 10 = 22 > 20) must be rejected
    r2_over = client.post(
        "/api/v1/reservations/",
        headers=headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "10.00"},
    )
    assert r2_over.status_code == 400
    assert "exceeds remaining allocation" in r2_over.json()["detail"]

    # Confirm the 12-unit reservation (consumed = 12, remaining = 8); trying to reserve 9 must be rejected
    assert client.post(f"/api/v1/reservations/{r1.json()['reservation_id']}/confirm", headers=headers).status_code == 200
    r3_over = client.post(
        "/api/v1/reservations/",
        headers=headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "9.00"},
    )
    assert r3_over.status_code == 400
    assert "exceeds remaining allocation" in r3_over.json()["detail"]

    # Reserving remaining 8 succeeds, then confirming makes allocation fully consumed (20/20)
    r4 = client.post(
        "/api/v1/reservations/",
        headers=headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "8.00"},
    )
    assert r4.status_code == 201
    assert client.post(f"/api/v1/reservations/{r4.json()['reservation_id']}/confirm", headers=headers).status_code == 200

    # No more reservations allowed when fully consumed
    r5 = client.post(
        "/api/v1/reservations/",
        headers=headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "1.00"},
    )
    assert r5.status_code == 400

    # Also reject reservations for CANCELLED or DISPATCHED allocations
    alloc_cancelled = OrderAllocation(
        order_item_id=data["item"].order_item_id,
        source_location_id=data["wh"].location_id,
        allocated_quantity=Decimal("10.00"),
        status="CANCELLED",
    )
    alloc_dispatched = OrderAllocation(
        order_item_id=data["item"].order_item_id,
        source_location_id=data["wh"].location_id,
        allocated_quantity=Decimal("10.00"),
        status="DISPATCHED",
    )
    db_session.add_all([alloc_cancelled, alloc_dispatched])
    db_session.commit()

    assert client.post("/api/v1/reservations/", headers=headers, json={"allocation_id": alloc_cancelled.allocation_id, "quantity_reserved": "5.00"}).status_code == 400
    assert client.post("/api/v1/reservations/", headers=headers, json={"allocation_id": alloc_dispatched.allocation_id, "quantity_reserved": "5.00"}).status_code == 400


def test_premature_reservation_expiry_rejected_and_expired_succeeds(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_reservation_fixture(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    # Create reservation expiring in 24 hours
    create_res = client.post(
        "/api/v1/reservations/",
        headers=headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "15.00", "expires_in_hours": 24},
    )
    assert create_res.status_code == 201
    res_id = create_res.json()["reservation_id"]

    # Premature expiry must be rejected
    premature = client.post(f"/api/v1/reservations/{res_id}/expire", headers=headers)
    assert premature.status_code == 400
    assert "unexpired" in premature.json()["detail"].lower()

    # Inventory reserved_quantity must remain 15 and reservation still ACTIVE
    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.reserved_quantity) == 15.00
    res_obj = db_session.query(StockReservation).filter_by(reservation_id=res_id).first()
    assert res_obj.status == "ACTIVE"

    # Reservation without expires_at also cannot be expired
    res_obj.expires_at = None
    db_session.commit()
    no_exp = client.post(f"/api/v1/reservations/{res_id}/expire", headers=headers)
    assert no_exp.status_code == 400

    # Move expires_at into the past -> expiry succeeds and decrements reserved_quantity exactly once
    res_obj = db_session.query(StockReservation).filter_by(reservation_id=res_id).first()
    res_obj.reserved_at = datetime.now(timezone.utc) - timedelta(hours=4)
    res_obj.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    exp_ok = client.post(f"/api/v1/reservations/{res_id}/expire", headers=headers)
    assert exp_ok.status_code == 200
    assert exp_ok.json()["status"] == "EXPIRED"

    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.reserved_quantity) == 0.00
    assert float(inv.quantity) == 50.00

    # Re-expiring must be rejected and not decrement again
    exp_again = client.post(f"/api/v1/reservations/{res_id}/expire", headers=headers)
    assert exp_again.status_code == 400


def test_reservation_operations_reject_negative_inventory(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_reservation_fixture(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    create_res = client.post(
        "/api/v1/reservations/",
        headers=headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "15.00"},
    )
    res_id = create_res.json()["reservation_id"]

    # Corrupt inventory so reserved_quantity (5) < reservation (15)
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    inv.reserved_quantity = Decimal("5.00")
    db_session.commit()

    # Release and confirm must both fail with 409 rather than clamping to zero
    assert client.post(f"/api/v1/reservations/{res_id}/release", headers=headers).status_code == 409
    assert client.post(f"/api/v1/reservations/{res_id}/confirm", headers=headers).status_code == 409

    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.reserved_quantity) == 5.00


def test_cross_warehouse_reservation_authorization(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_reservation_fixture(db_session, sample_locations, sample_product)

    # Create a second warehouse and its manager
    wh2 = Location(location_name="North Hub", location_type="SUB_WAREHOUSE", address="North Industrial Area")
    db_session.add(wh2)
    db_session.commit()
    db_session.refresh(wh2)

    mgr2 = User(
        name="Other Warehouse Manager",
        email="manager2@test.com",
        password_hash=hash_password("manager2"),
        role="WAREHOUSE_MANAGER",
        location_id=wh2.location_id,
    )
    db_session.add(mgr2)
    db_session.commit()
    db_session.refresh(mgr2)

    mgr2_token = create_access_token(data={"sub": str(mgr2.user_id), "email": mgr2.email, "role": mgr2.role})
    mgr2_headers = {"Authorization": f"Bearer {mgr2_token}"}
    mgr1_headers = auth_headers("manager")
    admin_headers = auth_headers("admin")

    # Manager 2 cannot create reservation for WH1's allocation
    assert client.post(
        "/api/v1/reservations/",
        headers=mgr2_headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "10.00"},
    ).status_code == 403

    # Manager 1 creates reservation in WH1
    r_res = client.post(
        "/api/v1/reservations/",
        headers=mgr1_headers,
        json={"allocation_id": data["alloc"].allocation_id, "quantity_reserved": "10.00"},
    )
    assert r_res.status_code == 201
    res_id = r_res.json()["reservation_id"]

    # Manager 2 cannot view WH1 reservations via list or allocation lookup
    list_mgr2 = client.get("/api/v1/reservations/", headers=mgr2_headers)
    assert list_mgr2.status_code == 200
    assert all(r["reservation_id"] != res_id for r in list_mgr2.json())

    assert client.get(f"/api/v1/reservations/allocation/{data['alloc'].allocation_id}", headers=mgr2_headers).status_code == 403

    # Manager 2 cannot release, confirm, or expire WH1 reservation
    assert client.post(f"/api/v1/reservations/{res_id}/release", headers=mgr2_headers).status_code == 403
    assert client.post(f"/api/v1/reservations/{res_id}/confirm", headers=mgr2_headers).status_code == 403
    assert client.post(f"/api/v1/reservations/{res_id}/expire", headers=mgr2_headers).status_code == 403

    # Admin retains unrestricted access
    admin_list = client.get("/api/v1/reservations/", headers=admin_headers)
    assert admin_list.status_code == 200
    assert any(r["reservation_id"] == res_id for r in admin_list.json())
    assert client.post(f"/api/v1/reservations/{res_id}/release", headers=admin_headers).status_code == 200
