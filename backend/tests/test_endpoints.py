from decimal import Decimal
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.models.inventory import Inventory


def test_root_endpoint(client: TestClient):
    """Test GET / returns 200 with application metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "app" in data
    assert "version" in data
    assert data["docs"] == "/docs"
    assert data["api_v1"] == "/api/v1"


def test_health_endpoint(client: TestClient):
    """Test GET /health returns 200 with healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data


def test_api_v1_health_endpoint(client: TestClient):
    """Test GET /api/v1/health returns 200 with v1 status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["api_version"] == "v1"


def test_database_health_live_connection(client: TestClient):
    """Test GET /health/db executes real SELECT 1 against Supabase."""
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["dialect"] == "postgresql"
    assert data["driver"] == "psycopg"
    assert "latency_ms" in data


def test_api_v1_database_health(client: TestClient):
    """Test GET /api/v1/health/db executes real SELECT 1 against Supabase."""
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True


def test_database_health_failure_handling(client: TestClient):
    """Test GET /health/db safely handles database connection errors with 503 status."""
    with patch(
        "app.main.check_database_connection",
        return_value={"connected": False, "error": "Simulated connection timeout", "latency_ms": 100.0},
    ):
        response = client.get("/health/db")
        assert response.status_code == 503
        data = response.json()
        assert data["connected"] is False
        assert "Simulated connection timeout" in data["error"]


def test_api_documentation_available(client: TestClient):
    """Test OpenAPI JSON specification and Swagger UI are accessible."""
    openapi_res = client.get("/openapi.json")
    assert openapi_res.status_code == 200
    openapi_data = openapi_res.json()
    assert "paths" in openapi_data
    assert "/health/db" in openapi_data["paths"]

    docs_res = client.get("/docs")
    assert docs_res.status_code == 200


def test_cors_headers(client: TestClient):
    """Test CORS preflight and headers allow the configured frontend origin."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/v1/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_modular_v1_domain_routers(client: TestClient):
    """Test that health and domain routers are registered and protected endpoints enforce 401."""
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200

    public_modules = [
        "auth", "locations", "products",
        "warehouses", "allocations"
    ]
    for mod in public_modules:
        response = client.get(f"/api/v1/{mod}/")
        assert response.status_code == 200, f"Module {mod} failed with status {response.status_code}"

    # Authenticated modules properly enforce 401 when accessed without credentials
    auth_protected_modules = [
        "inventory", "sales", "orders", "users", "reservations",
        "workers", "tasks", "dispatches", "stock-transfers",
        "forecasts", "alerts", "audit"
    ]
    for mod in auth_protected_modules:
        response = client.get(f"/api/v1/{mod}/")
        assert response.status_code == 401, f"Protected module {mod} should reject unauthenticated request with 401"


def test_inventory_listing_requires_authentication_and_scopes_authorized_users(
    client: TestClient, sample_locations, sample_product, db_session, auth_headers
):
    """Unauthenticated GET /api/v1/inventory/ must be rejected; authorized users see their own location."""
    shop_id = sample_locations["shop"].location_id
    wh_id = sample_locations["warehouse"].location_id

    db_session.add_all([
        Inventory(location_id=shop_id, product_id=sample_product.product_id, quantity=Decimal("20.00"), reserved_quantity=Decimal("0.00")),
        Inventory(location_id=wh_id, product_id=sample_product.product_id, quantity=Decimal("80.00"), reserved_quantity=Decimal("0.00")),
    ])
    db_session.commit()

    # Unauthenticated request rejected with 401
    unauth_res = client.get("/api/v1/inventory/")
    assert unauth_res.status_code == 401

    # Authorized shop owner sees only their shop's inventory
    shop_res = client.get("/api/v1/inventory/", headers=auth_headers("shop_owner"))
    assert shop_res.status_code == 200
    assert len(shop_res.json()) == 1
    assert shop_res.json()[0]["location_id"] == shop_id

    # Authorized warehouse manager sees only their warehouse's inventory
    mgr_res = client.get("/api/v1/inventory/", headers=auth_headers("manager"))
    assert mgr_res.status_code == 200
    assert len(mgr_res.json()) == 1
    assert mgr_res.json()[0]["location_id"] == wh_id

    # Admin sees all locations
    admin_res = client.get("/api/v1/inventory/", headers=auth_headers("admin"))
    assert admin_res.status_code == 200
    assert {r["location_id"] for r in admin_res.json()} == {shop_id, wh_id}
