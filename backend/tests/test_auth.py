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
