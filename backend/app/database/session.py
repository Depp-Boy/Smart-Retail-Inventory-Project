from typing import Generator
from sqlalchemy.orm import Session, sessionmaker
from app.database.connection import get_engine

_SessionLocal: sessionmaker | None = None


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
            expire_on_commit=False,
        )
    return _SessionLocal


def SessionLocal() -> Session:
    """Create a new SQLAlchemy database session using the lazily initialized session factory."""
    return get_session_factory()()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a scoped database session.
    Automatically commits/rolls back and closes session on completion.
    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
