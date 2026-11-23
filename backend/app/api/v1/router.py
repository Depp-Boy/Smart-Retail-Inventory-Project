from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    users,
    locations,
    products,
    inventory,
    sales,
    orders,
    warehouses,
    allocations,
    reservations,
    dispatches,
    workers,
    tasks,
    stock_transfers,
    forecasts,
    alerts,
    audit,
)

v1_router = APIRouter()

# Health endpoints
v1_router.include_router(health.router, tags=["Health"])

# Modular business routers
v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
v1_router.include_router(users.router, prefix="/users", tags=["Users"])
v1_router.include_router(locations.router, prefix="/locations", tags=["Locations"])
v1_router.include_router(products.router, prefix="/products", tags=["Products"])
v1_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
v1_router.include_router(sales.router, prefix="/sales", tags=["Sales"])
v1_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
v1_router.include_router(warehouses.router, prefix="/warehouses", tags=["Warehouses"])
v1_router.include_router(allocations.router, prefix="/allocations", tags=["Allocations"])
v1_router.include_router(reservations.router, prefix="/reservations", tags=["Stock Reservations"])
v1_router.include_router(dispatches.router, prefix="/dispatches", tags=["Dispatches"])
v1_router.include_router(workers.router, prefix="/workers", tags=["Workers"])
v1_router.include_router(tasks.router, prefix="/tasks", tags=["Worker Tasks"])
v1_router.include_router(tasks.router, prefix="/workers/tasks", tags=["Worker Tasks Alias"])
v1_router.include_router(stock_transfers.router, prefix="/stock-transfers", tags=["Stock Transfers"])
v1_router.include_router(forecasts.router, prefix="/forecasts", tags=["Forecasts"])
v1_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
v1_router.include_router(audit.router, prefix="/audit", tags=["Audit Logs"])
