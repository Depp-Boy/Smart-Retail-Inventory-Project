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
from app.models.user import User
from app.services.worker_task_service import WorkerTaskService


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

    return {"wh": wh, "order": order, "item": item, "alloc": alloc}


def _auth_for(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.user_id), "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


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


def test_manager_cannot_assign_task_to_other_warehouse_worker_or_allocation(
    client: TestClient, sample_locations, sample_users, sample_product, db_session, auth_headers
):
    data = setup_worker_task_fixture(db_session, sample_locations, sample_product)

    wh2 = Location(location_name="East Hub", location_type="SUB_WAREHOUSE", address="East Industrial Zone")
    db_session.add(wh2)
    db_session.commit()
    db_session.refresh(wh2)

    worker_wh2 = User(
        name="WH2 Worker",
        email="worker_wh2@test.com",
        password_hash=hash_password("worker2"),
        role="WAREHOUSE_WORKER",
        location_id=wh2.location_id,
    )
    alloc_wh2 = OrderAllocation(
        order_item_id=data["item"].order_item_id,
        source_location_id=wh2.location_id,
        allocated_quantity=Decimal("10.00"),
        status="ALLOCATED",
    )
    db_session.add_all([worker_wh2, alloc_wh2])
    db_session.commit()

    mgr1_headers = auth_headers("manager")

    # Manager 1 cannot assign task to WH2 worker
    res_other_worker = client.post(
        "/api/v1/tasks/",
        headers=mgr1_headers,
        json={
            "assigned_worker_id": worker_wh2.user_id,
            "task_type": "PICKING",
            "allocation_id": data["alloc"].allocation_id,
            "items": [{"product_id": sample_product.product_id, "quantity": "5.00"}],
        },
    )
    assert res_other_worker.status_code == 403

    # Manager 1 cannot assign task referencing WH2 allocation
    res_other_alloc = client.post(
        "/api/v1/tasks/",
        headers=mgr1_headers,
        json={
            "assigned_worker_id": sample_users["worker"].user_id,
            "task_type": "PICKING",
            "allocation_id": alloc_wh2.allocation_id,
            "items": [{"product_id": sample_product.product_id, "quantity": "5.00"}],
        },
    )
    assert res_other_alloc.status_code == 403

    # Assigning task to a non-worker role rejected
    res_non_worker = client.post(
        "/api/v1/tasks/",
        headers=mgr1_headers,
        json={
            "assigned_worker_id": sample_users["shop_owner"].user_id,
            "task_type": "PICKING",
            "allocation_id": data["alloc"].allocation_id,
        },
    )
    assert res_non_worker.status_code == 400


