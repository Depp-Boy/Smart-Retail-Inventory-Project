from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
import mongomock
import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.order import Order, OrderItem
from app.models.sale import Sale
from app.services.audit_service import AuditLogService


@pytest.fixture
def mock_mongo_audit():
    """Provide an isolated mongomock client wired into AuditLogService with clean teardown."""
    mock_client = mongomock.MongoClient(tz_aware=True)
    fake_settings = Settings(
        MONGODB_URL="mongodb://audituser:supersecret@localhost:27017",
        MONGODB_DB_NAME="test_smart_retail_audit",
        MONGODB_COLLECTION_NAME="audit_logs",
    )
    AuditLogService.close_client()
    with patch("app.services.audit_service.get_settings", return_value=fake_settings), patch.object(
        AuditLogService, "_create_mongo_client", return_value=mock_client
    ) as create_mock:
        yield {
            "client": mock_client,
            "collection": mock_client["test_smart_retail_audit"]["audit_logs"],
            "create_mock": create_mock,
            "settings": fake_settings,
        }
    AuditLogService.close_client()


def test_audit_service_unconfigured_mongodb_returns_false_without_raising():
    """When MONGODB_URL is not configured, log_event does not raise and does not falsely claim persistence."""
    AuditLogService.close_client()
    unconfigured = Settings(MONGODB_URL=None)
    with patch("app.services.audit_service.get_settings", return_value=unconfigured):
        persisted = AuditLogService.log_event(
            event_type="TEST_EVENT",
            actor_id=1,
            actor_role="ADMIN",
            entity_type="SALE",
            entity_id=999,
            details={"action": "test", "password": "supersecretpassword123"},
        )
        assert persisted is False
        ping_res = AuditLogService.ping()
        assert ping_res["configured"] is False
        assert ping_res["connected"] is False
    AuditLogService.close_client()


def test_mongodb_client_reuse_ping_and_indexes(mock_mongo_audit, client: TestClient, auth_headers):
    # Initialize & verify client is created once and reused
    c1 = AuditLogService.get_client()
    c2 = AuditLogService.get_client()
    assert c1 is c2
    assert mock_mongo_audit["create_mock"].call_count == 1

    # Ping succeeds and never leaks MONGODB_URL or credentials
    ping = AuditLogService.initialize()
    assert ping["configured"] is True
    assert ping["connected"] is True
    assert "supersecret" not in str(ping)
    assert "mongodb://" not in str(ping)

    # Required indexes are created
    idx_info = mock_mongo_audit["collection"].index_information()
    assert "idx_audit_event_type" in idx_info
    assert "idx_audit_actor_id" in idx_info
    assert "idx_audit_entity" in idx_info
    assert "idx_audit_timestamp" in idx_info
    assert "idx_audit_location_id" in idx_info

    # Health endpoint accessible to ADMIN only
    admin_h = client.get("/api/v1/audit/health", headers=auth_headers("admin"))
    assert admin_h.status_code == 200
    assert admin_h.json()["connected"] is True
    assert "supersecret" not in admin_h.text
    assert client.get("/api/v1/audit/health", headers=auth_headers("worker")).status_code == 403


