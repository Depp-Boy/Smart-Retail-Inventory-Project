import pytest
from decimal import Decimal
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.core.security import create_access_token, hash_password
from app.models.allocation import OrderAllocation
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.reservation import StockReservation
from app.models.sale import Sale, SaleItem
from app.models.user import User
from app.schemas.sale import SaleCreateRequest, SaleItemCreate
from app.services.sale_service import SaleService


def test_successful_sale_creation_and_atomic_stock_deduction(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id

    # Seed stock: 50 units
    inv = Inventory(location_id=shop_id, product_id=prod_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00"))
    db_session.add(inv)
    db_session.commit()

    headers = auth_headers("shop_owner")
    payload = {
        "shop_id": shop_id,
        "items": [{"product_id": prod_id, "quantity": "5.00"}],
        "payment_method": "UPI",
        "tax_amount": "14.50",
        "discount_amount": "10.00",
        "customer_name": "Ramesh Kumar",
        "customer_phone": "+91 9988776655",
    }
    # Unit price = 145.00 -> 5 * 145 = 725.00. Tax = 14.50, Discount = 10.00 -> Total = 729.50
    res = client.post("/api/v1/sales/", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert float(data["subtotal"]) == 725.00
    assert float(data["tax_amount"]) == 14.50
    assert float(data["discount_amount"]) == 10.00
    assert float(data["total_amount"]) == 729.50
    assert data["status"] == "COMPLETED"

    # Verify atomic stock deduction: 50 - 5 = 45
    db_session.expire_all()
    updated_inv = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first()
    assert float(updated_inv.quantity) == 45.00


def test_insufficient_stock_rejection_and_rollback(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id

    # Stock is only 3 units
    inv = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first()
    if not inv:
        inv = Inventory(location_id=shop_id, product_id=prod_id, quantity=Decimal("3.00"), reserved_quantity=Decimal("0.00"))
        db_session.add(inv)
        db_session.commit()
    else:
        inv.quantity = Decimal("3.00")
        db_session.commit()

    headers = auth_headers("shop_owner")
    payload = {
        "shop_id": shop_id,
        "items": [{"product_id": prod_id, "quantity": "10.00"}],  # Requests 10 units (only 3 available)
    }
    res = client.post("/api/v1/sales/", headers=headers, json=payload)
    assert res.status_code == 400
    assert "Insufficient available stock" in res.json()["detail"]

    # Verify inventory was NOT changed
    db_session.expire_all()
    check_inv = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first()
    assert float(check_inv.quantity) == 3.00


def test_sale_cancellation_restores_stock_idempotently(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id

    # Seed 20 units
    inv = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first()
    if not inv:
        inv = Inventory(location_id=shop_id, product_id=prod_id, quantity=Decimal("20.00"), reserved_quantity=Decimal("0.00"))
        db_session.add(inv)
    else:
        inv.quantity = Decimal("20.00")
    db_session.commit()

    headers = auth_headers("shop_owner")
    # Make sale of 4 units -> stock drops to 16
    sale_res = client.post("/api/v1/sales/", headers=headers, json={"shop_id": shop_id, "items": [{"product_id": prod_id, "quantity": "4.00"}]})
    assert sale_res.status_code == 201
    sale_id = sale_res.json()["sale_id"]

    db_session.expire_all()
    inv_after_sale = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first()
    assert float(inv_after_sale.quantity) == 16.00

    # Cancel sale -> stock should restore back to 20
    cancel_res = client.post(f"/api/v1/sales/{sale_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    db_session.expire_all()
    inv_after_cancel = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first()
    assert float(inv_after_cancel.quantity) == 20.00

    # Second cancellation attempt must be rejected (idempotency - stock not restored twice)
    repeat_res = client.post(f"/api/v1/sales/{sale_id}/cancel", headers=headers)
    assert repeat_res.status_code == 400
    assert "already marked as CANCELLED" in repeat_res.json()["detail"]


def test_sale_infers_shop_id_and_cannot_consume_reserved_stock(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id

    # Physical=25, Reserved=15 -> Available=10
    db_session.add(Inventory(location_id=shop_id, product_id=prod_id, quantity=Decimal("25.00"), reserved_quantity=Decimal("15.00")))
    db_session.commit()

    headers = auth_headers("shop_owner")

    # Attempting to sell 12 (exceeds available 10 even though physical is 25) must fail
    over_res = client.post(
        "/api/v1/sales/",
        headers=headers,
        json={"items": [{"product_id": prod_id, "quantity": "12.00"}]},  # shop_id omitted
    )
    assert over_res.status_code == 400
    assert "Insufficient available stock" in over_res.json()["detail"]

    # Selling 10 with shop_id omitted infers authenticated shop owner's shop
    ok_res = client.post(
        "/api/v1/sales/",
        headers=headers,
        json={"items": [{"product_id": prod_id, "quantity": "10.00"}]},
    )
    assert ok_res.status_code == 201
    assert ok_res.json()["shop_id"] == shop_id

    # Verify physical dropped 25 -> 15 and reserved stayed untouched at 15
    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first()
    assert float(inv.quantity) == 15.00
    assert float(inv.reserved_quantity) == 15.00


def test_sale_for_another_shop_and_unauthorized_roles_rejected(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    other_shop = Location(location_name="Indiranagar Mart", location_type="SHOP", address="100ft Rd, Indiranagar")
    db_session.add(other_shop)
    db_session.commit()
    db_session.refresh(other_shop)

    db_session.add(Inventory(location_id=other_shop.location_id, product_id=sample_product.product_id, quantity=Decimal("30.00"), reserved_quantity=Decimal("0.00")))
    db_session.add(Inventory(location_id=sample_locations["warehouse"].location_id, product_id=sample_product.product_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00")))
    db_session.commit()

    shop_owner_headers = auth_headers("shop_owner")
    admin_headers = auth_headers("admin")

    # Shop owner cannot record a sale for another shop
    res_other = client.post(
        "/api/v1/sales/",
        headers=shop_owner_headers,
        json={"shop_id": other_shop.location_id, "items": [{"product_id": sample_product.product_id, "quantity": "2.00"}]},
    )
    assert res_other.status_code == 403

    # Shop owner cannot list sales of another shop
    assert client.get(f"/api/v1/sales/?shop_id={other_shop.location_id}", headers=shop_owner_headers).status_code == 403

    # Warehouse manager and worker cannot create or list sales
    for role in ("manager", "worker"):
        assert client.post(
            "/api/v1/sales/",
            headers=auth_headers(role),
            json={"shop_id": sample_locations["shop"].location_id, "items": [{"product_id": sample_product.product_id, "quantity": "1.00"}]},
        ).status_code == 403
        assert client.get("/api/v1/sales/", headers=auth_headers(role)).status_code == 403

    # Admin records a sale at other_shop; Shop 1 owner cannot view or cancel it
    admin_sale = client.post(
        "/api/v1/sales/",
        headers=admin_headers,
        json={"shop_id": other_shop.location_id, "items": [{"product_id": sample_product.product_id, "quantity": "2.00"}]},
    )
    assert admin_sale.status_code == 201
    other_sale_id = admin_sale.json()["sale_id"]

    assert client.get(f"/api/v1/sales/{other_sale_id}", headers=shop_owner_headers).status_code == 403
    assert client.post(f"/api/v1/sales/{other_sale_id}/cancel", headers=shop_owner_headers).status_code == 403

    # Even Admin cannot record a retail sale against a warehouse location
    wh_sale = client.post(
        "/api/v1/sales/",
        headers=admin_headers,
        json={"shop_id": sample_locations["warehouse"].location_id, "items": [{"product_id": sample_product.product_id, "quantity": "2.00"}]},
    )
    assert wh_sale.status_code == 400
    assert "not a SHOP" in wh_sale.json()["detail"]


def test_invalid_product_and_missing_shop_inventory_rejected(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    headers = auth_headers("shop_owner")

    # Non-existent product -> 404
    res_missing_prod = client.post(
        "/api/v1/sales/",
        headers=headers,
        json={"shop_id": shop_id, "items": [{"product_id": 999999, "quantity": "1.00"}]},
    )
    assert res_missing_prod.status_code == 404

    # Existing product with NO inventory record at this shop -> 400
    res_no_inv = client.post(
        "/api/v1/sales/",
        headers=headers,
        json={"shop_id": shop_id, "items": [{"product_id": sample_product.product_id, "quantity": "1.00"}]},
    )
    assert res_no_inv.status_code == 400
    assert "no inventory record" in res_no_inv.json()["detail"]


def test_monetary_calculations_negative_tax_discount_invalid_totals_and_price_manipulation(
    client: TestClient, sample_locations, sample_product, sample_users, db_session, auth_headers
):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id  # price = 145.00
    db_session.add(Inventory(location_id=shop_id, product_id=prod_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00")))
    db_session.commit()

    shop_headers = auth_headers("shop_owner")
    admin_headers = auth_headers("admin")

    # Negative tax and discount rejected by API validation (422)
    assert client.post(
        "/api/v1/sales/",
        headers=shop_headers,
        json={"items": [{"product_id": prod_id, "quantity": "1.00"}], "tax_amount": "-5.00"},
    ).status_code == 422
    assert client.post(
        "/api/v1/sales/",
        headers=shop_headers,
        json={"items": [{"product_id": prod_id, "quantity": "1.00"}], "discount_amount": "-5.00"},
    ).status_code == 422

    # Direct service-layer negative tax/discount rejected with 400
    svc = SaleService(db_session)
    bad_tax_req = SaleCreateRequest.model_construct(
        shop_id=shop_id,
        items=[SaleItemCreate.model_construct(product_id=prod_id, quantity=Decimal("1.00"), unit_price=None)],
        payment_method="CASH",
        tax_amount=Decimal("-1.00"),
        discount_amount=Decimal("0.00"),
        customer_name=None,
        customer_phone=None,
    )
    with pytest.raises(HTTPException) as exc_tax:
        svc.record_sale(sample_users["shop_owner"], bad_tax_req)
    assert exc_tax.value.status_code == 400

    # Discount exceeding subtotal + tax (would produce negative total) MUST be rejected, NOT clamped to 0
    neg_total_res = client.post(
        "/api/v1/sales/",
        headers=shop_headers,
        json={
            "items": [{"product_id": prod_id, "quantity": "1.00"}],  # subtotal = 145.00
            "tax_amount": "5.00",
            "discount_amount": "200.00",  # 145 + 5 - 200 = -50 < 0
        },
    )
    assert neg_total_res.status_code == 400
    assert "negative" in neg_total_res.json()["detail"].lower()

    # Invalid payment method rejected
    bad_pm = client.post(
        "/api/v1/sales/",
        headers=shop_headers,
        json={"items": [{"product_id": prod_id, "quantity": "1.00"}], "payment_method": "CRYPTO"},
    )
    assert bad_pm.status_code == 400

    # Unauthorized unit_price manipulation by SHOP_OWNER rejected (403)
    manipulated = client.post(
        "/api/v1/sales/",
        headers=shop_headers,
        json={"items": [{"product_id": prod_id, "quantity": "2.00", "unit_price": "1.00"}]},
    )
    assert manipulated.status_code == 403

    # Exact catalog unit_price by SHOP_OWNER succeeds (201)
    exact_price = client.post(
        "/api/v1/sales/",
        headers=shop_headers,
        json={"items": [{"product_id": prod_id, "quantity": "2.00", "unit_price": "145.00"}], "tax_amount": "10.25", "discount_amount": "5.10"},
    )
    assert exact_price.status_code == 201
    assert Decimal(str(exact_price.json()["subtotal"])) == Decimal("290.00")
    assert Decimal(str(exact_price.json()["total_amount"])) == Decimal("295.15")

    # Admin may apply an authorized custom unit price
    admin_override = client.post(
        "/api/v1/sales/",
        headers=admin_headers,
        json={"shop_id": shop_id, "items": [{"product_id": prod_id, "quantity": "2.00", "unit_price": "140.00"}]},
    )
    assert admin_override.status_code == 201
    assert Decimal(str(admin_override.json()["total_amount"])) == Decimal("280.00")


def test_failed_multi_item_sale_rolls_back_all_changes(client: TestClient, sample_locations, sample_product, db_session, auth_headers):
    shop_id = sample_locations["shop"].location_id
    prod1 = sample_product
    prod2 = Product(
        product_name="Toor Dal 1kg",
        category="Pulses",
        unit="Pack",
        price=Decimal("160.00"),
        reorder_threshold=Decimal("10.00"),
        sku="DAL-TD-1KG",
    )
    db_session.add(prod2)
    db_session.commit()
    db_session.refresh(prod2)

    db_session.add_all([
        Inventory(location_id=shop_id, product_id=prod1.product_id, quantity=Decimal("40.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=shop_id, product_id=prod2.product_id, quantity=Decimal("2.00"), reserved_quantity=Decimal("0.00")),
    ])
    db_session.commit()

    headers = auth_headers("shop_owner")

    # Item 1 (10 <= 40) is valid, Item 2 (5 > 2) fails -> entire sale rolls back
    res = client.post(
        "/api/v1/sales/",
        headers=headers,
        json={
            "items": [
                {"product_id": prod1.product_id, "quantity": "10.00"},
                {"product_id": prod2.product_id, "quantity": "5.00"},
            ]
        },
    )
    assert res.status_code == 400

    # Duplicate product lines cumulatively exceeding stock (25 + 20 = 45 > 40) also roll back
    dup_res = client.post(
        "/api/v1/sales/",
        headers=headers,
        json={
            "items": [
                {"product_id": prod1.product_id, "quantity": "25.00"},
                {"product_id": prod1.product_id, "quantity": "20.00"},
            ]
        },
    )
    assert dup_res.status_code == 400

    db_session.expire_all()
    assert db_session.query(Sale).count() == 0
    assert db_session.query(SaleItem).count() == 0
    assert float(db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod1.product_id).first().quantity) == 40.00
    assert float(db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod2.product_id).first().quantity) == 2.00


def test_sale_status_transitions_and_cancellation_preserves_reserved_stock(
    client: TestClient, sample_locations, sample_product, sample_users, db_session, auth_headers
):
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id
    db_session.add(Inventory(location_id=shop_id, product_id=prod_id, quantity=Decimal("30.00"), reserved_quantity=Decimal("10.00")))
    db_session.commit()

    headers = auth_headers("shop_owner")

    # Sale 1: sell 8 -> physical 30 -> 22, reserved stays 10
    s1 = client.post("/api/v1/sales/", headers=headers, json={"items": [{"product_id": prod_id, "quantity": "8.00"}]})
    assert s1.status_code == 201
    s1_id = s1.json()["sale_id"]

    # Cancel Sale 1 -> physical 22 -> 30, reserved stays 10
    assert client.post(f"/api/v1/sales/{s1_id}/cancel", headers=headers).status_code == 200
    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first()
    assert float(inv.quantity) == 30.00
    assert float(inv.reserved_quantity) == 10.00

    # Invalid transitions from CANCELLED (repeat cancel or refund) must be rejected without restoring stock again
    assert client.post(f"/api/v1/sales/{s1_id}/cancel", headers=headers).status_code == 400
    assert client.post(f"/api/v1/sales/{s1_id}/refund", headers=headers).status_code == 400

    # Sale 2: sell 5 -> refund -> invalid cancel after refund rejected
    s2 = client.post("/api/v1/sales/", headers=headers, json={"items": [{"product_id": prod_id, "quantity": "5.00"}]})
    assert s2.status_code == 201
    s2_id = s2.json()["sale_id"]

    assert client.post(f"/api/v1/sales/{s2_id}/refund", headers=headers).status_code == 200
    assert client.post(f"/api/v1/sales/{s2_id}/cancel", headers=headers).status_code == 400
    assert client.post(f"/api/v1/sales/{s2_id}/refund", headers=headers).status_code == 400

    # Invalid action value at service layer rejected
    svc = SaleService(db_session)
    with pytest.raises(HTTPException) as exc:
        svc.cancel_or_refund_sale(sample_users["shop_owner"], s2_id, "COMPLETED")
    assert exc.value.status_code == 400

    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=prod_id).first()
    assert float(inv.quantity) == 30.00
    assert float(inv.reserved_quantity) == 10.00


def test_integration_shop_sale_preserves_warehouse_allocations_and_reservations(
    client: TestClient, sample_locations, sample_product, db_session, auth_headers
):
    wh_id = sample_locations["warehouse"].location_id
    shop_id = sample_locations["shop"].location_id
    prod_id = sample_product.product_id

    # Warehouse has 50 physical, 20 reserved for an active outgoing order allocation
    db_session.add(Inventory(location_id=wh_id, product_id=prod_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("20.00")))
    # Shop has 40 physical, 5 reserved
    db_session.add(Inventory(location_id=shop_id, product_id=prod_id, quantity=Decimal("40.00"), reserved_quantity=Decimal("5.00")))
    order = Order(shop_id=shop_id, status="PROCESSING")
    db_session.add(order)
    db_session.commit()
    item = OrderItem(order_id=order.order_id, product_id=prod_id, quantity_requested=Decimal("20.00"), quantity_allocated=Decimal("20.00"))
    db_session.add(item)
    db_session.commit()
    alloc = OrderAllocation(order_item_id=item.order_item_id, source_location_id=wh_id, allocated_quantity=Decimal("20.00"), status="RESERVED")
    db_session.add(alloc)
    db_session.commit()
    res_rec = StockReservation(allocation_id=alloc.allocation_id, quantity_reserved=Decimal("20.00"), status="ACTIVE")
    db_session.add(res_rec)
    db_session.commit()

    # Completed shop sale of 15 units
    sale_res = client.post(
        "/api/v1/sales/",
        headers=auth_headers("shop_owner"),
        json={"items": [{"product_id": prod_id, "quantity": "15.00"}]},
    )
    assert sale_res.status_code == 201

    # Verify warehouse stock, reservation, and allocation are completely untouched
    db_session.expire_all()
    wh_inv = db_session.query(Inventory).filter_by(location_id=wh_id, product_id=prod_id).first()
    assert float(wh_inv.quantity) == 50.00
    assert float(wh_inv.reserved_quantity) == 20.00
    assert db_session.query(StockReservation).filter_by(reservation_id=res_rec.reservation_id).first().status == "ACTIVE"
    assert db_session.query(OrderAllocation).filter_by(allocation_id=alloc.allocation_id).first().status == "RESERVED"

    # Shop inventory summary reflects the sale immediately without altering reserved stock
    summary = client.get(f"/api/v1/inventory/locations/{shop_id}/summary", headers=auth_headers("shop_owner"))
    assert summary.status_code == 200
    sdata = summary.json()
    assert float(sdata["total_physical_quantity"]) == 25.00
    assert float(sdata["total_reserved_quantity"]) == 5.00
    assert float(sdata["total_available_quantity"]) == 20.00
    assert sdata["low_stock_count"] == 1  # available 20 <= reorder_threshold 20
    assert sdata["out_of_stock_count"] == 0
