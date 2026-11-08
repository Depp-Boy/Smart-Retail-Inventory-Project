import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.models.inventory import Inventory
from app.models.product import Product


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