def test_audit_document_structure_bson_datetime_and_nested_secret_sanitization(mock_mongo_audit):
    ok = AuditLogService.log_event(
        event_type="sale_created",
        actor_id=42,
        actor_role="shop_owner",
        entity_type="sales",
        entity_id=101,
        location_id=7,
        details={
            "total_amount": Decimal("729.50"),
            "password": "top-secret-password",
            "nested": {
                "access_token": "jwt.secret.token",
                "refresh_token": "refresh-val",
                "credentials_uri": "mongodb+srv://admin:mySecretPass@cluster0.mongodb.net/db",
                "items": [
                    {"sku": "OIL-1L", "api_key": "sk-12345"},
                    {"secret_key": "abc", "qty": Decimal("2.00")},
                ],
            },
        },
    )
    assert ok is True

    raw = mock_mongo_audit["collection"].find_one({"entity_id": 101})
    assert raw is not None
    assert raw["event_type"] == "SALE_CREATED"
    assert raw["actor_id"] == 42
    assert raw["actor_role"] == "SHOP_OWNER"
    assert raw["entity_type"] == "SALE"
    assert raw["location_id"] == 7
    assert isinstance(raw["timestamp"], datetime)
    assert raw["timestamp"].tzinfo is not None

    # Verify Decimal converted to exact string and nested secrets fully sanitized
    assert raw["details"]["total_amount"] == "729.50"
    assert raw["details"]["password"] == "[REDACTED]"
    assert raw["details"]["nested"]["access_token"] == "[REDACTED]"
    assert raw["details"]["nested"]["refresh_token"] == "[REDACTED]"
    assert "mySecretPass" not in raw["details"]["nested"]["credentials_uri"]
    assert "[REDACTED]" in raw["details"]["nested"]["credentials_uri"]
    assert raw["details"]["nested"]["items"][0]["api_key"] == "[REDACTED]"
    assert raw["details"]["nested"]["items"][1]["secret_key"] == "[REDACTED]"
    assert raw["details"]["nested"]["items"][1]["qty"] == "2.00"


def test_audit_query_filters_pagination_and_role_authorization(
    mock_mongo_audit, client: TestClient, sample_locations, sample_users, auth_headers
):
    shop_id = sample_locations["shop"].location_id
    wh_id = sample_locations["warehouse"].location_id
    col = mock_mongo_audit["collection"]

    now = datetime.now(timezone.utc)
    col.insert_many([
        {
            "event_type": "SALE_CREATED",
            "actor_id": sample_users["shop_owner"].user_id,
            "actor_role": "SHOP_OWNER",
            "entity_type": "SALE",
            "entity_id": 10,
            "location_id": shop_id,
            "timestamp": now - timedelta(hours=3),
            "details": {"total_amount": "150.00"},
        },
        {
            "event_type": "DISPATCH_CREATED",
            "actor_id": sample_users["manager"].user_id,
            "actor_role": "WAREHOUSE_MANAGER",
            "entity_type": "DISPATCH",
            "entity_id": 20,
            "location_id": wh_id,
            "timestamp": now - timedelta(hours=2),
            "details": {"order_id": 1},
        },
        {
            "event_type": "DISPATCH_DELIVERED",
            "actor_id": sample_users["manager"].user_id,
            "actor_role": "WAREHOUSE_MANAGER",
            "entity_type": "DISPATCH",
            "entity_id": 20,
            "location_id": wh_id,
            "timestamp": now - timedelta(hours=1),
            "details": {"order_id": 1},
        },
    ])

    admin_h = auth_headers("admin")
    mgr_h = auth_headers("manager")
    shop_h = auth_headers("shop_owner")
    worker_h = auth_headers("worker")

    # Unauthenticated -> 401
    assert client.get("/api/v1/audit/").status_code == 401

    # Worker -> 403
    assert client.get("/api/v1/audit/", headers=worker_h).status_code == 403

    # Admin sees all 3 with pagination
    all_res = client.get("/api/v1/audit/?skip=0&limit=2", headers=admin_h)
    assert all_res.status_code == 200
    assert all_res.json()["total"] == 3
    assert len(all_res.json()["items"]) == 2

    page2 = client.get("/api/v1/audit/?skip=2&limit=2", headers=admin_h)
    assert page2.status_code == 200
    assert len(page2.json()["items"]) == 1

    # Filters: event_type, entity_type + entity_id, actor_id, date range
    by_event = client.get("/api/v1/audit/?event_type=DISPATCH_DELIVERED", headers=admin_h)
    assert by_event.status_code == 200
    assert by_event.json()["total"] == 1
    assert by_event.json()["items"][0]["entity_id"] == 20

    by_entity = client.get("/api/v1/audit/?entity_type=DISPATCH&entity_id=20", headers=admin_h)
    assert by_entity.status_code == 200
    assert by_entity.json()["total"] == 2

    start_iso = (now - timedelta(hours=2, minutes=30)).isoformat()
    end_iso = (now - timedelta(minutes=30)).isoformat()
    by_date = client.get("/api/v1/audit/", params={"start_date": start_iso, "end_date": end_iso}, headers=admin_h)
    assert by_date.status_code == 200
    assert by_date.json()["total"] == 2

    # Invalid date range -> 400
    assert client.get("/api/v1/audit/", params={"start_date": end_iso, "end_date": start_iso}, headers=admin_h).status_code == 400

    # Warehouse manager sees ONLY their warehouse's logs and cannot query shop's location_id
    mgr_res = client.get("/api/v1/audit/", headers=mgr_h)
    assert mgr_res.status_code == 200
    assert mgr_res.json()["total"] == 2
    assert all(item["location_id"] == wh_id for item in mgr_res.json()["items"])
    assert client.get(f"/api/v1/audit/?location_id={shop_id}", headers=mgr_h).status_code == 403

    # Shop owner sees ONLY their shop's logs and cannot query warehouse's location_id
    shop_res = client.get("/api/v1/audit/", headers=shop_h)
    assert shop_res.status_code == 200
    assert shop_res.json()["total"] == 1
    assert shop_res.json()["items"][0]["location_id"] == shop_id
    assert client.get(f"/api/v1/audit/?location_id={wh_id}", headers=shop_h).status_code == 403


