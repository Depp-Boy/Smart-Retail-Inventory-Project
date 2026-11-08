import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.session import get_db
from app.models import (
    Base, Location, User, Product, Inventory, ShopWarehouse,
    Sale, SaleItem, Order, OrderItem, OrderAllocation, StockReservation,
    WorkerTask, WorkerTaskItem, Dispatch, DispatchItem, StockTransfer,
    Forecast, Alert
)
from app.core.security import hash_password, create_access_token

# Isolated in-memory SQLite engine for tests (zero impact on Supabase)
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all schema tables in memory before testing and drop on completion."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Provide a clean session for each test function and reset tables after."""
    session = TestingSessionLocal()
    yield session
    session.close()
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client(db_session):
    """TestClient that overrides get_db dependency with isolated test session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_locations(db_session):
    """Create sample shop and warehouse locations for testing."""
    wh = Location(
        location_name="Bengaluru Central DC",
        location_type="MAIN_WAREHOUSE",
        address="Plot 42, Electronic City, Bengaluru",
    )
    shop = Location(
        location_name="Koramangala Supermarket",
        location_type="SHOP",
        address="80 Feet Road, Koramangala, Bengaluru",
    )
    db_session.add_all([wh, shop])
    db_session.commit()
    db_session.refresh(wh)
    db_session.refresh(shop)

    # Link shop to warehouse as preferred
    link = ShopWarehouse(
        shop_id=shop.location_id,
        warehouse_id=wh.location_id,
        is_preferred=True,
        priority=1,
    )
    db_session.add(link)
    db_session.commit()

    return {"warehouse": wh, "shop": shop}


@pytest.fixture
def sample_users(db_session, sample_locations):
    """Create test users for role-based authorization testing."""
    admin = User(
        name="Admin User",
        email="admin@test.com",
        password_hash=hash_password("admin123"),
        role="ADMIN",
    )
    shop_owner = User(
        name="Shop Owner",
        email="shop@test.com",
        password_hash=hash_password("shop123"),
        role="SHOP_OWNER",
        location_id=sample_locations["shop"].location_id,
    )
    wh_manager = User(
        name="Warehouse Manager",
        email="manager@test.com",
        password_hash=hash_password("manager123"),
        role="WAREHOUSE_MANAGER",
        location_id=sample_locations["warehouse"].location_id,
    )
    worker = User(
        name="Warehouse Worker",
        email="worker@test.com",
        password_hash=hash_password("worker123"),
        role="WAREHOUSE_WORKER",
        location_id=sample_locations["warehouse"].location_id,
    )
    db_session.add_all([admin, shop_owner, wh_manager, worker])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(shop_owner)
    db_session.refresh(wh_manager)
    db_session.refresh(worker)

    return {"admin": admin, "shop_owner": shop_owner, "manager": wh_manager, "worker": worker}


@pytest.fixture
def auth_headers(sample_users):
    """Generate authorization headers for test users."""
    def _get_headers(role: str):
        user = sample_users[role]
        token = create_access_token(data={"sub": str(user.user_id), "email": user.email, "role": user.role})
        return {"Authorization": f"Bearer {token}"}

    return _get_headers


@pytest.fixture
def sample_product(db_session):
    """Create a sample product with inventory."""
    prod = Product(
        product_name="Fortune Sunlite Sunflower Oil 1L",
        category="Cooking Oil",
        unit="Pouch",
        price=Decimal("145.00"),
        reorder_threshold=Decimal("20.00"),
        sku="OIL-FS-1L",
        cost_price=Decimal("120.00"),
    )
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    return prod
