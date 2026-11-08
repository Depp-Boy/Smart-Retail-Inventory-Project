from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.database.connection import check_database_connection
from app.database.session import get_db

router = APIRouter()


@router.get("/health", summary="V1 API Health Check")
def v1_health():
    settings = get_settings()
    return {
        "status": "healthy",
        "api_version": "v1",
        "app_env": settings.APP_ENV,
    }


@router.get("/health/db", summary="V1 Database Health Check")
def v1_health_db():
    db_status = check_database_connection()
    status_code = status.HTTP_200_OK if db_status.get("connected") else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=db_status)