def test_postgresql_transaction_succeeds_even_if_mongodb_unavailable(
    client: TestClient, sample_locations, sample_product, db_session, auth_headers
):
    shop_id = sample_locations["shop"].location_id
    db_session.add(Inventory(location_id=shop_id, product_id=sample_product.product_id, quantity=Decimal("30.00"), reserved_quantity=Decimal("0.00")))
    db_session.commit()

    broken_collection = MagicMock()
    broken_collection.insert_one.side_effect = RuntimeError("MongoDB connection timed out")

    AuditLogService.close_client()
    with patch.object(AuditLogService, "_get_collection", return_value=broken_collection):
        # Direct audit call reports False (never falsely claims persistence)
        assert AuditLogService.log_event("TEST_FAIL", 1, "SALE", 1) is False

        # Business sale STILL succeeds and commits to PostgreSQL!
        res = client.post(
            "/api/v1/sales/",
            headers=auth_headers("shop_owner"),
            json={"items": [{"product_id": sample_product.product_id, "quantity": "5.00"}]},
        )
        assert res.status_code == 201

    db_session.expire_all()
    assert db_session.query(Sale).count() == 1
    inv = db_session.query(Inventory).filter_by(location_id=shop_id, product_id=sample_product.product_id).first()
    assert float(inv.quantity) == 25.00

    # Query API returns 503 when MongoDB is unavailable
    unconfigured = Settings(MONGODB_URL=None)
    with patch("app.services.audit_service.get_settings", return_value=unconfigured):
        assert client.get("/api/v1/audit/", headers=auth_headers("admin")).status_code == 503


