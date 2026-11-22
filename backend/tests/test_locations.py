import pytest
from fastapi.testclient import TestClient


def test_location_creation_and_listing(client: TestClient, auth_headers):
    headers = auth_headers("admin")
    payload = {
        "location_name": "Whitefield Fulfillment Center",
        "location_type": "SUB_WAREHOUSE",
        "address": "ITPL Main Road, Whitefield, Bengaluru",
    }
    res = client.post("/api/v1/locations/", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["location_name"] == "Whitefield Fulfillment Center"
    assert data["location_type"] == "SUB_WAREHOUSE"

    # List warehouses
    wh_res = client.get("/api/v1/locations/warehouses")
    assert wh_res.status_code == 200
    assert any(w["location_name"] == "Whitefield Fulfillment Center" for w in wh_res.json())


def test_invalid_location_type_rejected(client: TestClient, auth_headers):
    headers = auth_headers("admin")
    payload = {
        "location_name": "Invalid Location",
        "location_type": "AIRPORT",
        "address": "Airport Road",
    }
    res = client.post("/api/v1/locations/", headers=headers, json=payload)
    assert res.status_code == 400


def test_shop_preferred_warehouse_routing(client: TestClient, sample_locations, auth_headers):
    shop_id = sample_locations["shop"].location_id
    wh_id = sample_locations["warehouse"].location_id

    # Retrieve preferred warehouse
    res = client.get(f"/api/v1/warehouses/shops/{shop_id}/preferred-warehouse")
    assert res.status_code == 200
    data = res.json()
    assert data["shop_id"] == shop_id
    assert data["warehouse_id"] == wh_id
    assert data["is_preferred"] is True


def test_set_preferred_warehouse_exclusivity(client: TestClient, sample_locations, auth_headers, db_session):
    from app.models.location import Location
    headers = auth_headers("admin")
    shop_id = sample_locations["shop"].location_id

    # Create a second warehouse
    wh2 = Location(
        location_name="Peenya Industrial Warehouse",
        location_type="MAIN_WAREHOUSE",
        address="Peenya 2nd Stage, Bengaluru",
    )
    db_session.add(wh2)
    db_session.commit()
    db_session.refresh(wh2)

    # Set wh2 as preferred warehouse for shop
    res = client.put(f"/api/v1/warehouses/shops/{shop_id}/preferred-warehouse/{wh2.location_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_preferred"] is True

    # Check that previous warehouse is now in alternative warehouses
    alt_res = client.get(f"/api/v1/warehouses/shops/{shop_id}/alternative-warehouses")
    assert alt_res.status_code == 200
    alts = alt_res.json()
    assert any(a["warehouse_id"] == sample_locations["warehouse"].location_id for a in alts)
