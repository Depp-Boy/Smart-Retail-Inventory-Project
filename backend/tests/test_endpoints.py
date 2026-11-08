from unittest.mock import patch
from fastapi.testclient import TestClient


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
    """Test that all 16 domain routers are registered and responsive under /api/v1."""
    public_modules = [
        "auth", "locations", "products", "inventory",
        "warehouses", "allocations"
    ]
    for mod in public_modules:
        response = client.get(f"/api/v1/{mod}/")
        assert response.status_code == 200, f"Module {mod} failed with status {response.status_code}"

    # Authenticated modules properly enforce 401 when accessed without credentials
    auth_protected_modules = [
        "sales", "orders", "users", "reservations",
        "workers", "tasks", "dispatches", "stock-transfers",
        "forecasts", "alerts"
    ]
    for mod in auth_protected_modules:
        response = client.get(f"/api/v1/{mod}/")
        assert response.status_code == 401, f"Protected module {mod} should reject unauthenticated request with 401"

