from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserProfileResponse,
    UserUpdateRequest,
    ChangePasswordRequest,
)
from app.schemas.location import (
    LocationCreate,
    LocationUpdate,
    LocationResponse,
    ShopWarehouseCreate,
    ShopWarehouseResponse,
)
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.schemas.inventory import InventoryResponse, InventorySummaryResponse
from app.schemas.sale import SaleItemCreate, SaleCreateRequest, SaleItemResponse, SaleResponse
from app.schemas.order import OrderItemCreate, OrderCreateRequest, OrderItemResponse, OrderResponse
from app.schemas.allocation import (
    AllocationCreateRequest,
    AllocationResponse,
    OrderAllocationSummaryResponse,
)
from app.schemas.reservation import ReservationCreateRequest, ReservationResponse
from app.schemas.worker_task import (
    WorkerTaskItemCreate,
    WorkerTaskItemResponse,
    WorkerTaskCreateRequest,
    WorkerTaskResponse,
    WorkerTaskProgressUpdate,
    WorkerTaskStatusUpdate,
)
from app.schemas.dispatch import (
    DispatchItemCreate,
    DispatchItemResponse,
    DispatchCreateRequest,
    DispatchStatusUpdate,
    DispatchResponse,
)
from app.schemas.stock_transfer import (
    StockTransferCreateRequest,
    StockTransferStatusUpdate,
    StockTransferResponse,
)
from app.schemas.forecast import (
    ForecastGenerateRequest,
    ForecastResponse,
    ReorderRecommendationResponse,
)
from app.schemas.alert import AlertCreateRequest, AlertStatusUpdate, AlertResponse

__all__ = [
    "MessageResponse",
    "PaginatedResponse",
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "UserProfileResponse",
    "UserUpdateRequest",
    "ChangePasswordRequest",
    "LocationCreate",
    "LocationUpdate",
    "LocationResponse",
    "ShopWarehouseCreate",
    "ShopWarehouseResponse",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "InventoryResponse",
    "InventorySummaryResponse",
    "SaleItemCreate",
    "SaleCreateRequest",
    "SaleItemResponse",
    "SaleResponse",
    "OrderItemCreate",
    "OrderCreateRequest",
    "OrderItemResponse",
    "OrderResponse",
    "AllocationCreateRequest",
    "AllocationResponse",
    "OrderAllocationSummaryResponse",
    "ReservationCreateRequest",
    "ReservationResponse",
    "WorkerTaskItemCreate",
    "WorkerTaskItemResponse",
    "WorkerTaskCreateRequest",
    "WorkerTaskResponse",
    "WorkerTaskProgressUpdate",
    "WorkerTaskStatusUpdate",
    "DispatchItemCreate",
    "DispatchItemResponse",
    "DispatchCreateRequest",
    "DispatchStatusUpdate",
    "DispatchResponse",
    "StockTransferCreateRequest",
    "StockTransferStatusUpdate",
    "StockTransferResponse",
    "ForecastGenerateRequest",
    "ForecastResponse",
    "ReorderRecommendationResponse",
    "AlertCreateRequest",
    "AlertStatusUpdate",
    "AlertResponse",
]
