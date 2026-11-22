import time
from typing import Any, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """
    Get or initialize the SQLAlchemy 2.x engine with Psycopg 3 dialect.
    Configured for Supabase pooler stability.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args: Dict[str, Any] = {}
        
        # Enforce SSL for remote PostgreSQL/Supabase instances
        if "localhost" not in settings.DATABASE_URL and "127.0.0.1" not in settings.DATABASE_URL:
            connect_args["sslmode"] = "require"

        _engine = create_engine(
            settings.sqlalchemy_database_uri,
            connect_args=connect_args,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=settings.DEBUG,
            future=True,
        )
    return _engine


def check_database_connection() -> Dict[str, Any]:
    """
    Execute a real SELECT 1 query against the database to verify connectivity.
    Safe failure handling without crashing the application.
    """
    start_time = time.perf_counter()
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if result == 1:
                return {
                    "connected": True,
                    "dialect": engine.dialect.name,
                    "driver": engine.dialect.driver,
                    "latency_ms": latency_ms,
                    "message": "Database connection verified successfully via SELECT 1",
                }
            return {
                "connected": False,
                "error": f"Unexpected result from SELECT 1: {result}",
                "latency_ms": latency_ms,
            }
    except SQLAlchemyError as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "connected": False,
            "error": str(exc.__cause__ or exc),
            "latency_ms": latency_ms,
            "message": "Failed to connect to PostgreSQL database",
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "connected": False,
            "error": str(exc),
            "latency_ms": latency_ms,
            "message": "Unexpected error during database health check",
        }