def test_no_success_audit_on_postgres_failure_and_duplicate_prevention(
    mock_mongo_audit, client: TestClient, sample_locations, sample_product, sample_users, db_session, auth_headers
):
    shop_id = sample_locations["shop"].location_id
    wh_id = sample_locations["warehouse"].location_id
    col = mock_mongo_audit["collection"]

    db_session.add(Inventory(location_id=shop_id, product_id=sample_product.product_id, quantity=Decimal("2.00"), reserved_quantity=Decimal("0.00")))
    db_session.add(Inventory(location_id=wh_id, product_id=sample_product.product_id, quantity=Decimal("50.00"), reserved_quantity=Decimal("0.00")))
    db_session.commit()

    # 1. Failed sale (insufficient stock) -> ZERO SALE_CREATED audit events!
    fail_sale = client.post(
        "/api/v1/sales/",
        headers=auth_headers("shop_owner"),
        json={"items": [{"product_id": sample_product.product_id, "quantity": "20.00"}]},
    )
    assert fail_sale.status_code == 400
    assert col.count_documents({"event_type": "SALE_CREATED"}) == 0

    # 2. Failed login logs AUTH_LOGIN_FAILED without storing credentials
    fail_login = client.post(
        "/api/v1/auth/login",
        json={"email": sample_users["shop_owner"].email, "password": "wrong-password-123"},
    )
    assert fail_login.status_code == 401
    failed_doc = col.find_one({"event_type": "AUTH_LOGIN_FAILED"})
    assert failed_doc is not None
    assert "wrong-password-123" not in str(failed_doc)

    # 3. Successful login logs AUTH_LOGIN_SUCCESS without storing JWT/password
    ok_login = client.post(
        "/api/v1/auth/login",
        json={"email": sample_users["shop_owner"].email, "password": "shop123"},
    )
    assert ok_login.status_code == 200
    ok_doc = col.find_one({"event_type": "AUTH_LOGIN_SUCCESS"})
    assert ok_doc is not None
    assert ok_doc["actor_role"] == "SHOP_OWNER"
    assert "shop123" not in str(ok_doc)

    # 4. Idempotency-key deduplication in AuditLogService
    assert AuditLogService.log_event("CUSTOM_EVENT", 1, "ORDER", 55, idempotency_key="order-55-v1") is True
    assert AuditLogService.log_event("CUSTOM_EVENT", 1, "ORDER", 55, idempotency_key="order-55-v1") is True
    assert col.count_documents({"event_type": "CUSTOM_EVENT", "entity_id": 55}) == 1

    # 5. Repeated identical forecast generation does NOT create duplicate FORECAST_GENERATED events
    f1 = client.post(
        "/api/v1/forecasts/generate",
        headers=auth_headers("shop_owner"),
        json={"shop_id": shop_id, "product_id": sample_product.product_id, "forecast_period": "2026-04-01", "model_preference": "SMA"},
    )
    f2 = client.post(
        "/api/v1/forecasts/generate",
        headers=auth_headers("shop_owner"),
        json={"shop_id": shop_id, "product_id": sample_product.product_id, "forecast_period": "2026-04-01", "model_preference": "SMA"},
    )
    assert f1.status_code == 201 and f2.status_code == 201
    assert col.count_documents({"event_type": "FORECAST_GENERATED"}) == 1

    # 6. Repeated cancel_allocation on already cancelled allocation does NOT emit duplicate ALLOCATION_CANCELLED
    order_res = client.post(
        "/api/v1/orders/",
        headers=auth_headers("shop_owner"),
        json={"shop_id": shop_id, "items": [{"product_id": sample_product.product_id, "quantity_requested": "10.00"}]},
    )
    assert order_res.status_code == 201
    assert col.count_documents({"event_type": "ORDER_CREATED"}) == 1
    order_item_id = order_res.json()["items"][0]["order_item_id"]

    alloc_res = client.post(
        "/api/v1/allocations/",
        headers=auth_headers("manager"),
        json={"order_item_id": order_item_id, "source_location_id": wh_id, "allocated_quantity": "10.00"},
    )
    alloc_id = alloc_res.json()["allocation_id"]
    assert client.post(f"/api/v1/allocations/{alloc_id}/cancel", headers=auth_headers("manager")).status_code == 200
    assert client.post(f"/api/v1/allocations/{alloc_id}/cancel", headers=auth_headers("manager")).status_code == 200
    assert col.count_documents({"event_type": "ALLOCATION_CANCELLED", "entity_id": alloc_id}) == 1
