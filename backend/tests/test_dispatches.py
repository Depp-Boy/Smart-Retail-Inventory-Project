import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.models.allocation import OrderAllocation
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem


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

    return {"wh": wh, "shop": shop, "order": order, "item": item, "alloc": alloc}


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
    dsp_id = dsp_res.json()["dispatch_id"]

    # Transition to IN_TRANSIT
    t_res = client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "IN_TRANSIT"})
    assert t_res.status_code == 200
    assert t_res.json()["dispatch_date"] is not None

    # Transition to DELIVERED -> rule 3: checks delivered quantity satisfies quantity_requested (50 >= 50) -> FULFILLED
    d_res = client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=headers, json={"status": "DELIVERED"})
    assert d_res.status_code == 200

    db_session.expire_all()
    order = db_session.query(Order).filter_by(order_id=data["order"].order_id).first()
    assert order.status == "FULFILLED"
