# StockSense — FastAPI Backend Foundation

FastAPI backend service for the **Smart Retail Inventory Management and Demand Forecasting System**, integrated with Supabase PostgreSQL via SQLAlchemy 2.x and Psycopg 3.

---

## 1. Architecture & Tech Stack

- **Framework:** FastAPI `0.115+`
- **ASGI Server:** Uvicorn `0.32+` (with standard extras: uvloop, httptools, watchfiles)
- **Database Engine:** SQLAlchemy `2.0+`
- **Database Driver:** Psycopg 3 (`psycopg[binary]>=3.2.0`)
- **Configuration & Validation:** Pydantic v2 & Pydantic Settings
- **Testing:** Pytest & FastAPI TestClient (HTTPX)
- **Database:** Supabase PostgreSQL (AWS EU-West-1 pooler with SSL)

---

## 2. Directory Layout

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory, CORS, root & health endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic Settings (env validation, driver normalization)
│   │   └── security.py             # Security & token stubs
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py           # SQLAlchemy 2 engine, pooling, SSL & live health check
│   │   └── session.py              # Session factory & get_db() FastAPI dependency
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py               # Top-level API router mounting /api/v1
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py           # V1 router aggregating all 15 modular domain routers
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── health.py       # GET /api/v1/health & GET /api/v1/health/db
│   │           ├── auth.py         # Authentication & token endpoints
│   │           ├── users.py        # User management
│   │           ├── locations.py    # Retail shops & fulfillment centers
│   │           ├── products.py     # Product catalog
│   │           ├── inventory.py    # Stock tracking
│   │           ├── sales.py        # POS transactions & line items
│   │           ├── orders.py       # Replenishment orders
│   │           ├── warehouses.py   # Warehouse operations
│   │           ├── allocations.py  # Stock allocations
│   │           ├── reservations.py # Stock reservations
│   │           ├── dispatches.py   # Outgoing dispatches & carriers
│   │           ├── workers.py      # Worker task management
│   │           ├── stock_transfers.py # Inter-facility stock transfers
│   │           ├── forecasts.py    # AI demand forecasting
│   │           └── alerts.py       # Stockout & threshold alerts
│   ├── models/                     # SQLAlchemy ORM models (reserved for subsequent prompt)
│   ├── schemas/                    # Pydantic schemas (reserved for subsequent prompt)
│   ├── services/                   # Business logic services
│   ├── repositories/               # Data access layer
│   └── utils/
│       ├── __init__.py
│       └── schema_inspector.py     # PostgreSQL information_schema batch inspection tool
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest TestClient fixture
│   └── test_endpoints.py           # Automated test suite (health, db, cors, docs, modules)
├── .env                            # Environment variables (excluded from Git)
├── .env.example                    # Environment template
├── requirements.txt                # Python package dependencies
├── SCHEMA_INSPECTION.md            # Generated Supabase schema report (18 tables, 126 cols)
└── README.md                       # This file
```

---

## 3. Environment Setup

### Prerequisites
- Python 3.11+ (verified with Python 3.13)
- Windows PowerShell or Bash terminal

### Create Virtual Environment
```powershell
cd backend
python -m venv .venv
```

### Activate Virtual Environment
- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 4. Configuration (`.env`)

Copy `.env.example` to `.env` and fill in your credentials:

```ini
DATABASE_URL="postgresql://postgres.<project-ref>:<password>@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
APP_ENV=development
SECRET_KEY=your_random_secret_key_at_least_32_characters
ACCESS_TOKEN_EXPIRE_MINUTES=30
FRONTEND_URL=http://localhost:5173
```

> **Driver Note:** The application automatically normalizes `postgresql://` and `postgres://` connection strings to `postgresql+psycopg://` so SQLAlchemy 2 uses the Psycopg 3 driver with SSL enabled.

---

## 5. Running the Application

### Development Server
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Server endpoints will be available at:
- **Root Info:** `http://127.0.0.1:8000/`
- **Application Health:** `http://127.0.0.1:8000/health`
- **Database Health (Live `SELECT 1`):** `http://127.0.0.1:8000/health/db`
- **API v1 Health:** `http://127.0.0.1:8000/api/v1/health`
- **Swagger Documentation:** `http://127.0.0.1:8000/docs`
- **ReDoc Documentation:** `http://127.0.0.1:8000/redoc`
- **OpenAPI Schema:** `http://127.0.0.1:8000/openapi.json`

---

## 6. Supabase Database Schema Inspection

The repository includes a batch inspection utility that queries PostgreSQL `information_schema` and `pg_catalog` across all 18 tables:

```powershell
python -m app.utils.schema_inspector
```

This outputs a comprehensive report saved to `SCHEMA_INSPECTION.md` listing:
- 18 discovered tables
- 126 columns with exact PostgreSQL data types, nullability, defaults, and primary keys
- 35 foreign key constraints
- Check constraints and indexes

---

## 7. Running Automated Tests

Run the full pytest suite:

```powershell
pytest -v
```

Tests verify:
1. Root endpoint (`/`) metadata and status.
2. Application health check (`/health`).
3. API v1 health check (`/api/v1/health`).
4. Live Supabase database health check (`/health/db` executing `SELECT 1`).
5. API v1 database health check (`/api/v1/health/db`).
6. Safe connection error handling (`503 Service Unavailable` on connection failure without crash).
7. OpenAPI documentation availability (`/openapi.json` and `/docs`).
8. CORS preflight headers allowing `http://localhost:5173`.
9. All 15 modular domain routers mounted under `/api/v1`.