def test_task_creation_validates_references_types_priorities_and_items(
    client: TestClient, sample_locations, sample_users, sample_product, db_session, auth_headers
):
    data = setup_worker_task_fixture(db_session, sample_locations, sample_product)
    mgr_headers = auth_headers("manager")
    worker_id = sample_users["worker"].user_id

    wrong_prod = Product(product_name="Unrelated Soap", category="Personal Care", unit="Bar", price=Decimal("40.00"), reorder_threshold=Decimal("5.00"), sku="SOAP-1")
    db_session.add(wrong_prod)
    db_session.commit()

    # Non-existent allocation / dispatch -> 404
    assert client.post("/api/v1/tasks/", headers=mgr_headers, json={"assigned_worker_id": worker_id, "task_type": "PICKING", "allocation_id": 999999}).status_code == 404
    assert client.post("/api/v1/tasks/", headers=mgr_headers, json={"assigned_worker_id": worker_id, "task_type": "DISPATCH", "dispatch_id": 999999}).status_code == 404

    # Invalid task_type and priority -> 400
    assert client.post("/api/v1/tasks/", headers=mgr_headers, json={"assigned_worker_id": worker_id, "task_type": "DRIVING", "allocation_id": data["alloc"].allocation_id}).status_code == 400
    assert client.post("/api/v1/tasks/", headers=mgr_headers, json={"assigned_worker_id": worker_id, "task_type": "PICKING", "priority": "URGENT", "allocation_id": data["alloc"].allocation_id}).status_code == 400

    # Wrong product in task items -> 400
    res_wrong_prod = client.post(
        "/api/v1/tasks/",
        headers=mgr_headers,
        json={
            "assigned_worker_id": worker_id,
            "task_type": "PICKING",
            "allocation_id": data["alloc"].allocation_id,
            "items": [{"product_id": wrong_prod.product_id, "quantity": "5.00"}],
        },
    )
    assert res_wrong_prod.status_code == 400

    # Quantity exceeding allocation (20 > 15) -> 400
    res_over_qty = client.post(
        "/api/v1/tasks/",
        headers=mgr_headers,
        json={
            "assigned_worker_id": worker_id,
            "task_type": "PICKING",
            "allocation_id": data["alloc"].allocation_id,
            "items": [{"product_id": sample_product.product_id, "quantity": "20.00"}],
        },
    )
    assert res_over_qty.status_code == 400

    # Duplicate product in task items -> 400
    res_dup = client.post(
        "/api/v1/tasks/",
        headers=mgr_headers,
        json={
            "assigned_worker_id": worker_id,
            "task_type": "PICKING",
            "allocation_id": data["alloc"].allocation_id,
            "items": [
                {"product_id": sample_product.product_id, "quantity": "5.00"},
                {"product_id": sample_product.product_id, "quantity": "5.00"},
            ],
        },
    )
    assert res_dup.status_code == 400

    # Contradictory allocation + dispatch reference -> 400
    db_session.add(Inventory(location_id=data["wh"].location_id, product_id=sample_product.product_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00")))
    alloc_other = OrderAllocation(order_item_id=data["item"].order_item_id, source_location_id=data["wh"].location_id, allocated_quantity=Decimal("10.00"), status="ALLOCATED")
    db_session.add(alloc_other)
    db_session.commit()

    dsp = client.post(
        "/api/v1/dispatches/",
        headers=mgr_headers,
        json={
            "order_id": data["order"].order_id,
            "source_location_id": data["wh"].location_id,
            "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "10.00"}],
        },
    )
    assert dsp.status_code == 201
    dsp_id = dsp.json()["dispatch_id"]

    res_contra = client.post(
        "/api/v1/tasks/",
        headers=mgr_headers,
        json={
            "assigned_worker_id": worker_id,
            "task_type": "DISPATCH",
            "allocation_id": alloc_other.allocation_id,
            "dispatch_id": dsp_id,
        },
    )
    assert res_contra.status_code == 400
    assert "Contradictory" in res_contra.json()["detail"]

    # Valid DISPATCH task with matching dispatch and item quantity succeeds
    res_ok = client.post(
        "/api/v1/tasks/",
        headers=mgr_headers,
        json={
            "assigned_worker_id": worker_id,
            "task_type": "DISPATCH",
            "dispatch_id": dsp_id,
            "items": [{"product_id": sample_product.product_id, "quantity": "10.00"}],
        },
    )
    assert res_ok.status_code == 201


def test_task_and_worker_visibility_isolation(client: TestClient, sample_locations, sample_users, sample_product, db_session, auth_headers):
    data = setup_worker_task_fixture(db_session, sample_locations, sample_product)

    # Second worker in WH1, plus WH2 with manager2 and worker_wh2
    worker1b = User(name="WH1 Worker B", email="worker1b@test.com", password_hash=hash_password("w1b"), role="WAREHOUSE_WORKER", location_id=data["wh"].location_id)
    wh2 = Location(location_name="North Hub", location_type="SUB_WAREHOUSE", address="North Rd")
    db_session.add_all([worker1b, wh2])
    db_session.commit()
    db_session.refresh(worker1b)
    db_session.refresh(wh2)

    mgr2 = User(name="WH2 Manager", email="mgr2_vis@test.com", password_hash=hash_password("m2"), role="WAREHOUSE_MANAGER", location_id=wh2.location_id)
    worker2 = User(name="WH2 Worker", email="worker2_vis@test.com", password_hash=hash_password("w2"), role="WAREHOUSE_WORKER", location_id=wh2.location_id)
    alloc2 = OrderAllocation(order_item_id=data["item"].order_item_id, source_location_id=wh2.location_id, allocated_quantity=Decimal("10.00"), status="ALLOCATED")
    db_session.add_all([mgr2, worker2, alloc2])
    db_session.commit()

    mgr1_h = auth_headers("manager")
    worker1_h = auth_headers("worker")
    worker1b_h = _auth_for(worker1b)
    mgr2_h = _auth_for(mgr2)
    admin_h = auth_headers("admin")
    shop_h = auth_headers("shop_owner")

    # Create task for worker1 in WH1 and task for worker2 in WH2
    t1 = client.post("/api/v1/tasks/", headers=mgr1_h, json={"assigned_worker_id": sample_users["worker"].user_id, "task_type": "PICKING", "allocation_id": data["alloc"].allocation_id}).json()
    t2 = client.post("/api/v1/tasks/", headers=mgr2_h, json={"assigned_worker_id": worker2.user_id, "task_type": "PICKING", "allocation_id": alloc2.allocation_id}).json()

    # Worker 1B cannot access Worker 1's task by ID or list Worker 1's tasks
    assert client.get(f"/api/v1/tasks/{t1['task_id']}", headers=worker1b_h).status_code == 403
    assert client.get(f"/api/v1/workers/{sample_users['worker'].user_id}/tasks", headers=worker1b_h).status_code == 403
    assert client.get(f"/api/v1/tasks/?worker_id={sample_users['worker'].user_id}", headers=worker1b_h).status_code == 403

    # Worker 1 sees only their own task
    w1_list = client.get("/api/v1/tasks/", headers=worker1_h)
    assert w1_list.status_code == 200
    assert [t["task_id"] for t in w1_list.json()] == [t1["task_id"]]

    # Manager 1 cannot access WH2 tasks or WH2 workers via ID or query params
    assert client.get(f"/api/v1/tasks/{t2['task_id']}", headers=mgr1_h).status_code == 403
    assert client.get(f"/api/v1/workers/warehouse/{wh2.location_id}/tasks", headers=mgr1_h).status_code == 403
    assert client.get(f"/api/v1/tasks/?warehouse_id={wh2.location_id}", headers=mgr1_h).status_code == 403
    assert client.get(f"/api/v1/workers/{worker2.user_id}/tasks", headers=mgr1_h).status_code == 403
    assert client.get(f"/api/v1/workers/?warehouse_id={wh2.location_id}", headers=mgr1_h).status_code == 403

    # Manager 1 listing /workers/ without param sees only WH1 workers
    mgr1_workers = client.get("/api/v1/workers/", headers=mgr1_h)
    assert mgr1_workers.status_code == 200
    assert all(w["location_id"] == data["wh"].location_id for w in mgr1_workers.json())

    # Shop owner is denied task access
    assert client.get("/api/v1/tasks/", headers=shop_h).status_code == 403
    assert client.get(f"/api/v1/tasks/{t1['task_id']}", headers=shop_h).status_code == 403

    # Admin can access tasks across both warehouses
    admin_list = client.get("/api/v1/tasks/", headers=admin_h)
    assert admin_list.status_code == 200
    assert {t["task_id"] for t in admin_list.json()} == {t1["task_id"], t2["task_id"]}
    assert client.get(f"/api/v1/tasks/{t2['task_id']}", headers=admin_h).status_code == 200


def test_task_progress_ownership_item_mismatch_negative_and_multi_item_completion(
    client: TestClient, sample_locations, sample_users, sample_product, db_session, auth_headers
):
    data = setup_worker_task_fixture(db_session, sample_locations, sample_product)
    prod2 = Product(product_name="Sugar 1kg", category="Grocery", unit="Pack", price=Decimal("45.00"), reorder_threshold=Decimal("5.00"), sku="SUG-WT-1")
    db_session.add(prod2)
    db_session.commit()

    # Seed inventory & dispatch with 2 products so we can test multi-item task progress
    db_session.add_all([
        Inventory(location_id=data["wh"].location_id, product_id=sample_product.product_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=data["wh"].location_id, product_id=prod2.product_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00")),
    ])
    oi2 = OrderItem(order_id=data["order"].order_id, product_id=prod2.product_id, quantity_requested=Decimal("10.00"), quantity_allocated=Decimal("10.00"))
    db_session.add(oi2)
    db_session.commit()
    alloc2 = OrderAllocation(order_item_id=oi2.order_item_id, source_location_id=data["wh"].location_id, allocated_quantity=Decimal("10.00"), status="ALLOCATED")
    db_session.add(alloc2)
    db_session.commit()

    mgr_h = auth_headers("manager")
    worker1_h = auth_headers("worker")

    worker1b = User(name="Other Worker", email="w1b_prog@test.com", password_hash=hash_password("w1b"), role="WAREHOUSE_WORKER", location_id=data["wh"].location_id)
    db_session.add(worker1b)
    db_session.commit()
    worker1b_h = _auth_for(worker1b)

    dsp = client.post(
        "/api/v1/dispatches/",
        headers=mgr_h,
        json={
            "order_id": data["order"].order_id,
            "source_location_id": data["wh"].location_id,
            "items": [
                {"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "10.00"},
                {"allocation_id": alloc2.allocation_id, "product_id": prod2.product_id, "quantity": "5.00"},
            ],
        },
    ).json()

    t1 = client.post(
        "/api/v1/tasks/",
        headers=mgr_h,
        json={
            "assigned_worker_id": sample_users["worker"].user_id,
            "task_type": "PACKING",
            "dispatch_id": dsp["dispatch_id"],
            "items": [
                {"product_id": sample_product.product_id, "quantity": "10.00"},
                {"product_id": prod2.product_id, "quantity": "5.00"},
            ],
        },
    ).json()
    t2 = client.post(
        "/api/v1/tasks/",
        headers=mgr_h,
        json={
            "assigned_worker_id": worker1b.user_id,
            "task_type": "PICKING",
            "allocation_id": alloc2.allocation_id,
            "items": [{"product_id": prod2.product_id, "quantity": "5.00"}],
        },
    ).json()

    t1_item1 = t1["items"][0]["task_item_id"]
    t1_item2 = t1["items"][1]["task_item_id"]
    t2_item1 = t2["items"][0]["task_item_id"]

    # Worker 1B cannot update Worker 1's task
    assert client.patch(f"/api/v1/tasks/{t1['task_id']}/items/{t1_item1}/progress", headers=worker1b_h, json={"completed_quantity": "2.00"}).status_code == 403

    # Worker 1 cannot modify an item belonging to Task 2 via Task 1 URL
    assert client.patch(f"/api/v1/tasks/{t1['task_id']}/items/{t2_item1}/progress", headers=worker1_h, json={"completed_quantity": "2.00"}).status_code == 404

    # Negative completed_quantity rejected (422 via HTTP, 400 via service)
    assert client.patch(f"/api/v1/tasks/{t1['task_id']}/items/{t1_item1}/progress", headers=worker1_h, json={"completed_quantity": "-1.00"}).status_code == 422
    with pytest.raises(HTTPException) as neg_exc:
        WorkerTaskService(db_session).update_task_progress(t1["task_id"], t1_item1, Decimal("-1.00"), actor=sample_users["worker"])
    assert neg_exc.value.status_code == 400

    # Completing item 1 only moves task to IN_PROGRESS (NOT COMPLETED)
    p1 = client.patch(f"/api/v1/tasks/{t1['task_id']}/items/{t1_item1}/progress", headers=worker1_h, json={"completed_quantity": "10.00"})
    assert p1.status_code == 200
    assert p1.json()["status"] == "IN_PROGRESS"
    assert p1.json()["completed_at"] is None

    # Completing item 2 transitions task to COMPLETED and sets completed_at
    p2 = client.patch(f"/api/v1/tasks/{t1['task_id']}/items/{t1_item2}/progress", headers=worker1_h, json={"completed_quantity": "5.00"})
    assert p2.status_code == 200
    assert p2.json()["status"] == "COMPLETED"
    assert p2.json()["completed_at"] is not None


def test_task_status_transitions_worker_restrictions_and_admin_reopen(
    client: TestClient, sample_locations, sample_users, sample_product, db_session, auth_headers
):
    data = setup_worker_task_fixture(db_session, sample_locations, sample_product)
    mgr_h = auth_headers("manager")
    worker_h = auth_headers("worker")

    t = client.post(
        "/api/v1/tasks/",
        headers=mgr_h,
        json={
            "assigned_worker_id": sample_users["worker"].user_id,
            "task_type": "PACKING",
            "allocation_id": data["alloc"].allocation_id,
            "items": [{"product_id": sample_product.product_id, "quantity": "10.00"}],
        },
    ).json()
    task_id = t["task_id"]
    item_id = t["items"][0]["task_item_id"]

    # Worker cannot arbitrarily cancel task -> 403
    assert client.patch(f"/api/v1/tasks/{task_id}/status", headers=worker_h, json={"status": "CANCELLED"}).status_code == 403

    # Worker cannot jump PENDING -> COMPLETED -> 400
    assert client.patch(f"/api/v1/tasks/{task_id}/status", headers=worker_h, json={"status": "COMPLETED"}).status_code == 400

    # Worker starts task: PENDING -> IN_PROGRESS -> 200
    assert client.patch(f"/api/v1/tasks/{task_id}/status", headers=worker_h, json={"status": "IN_PROGRESS"}).status_code == 200

    # Worker cannot manually mark unfinished task COMPLETED -> 400
    assert client.patch(f"/api/v1/tasks/{task_id}/status", headers=worker_h, json={"status": "COMPLETED"}).status_code == 400

    # Complete item -> task auto-transitions to COMPLETED with completed_at set
    done = client.patch(f"/api/v1/tasks/{task_id}/items/{item_id}/progress", headers=worker_h, json={"completed_quantity": "10.00"})
    assert done.status_code == 200
    assert done.json()["status"] == "COMPLETED"
    assert done.json()["completed_at"] is not None

    # Worker cannot reopen completed task -> 403
    assert client.patch(f"/api/v1/tasks/{task_id}/status", headers=worker_h, json={"status": "IN_PROGRESS"}).status_code == 403

    # Manager can administratively reopen COMPLETED -> IN_PROGRESS, which clears completed_at
    reopened = client.patch(f"/api/v1/tasks/{task_id}/status", headers=mgr_h, json={"status": "IN_PROGRESS"})
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "IN_PROGRESS"
    assert reopened.json()["completed_at"] is None

    # Manager cancels IN_PROGRESS task -> CANCELLED; cannot transition out of CANCELLED
    cancelled = client.patch(f"/api/v1/tasks/{task_id}/status", headers=mgr_h, json={"status": "CANCELLED"})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert client.patch(f"/api/v1/tasks/{task_id}/status", headers=mgr_h, json={"status": "IN_PROGRESS"}).status_code == 400


def test_worker_dispatch_integration_and_no_double_stock_deduction(
    client: TestClient, sample_locations, sample_users, sample_product, db_session, auth_headers
):
    data = setup_worker_task_fixture(db_session, sample_locations, sample_product)
    db_session.add(Inventory(location_id=data["wh"].location_id, product_id=sample_product.product_id, quantity=Decimal("100.00"), reserved_quantity=Decimal("0.00")))
    db_session.commit()

    mgr_h = auth_headers("manager")
    worker_h = auth_headers("worker")

    # Create dispatch for 15 units -> inventory drops 100 -> 85
    dsp = client.post(
        "/api/v1/dispatches/",
        headers=mgr_h,
        json={
            "order_id": data["order"].order_id,
            "source_location_id": data["wh"].location_id,
            "items": [{"allocation_id": data["alloc"].allocation_id, "product_id": sample_product.product_id, "quantity": "15.00"}],
        },
    )
    assert dsp.status_code == 201
    dsp_id = dsp.json()["dispatch_id"]

    # Worker with only a PICKING task cannot update dispatch status -> 403
    client.post(
        "/api/v1/tasks/",
        headers=mgr_h,
        json={
            "assigned_worker_id": sample_users["worker"].user_id,
            "task_type": "PICKING",
            "dispatch_id": dsp_id,
            "items": [{"product_id": sample_product.product_id, "quantity": "15.00"}],
        },
    )
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker_h, json={"status": "PACKING"}).status_code == 403

    # Assign valid DISPATCH task to Worker 1
    dt = client.post(
        "/api/v1/tasks/",
        headers=mgr_h,
        json={
            "assigned_worker_id": sample_users["worker"].user_id,
            "task_type": "DISPATCH",
            "dispatch_id": dsp_id,
            "items": [{"product_id": sample_product.product_id, "quantity": "15.00"}],
        },
    ).json()

    # Completing the worker task must NOT deduct inventory a second time (stays 85.00)
    dt_item_id = dt["items"][0]["task_item_id"]
    assert client.patch(f"/api/v1/tasks/{dt['task_id']}/items/{dt_item_id}/progress", headers=worker_h, json={"completed_quantity": "15.00"}).status_code == 200
    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 85.00

    # Worker cannot bypass dispatch state machine (PENDING -> IN_TRANSIT -> 400)
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker_h, json={"status": "IN_TRANSIT"}).status_code == 400

    # Worker with DISPATCH task can step PENDING -> PACKING -> READY -> IN_TRANSIT
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker_h, json={"status": "PACKING"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker_h, json={"status": "CANCELLED"}).status_code == 403
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker_h, json={"status": "READY"}).status_code == 200
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker_h, json={"status": "IN_TRANSIT"}).status_code == 200

    # Worker cannot mark dispatch DELIVERED -> 403
    assert client.patch(f"/api/v1/dispatches/{dsp_id}/status", headers=worker_h, json={"status": "DELIVERED"}).status_code == 403

    # Inventory remains 85.00 throughout
    db_session.expire_all()
    inv = db_session.query(Inventory).filter_by(location_id=data["wh"].location_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 85.00


def test_create_worker_authorization_password_hashing_and_audit(
    client: TestClient, sample_locations, sample_users, db_session, auth_headers
):
    from unittest.mock import patch
    import mongomock
    from app.core.config import Settings
    from app.core.security import verify_password
    from app.services.audit_service import AuditLogService

    wh1_id = sample_locations["warehouse"].location_id
    shop_id = sample_locations["shop"].location_id

    wh2 = Location(location_name="West Regional Hub", location_type="SUB_WAREHOUSE", address="Peenya Industrial Area")
    db_session.add(wh2)
    db_session.commit()
    db_session.refresh(wh2)

    mock_client = mongomock.MongoClient(tz_aware=True)
    fake_settings = Settings(MONGODB_URL="mongodb://localhost:27017", MONGODB_DB_NAME="test_worker_audit")
    AuditLogService.close_client()

    with patch("app.services.audit_service.get_settings", return_value=fake_settings), patch.object(
        AuditLogService, "_create_mongo_client", return_value=mock_client
    ):
        col = mock_client["test_worker_audit"]["audit_logs"]

        # 1. SHOP_OWNER and WAREHOUSE_WORKER are forbidden (403)
        for forbidden_role in ("shop_owner", "worker"):
            r = client.post(
                "/api/v1/workers/",
                headers=auth_headers(forbidden_role),
                json={"name": "Blocked Worker", "email": f"blocked_{forbidden_role}@test.com", "password": "WorkerPass123"},
            )
            assert r.status_code == 403

        # 2. WAREHOUSE_MANAGER cannot create a worker in another warehouse (403)
        cross_wh = client.post(
            "/api/v1/workers/",
            headers=auth_headers("manager"),
            json={
                "name": "Cross WH Worker",
                "email": "crosswh@test.com",
                "password": "WorkerPass123",
                "location_id": wh2.location_id,
            },
        )
        assert cross_wh.status_code == 403

        # 3. WAREHOUSE_MANAGER creates a worker in their own warehouse (location_id inferred)
        mgr_res = client.post(
            "/api/v1/workers/",
            headers=auth_headers("manager"),
            json={
                "name": "Kiran Picker",
                "email": "kiran.picker@test.com",
                "password": "KiranSecretPassword1",
                "phone": "+91 98111 22222",
            },
        )
        assert mgr_res.status_code == 201
        mgr_body = mgr_res.json()
        assert mgr_body["role"] == "WAREHOUSE_WORKER"
        assert mgr_body["location_id"] == wh1_id
        assert "password" not in mgr_body
        assert "password_hash" not in mgr_body

        # Verify password is stored hashed (never plaintext) and worker can log in
        db_session.expire_all()
        db_kiran = db_session.query(User).filter_by(email="kiran.picker@test.com").first()
        assert db_kiran is not None
        assert db_kiran.password_hash != "KiranSecretPassword1"
        assert verify_password("KiranSecretPassword1", db_kiran.password_hash)
        assert client.post("/api/v1/auth/login", json={"email": "kiran.picker@test.com", "password": "KiranSecretPassword1"}).status_code == 200

        # Duplicate email rejected (400)
        dup = client.post(
            "/api/v1/workers/",
            headers=auth_headers("manager"),
            json={"name": "Dup Kiran", "email": "kiran.picker@test.com", "password": "AnotherPassword1"},
        )
        assert dup.status_code == 400

        # 4. ADMIN creates a worker in WH2 (valid warehouse), rejected for SHOP location or missing location_id
        assert client.post(
            "/api/v1/workers/",
            headers=auth_headers("admin"),
            json={"name": "No WH Worker", "email": "nowh@test.com", "password": "AdminWorkerPass1"},
        ).status_code == 400
        assert client.post(
            "/api/v1/workers/",
            headers=auth_headers("admin"),
            json={"name": "Shop Worker", "email": "shopw@test.com", "password": "AdminWorkerPass1", "location_id": shop_id},
        ).status_code == 400

        admin_res = client.post(
            "/api/v1/workers/",
            headers=auth_headers("admin"),
            json={
                "name": "Arjun Loader",
                "email": "arjun.loader@test.com",
                "password": "ArjunSecurePassword2",
                "location_id": wh2.location_id,
            },
        )
        assert admin_res.status_code == 201
        assert admin_res.json()["role"] == "WAREHOUSE_WORKER"
        assert admin_res.json()["location_id"] == wh2.location_id

        # 5. Verify MongoDB WORKER_CREATED audit events were recorded without passwords
        mgr_audit = col.find_one({"event_type": "WORKER_CREATED", "entity_id": mgr_body["user_id"]})
        admin_audit = col.find_one({"event_type": "WORKER_CREATED", "entity_id": admin_res.json()["user_id"]})
        assert mgr_audit is not None
        assert mgr_audit["actor_role"] == "WAREHOUSE_MANAGER"
        assert mgr_audit["location_id"] == wh1_id
        assert "KiranSecretPassword1" not in str(mgr_audit)

        assert admin_audit is not None
        assert admin_audit["actor_role"] == "ADMIN"
        assert admin_audit["location_id"] == wh2.location_id
        assert "ArjunSecurePassword2" not in str(admin_audit)

    AuditLogService.close_client()
