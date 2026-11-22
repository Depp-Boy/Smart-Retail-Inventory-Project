import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.models.inventory import Inventory
from app.models.location import Location


def setup_transfer_fixture(db_session, sample_locations, sample_product):
    src = sample_locations["warehouse"]
    dest = Location(location_name="Hub B", location_type="SUB_WAREHOUSE", address="Industrial Zone B")
    db_session.add(dest)
    db_session.commit()

    inv_src = Inventory(location_id=src.location_id, product_id=sample_product.product_id, quantity=Decimal("100.00"), reserved_quantity=Decimal("0.00"))
    db_session.add(inv_src)
    db_session.commit()

    return {"src": src, "dest": dest, "inv_src": inv_src}


def test_create_stock_transfer(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_transfer_fixture(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    payload = {
        "source_location_id": data["src"].location_id,
        "destination_location_id": data["dest"].location_id,
        "product_id": sample_product.product_id,
        "quantity": "25.00",
    }
    res = client.post("/api/v1/stock-transfers/", headers=headers, json=payload)
    assert res.status_code == 201
    assert res.json()["status"] == "PENDING"


def test_transfer_to_same_location_rejected(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_transfer_fixture(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    payload = {
        "source_location_id": data["src"].location_id,
        "destination_location_id": data["src"].location_id,
        "product_id": sample_product.product_id,
        "quantity": "10.00",
    }
    res = client.post("/api/v1/stock-transfers/", headers=headers, json=payload)
    assert res.status_code == 400
    assert "must be different" in res.json()["detail"]


def test_in_transit_deducts_source_stock_and_completion_credits_destination(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_transfer_fixture(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    create_res = client.post(
        "/api/v1/stock-transfers/",
        headers=headers,
        json={"source_location_id": data["src"].location_id, "destination_location_id": data["dest"].location_id, "product_id": sample_product.product_id, "quantity": "30.00"},
    )
    tr_id = create_res.json()["transfer_id"]

    # 1. Mark IN_TRANSIT -> source stock deducted from 100 to 70
    transit_res = client.patch(f"/api/v1/stock-transfers/{tr_id}/status", headers=headers, json={"status": "IN_TRANSIT"})
    assert transit_res.status_code == 200

    db_session.expire_all()
    src_inv = db_session.query(Inventory).filter_by(location_id=data["src"].location_id, product_id=sample_product.product_id).first()
    assert float(src_inv.quantity) == 70.00

    # 2. Mark COMPLETED -> destination stock credited with 30
    complete_res = client.patch(f"/api/v1/stock-transfers/{tr_id}/status", headers=headers, json={"status": "COMPLETED"})
    assert complete_res.status_code == 200

    db_session.expire_all()
    dest_inv = db_session.query(Inventory).filter_by(location_id=data["dest"].location_id, product_id=sample_product.product_id).first()
    assert float(dest_inv.quantity) == 30.00


def test_in_transit_cancellation_rejected_with_409_conflict(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    data = setup_transfer_fixture(db_session, sample_locations, sample_product)
    headers = auth_headers("manager")

    create_res = client.post(
        "/api/v1/stock-transfers/",
        headers=headers,
        json={"source_location_id": data["src"].location_id, "destination_location_id": data["dest"].location_id, "product_id": sample_product.product_id, "quantity": "10.00"},
    )
    tr_id = create_res.json()["transfer_id"]
    client.patch(f"/api/v1/stock-transfers/{tr_id}/status", headers=headers, json={"status": "IN_TRANSIT"})

    # Rule 2: In-transit cancellation MUST be rejected with HTTP 409 Conflict
    cancel_res = client.patch(f"/api/v1/stock-transfers/{tr_id}/status", headers=headers, json={"status": "CANCELLED"})
    assert cancel_res.status_code == 409
    assert "In-transit transfers cannot be cancelled" in cancel_res.json()["detail"]
