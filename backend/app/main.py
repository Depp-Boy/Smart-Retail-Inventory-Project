from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.database.connection import check_database_connection, get_engine
from app.services.audit_service import AuditLogService
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup: initialize PostgreSQL engine & optional MongoDB audit client
    get_engine()
    if get_settings().MONGODB_URL:
        AuditLogService.initialize()
    yield
    # Application shutdown: dispose PostgreSQL pool & close MongoDB client cleanly
    AuditLogService.close_client()
    engine = get_engine()
    engine.dispose()


def create_application() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="FastAPI Backend for Smart Retail Inventory Management and Demand Forecasting System",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root Level Endpoints
    @app.get("/", summary="Root API Information", tags=["General"])
    def root():
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
            "environment": settings.APP_ENV,
            "docs": "/docs",
            "api_v1": "/api/v1",
        }

    @app.get("/health", summary="Basic Application Health Check", tags=["Health"])
    def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "environment": settings.APP_ENV,
        }

    @app.get("/health/db", summary="Live Database Health Check (SELECT 1)", tags=["Health"])
    def database_health_check():
        db_status = check_database_connection()
        status_code = status.HTTP_200_OK if db_status.get("connected") else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(status_code=status_code, content=db_status)

    # Mount API Routers
    app.include_router(api_router, prefix="/api")

    return app


app = create_application()
