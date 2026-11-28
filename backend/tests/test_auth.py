import pytest
from fastapi.testclient import TestClient


def test_successful_registration(client: TestClient):
    payload = {
        "name": "New Shop Owner",
        "email": "newshop@test.com",
        "password": "securepassword123",
        "role": "SHOP_OWNER",
        "phone": "+91 9876543210",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newshop@test.com"
    assert data["role"] == "SHOP_OWNER"
    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_email_registration_rejected(client: TestClient, sample_users):
    payload = {
        "name": "Duplicate User",
        "email": "shop@test.com",  # Already exists in sample_users
        "password": "anyPassword123",
        "role": "SHOP_OWNER",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 400
    assert "already registered" in res.json()["detail"]


def test_invalid_role_registration_rejected(client: TestClient):
    payload = {
        "name": "Invalid Role User",
        "email": "invalidrole@test.com",
        "password": "password123",
        "role": "SUPER_HERO",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 400
    assert "Invalid role" in res.json()["detail"]


def test_successful_login(client: TestClient, sample_users):
    payload = {"email": "shop@test.com", "password": "shop123"}
    res = client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "SHOP_OWNER"
    assert data["expires_in_minutes"] > 0


def test_incorrect_password_rejected(client: TestClient, sample_users):
    payload = {"email": "shop@test.com", "password": "wrongpassword"}
    res = client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


def test_nonexistent_user_login_rejected(client: TestClient):
    payload = {"email": "nobody@test.com", "password": "password123"}
    res = client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 401


def test_get_current_user_profile(client: TestClient, auth_headers):
    headers = auth_headers("shop_owner")
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "shop@test.com"
    assert data["role"] == "SHOP_OWNER"


def test_invalid_token_rejected(client: TestClient):
    headers = {"Authorization": "Bearer invalid.fake.token"}
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401


def test_unauthenticated_request_rejected(client: TestClient):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_change_password(client: TestClient, auth_headers):
    headers = auth_headers("shop_owner")
    # Change password
    res = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "shop123", "new_password": "newpassword123"},
    )
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Login with new password
    login_res = client.post("/api/v1/auth/login", json={"email": "shop@test.com", "password": "newpassword123"})
    assert login_res.status_code == 200


def test_change_password_with_incorrect_current_password(client: TestClient, auth_headers):
    headers = auth_headers("shop_owner")
    res = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "wrongpassword", "new_password": "newpassword123"},
    )
    assert res.status_code == 400
    assert "Current password is incorrect" in res.json()["detail"]


def test_role_authorization_enforcement(client: TestClient, auth_headers):
    # ADMIN is allowed to list users
    admin_headers = auth_headers("admin")
    admin_res = client.get("/api/v1/users/", headers=admin_headers)
    assert admin_res.status_code == 200

    # SHOP_OWNER is forbidden from listing all users
    shop_headers = auth_headers("shop_owner")
    shop_res = client.get("/api/v1/users/", headers=shop_headers)
    assert shop_res.status_code == 403
    assert "Access forbidden" in shop_res.json()["detail"]


def test_stateless_logout_endpoint(client: TestClient, auth_headers):
    headers = auth_headers("shop_owner")
    res = client.post("/api/v1/auth/logout", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "Logout successful" in data["message"]


@pytest.mark.parametrize("forbidden_role", ["ADMIN", "WAREHOUSE_MANAGER", "WAREHOUSE_WORKER"])
def test_public_registration_rejects_privileged_roles(client: TestClient, forbidden_role: str):
    payload = {
        "name": "Unauthorized Role Attempt",
        "email": f"{forbidden_role.lower()}@test.com",
        "password": "StrongPassword123",
        "role": forbidden_role,
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 403
    assert "SHOP_OWNER" in res.json()["detail"]


def test_public_shop_owner_registration_hashes_password_and_logs_audit(client: TestClient, db_session):
    from unittest.mock import patch
    import mongomock
    from app.core.config import Settings
    from app.core.security import verify_password
    from app.models.location import Location
    from app.models.user import User
    from app.services.audit_service import AuditLogService

    mock_client = mongomock.MongoClient(tz_aware=True)
    fake_settings = Settings(MONGODB_URL="mongodb://localhost:27017", MONGODB_DB_NAME="test_auth_audit")
    AuditLogService.close_client()

    with patch("app.services.audit_service.get_settings", return_value=fake_settings), patch.object(
        AuditLogService, "_create_mongo_client", return_value=mock_client
    ):
        res = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Priya Retail",
                "email": "priya@retail.com",
                "password": "ShopPassword123",
                "role": "SHOP_OWNER",
                "phone": "+91 90000 11111",
                "location_name": "Priya Supermart",
                "location_type": "MAIN_WAREHOUSE",  # Must be forced to SHOP
                "location_address": "12 MG Road, Bengaluru",
            },
        )
        assert res.status_code == 201
        body = res.json()
        assert body["role"] == "SHOP_OWNER"
        assert body["location_id"] is not None

        db_session.expire_all()
        user = db_session.query(User).filter_by(email="priya@retail.com").first()
        assert user is not None
        assert user.password_hash != "ShopPassword123"
        assert verify_password("ShopPassword123", user.password_hash)

        loc = db_session.query(Location).filter_by(location_id=user.location_id).first()
        assert loc is not None
        assert loc.location_type == "SHOP"

        audit_doc = mock_client["test_auth_audit"]["audit_logs"].find_one(
            {"event_type": "USER_REGISTERED", "entity_id": user.user_id}
        )
        assert audit_doc is not None
        assert "ShopPassword123" not in str(audit_doc)
    AuditLogService.close_client()


def test_seed_demo_endpoint_requires_admin(client: TestClient, auth_headers):
    # Unauthenticated must be rejected (401)
    assert client.post("/api/v1/auth/seed-demo").status_code == 401
    # Non-admin roles must be rejected (403)
    for role in ("shop_owner", "manager", "worker"):
        assert client.post("/api/v1/auth/seed-demo", headers=auth_headers(role)).status_code == 403


def test_create_admin_bootstrap_script_hashes_password_and_rejects_duplicate_email(db_session):
    from app.core.security import verify_password
    from app.models.user import User
    from scripts.create_admin import create_admin_user

    admin = create_admin_user(
        db_session,
        name="Initial System Admin",
        email="Bootstrap.Admin@Example.com",
        password="UltraSecureAdminPass99!",
    )
    assert admin.role == "ADMIN"
    assert admin.email == "bootstrap.admin@example.com"
    assert admin.password_hash != "UltraSecureAdminPass99!"
    assert verify_password("UltraSecureAdminPass99!", admin.password_hash)

    # Duplicate email (case-insensitive) must be rejected
    with pytest.raises(ValueError, match="already exists"):
        create_admin_user(
            db_session,
            name="Duplicate Admin",
            email="bootstrap.admin@example.com",
            password="AnotherSecurePassword88!",
        )

    assert db_session.query(User).filter_by(email="bootstrap.admin@example.com").count() == 1
