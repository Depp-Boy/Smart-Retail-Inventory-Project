import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.models.allocation import OrderAllocation
from app.models.order import Order, OrderItem


def setup_worker_task_fixture(db_session, sample_locations, sample_product):
    wh = sample_locations["warehouse"]
    order = Order(shop_id=sample_locations["shop"].location_id, status="PROCESSING")
    db_session.add(order)
    db_session.commit()

    item = OrderItem(order_id=order.order_id, product_id=sample_product.product_id, quantity_requested=Decimal("15.00"), quantity_allocated=Decimal("15.00"))
    db_session.add(item)
    db_session.commit()

    alloc = OrderAllocation(order_item_id=item.order_item_id, source_location_id=wh.location_id, allocated_quantity=Decimal("15.00"), status="ALLOCATED")
    db_session.add(alloc)
    db_session.commit()
    db_session.refresh(alloc)

    return {"alloc": alloc}


def test_create_worker_task_by_manager(client: TestClient, sample_locations, sample_users, sample_product, db_session, auth_headers):
    data = setup_worker_task_fixture(db_session, sample_locations, sample_product)
    manager_headers = auth_headers("manager")
    worker = sample_users["worker"]

    payload = {
        "assigned_worker_id": worker.user_id,
        "task_type": "PICKING",
        "priority": "HIGH",
        "allocation_id": data["alloc"].allocation_id,
        "instructions": "Pick 15 pouches of sunflower oil from Zone B",
        "items": [{"product_id": sample_product.product_id, "quantity": "15.00"}],
    }
    res = client.post("/api/v1/tasks/", headers=manager_headers, json=payload)
    assert res.status_code == 201
    task = res.json()
    assert task["task_type"] == "PICKING"
    assert task["priority"] == "HIGH"
    assert task["status"] == "PENDING"
    assert len(task["items"]) == 1


def test_worker_task_creation_rejected_for_unauthorized_role(client: TestClient, sample_locations, sample_users, sample_product, db_session, auth_headers):
    data = setup_worker_task_fixture(db_session, sample_locations, sample_product)
    worker_headers = auth_headers("worker")

    payload = {
        "assigned_worker_id": sample_users["worker"].user_id,
        "task_type": "PICKING",
        "allocation_id": data["alloc"].allocation_id,
    }
    res = client.post("/api/v1/tasks/", headers=worker_headers, json=payload)
    assert res.status_code == 403


def test_worker_task_item_progress_update(client: TestClient, sample_locations, sample_users, sample_product, db_session, auth_headers):
    data = setup_worker_task_fixture(db_session, sample_locations, sample_product)
    manager_headers = auth_headers("manager")
    worker_headers = auth_headers("worker")
    worker = sample_users["worker"]

    # 1. Create task
    create_res = client.post(
        "/api/v1/tasks/",
        headers=manager_headers,
        json={
            "assigned_worker_id": worker.user_id,
            "task_type": "PACKING",
            "allocation_id": data["alloc"].allocation_id,
            "items": [{"product_id": sample_product.product_id, "quantity": "10.00"}],
        },
    )
    task_id = create_res.json()["task_id"]
    item_id = create_res.json()["items"][0]["task_item_id"]

    # 2. Worker updates progress to 5 -> IN_PROGRESS
    prog1 = client.patch(
        f"/api/v1/tasks/{task_id}/items/{item_id}/progress",
        headers=worker_headers,
        json={"completed_quantity": "5.00"},
    )
    assert prog1.status_code == 200
    assert prog1.json()["status"] == "IN_PROGRESS"

    # 3. Worker updates progress to 10 -> COMPLETED
    prog2 = client.patch(
        f"/api/v1/tasks/{task_id}/items/{item_id}/progress",
        headers=worker_headers,
        json={"completed_quantity": "10.00"},
    )
    assert prog2.status_code == 200
    assert prog2.json()["status"] == "COMPLETED"
    assert prog2.json()["completed_at"] is not None


def test_completed_quantity_exceeding_total_rejected(client: TestClient, sample_locations, sample_users, sample_product, db_session, auth_headers):
    data = setup_worker_task_fixture(db_session, sample_locations, sample_product)
    manager_headers = auth_headers("manager")
    worker_headers = auth_headers("worker")
    worker = sample_users["worker"]

    create_res = client.post(
        "/api/v1/tasks/",
        headers=manager_headers,
        json={
            "assigned_worker_id": worker.user_id,
            "task_type": "PACKING",
            "allocation_id": data["alloc"].allocation_id,
            "items": [{"product_id": sample_product.product_id, "quantity": "5.00"}],
        },
    )
    task_id = create_res.json()["task_id"]
    item_id = create_res.json()["items"][0]["task_item_id"]

    # Cannot complete 12 when quantity is 5
    res = client.patch(
        f"/api/v1/tasks/{task_id}/items/{item_id}/progress",
        headers=worker_headers,
        json={"completed_quantity": "12.00"},
    )
    assert res.status_code == 400
    assert "cannot exceed assigned quantity" in res.json()["detail"]
