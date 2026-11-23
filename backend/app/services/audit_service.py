import logging
import re
import threading
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SENSITIVE_KEY_TOKENS = (
    "password",
    "passwd",
    "pwd",
    "token",
    "jwt",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "mongodb_url",
    "database_url",
    "connection_string",
    "dsn",
    "private_key",
    "service_role_key",
    "anon_key",
)

_URI_CREDENTIALS_PATTERN = re.compile(
    r"(mongodb(?:\+srv)?|postgres(?:ql)?|redis|amqp|https?)://[^/\s:@]+:[^/\s@]+@",
    re.IGNORECASE,
)

_ENTITY_TYPE_NORMALIZATION = {
    "sales": "SALE",
    "sale": "SALE",
    "orders": "ORDER",
    "order": "ORDER",
    "order_allocations": "ALLOCATION",
    "allocations": "ALLOCATION",
    "allocation": "ALLOCATION",
    "stock_reservations": "RESERVATION",
    "reservations": "RESERVATION",
    "reservation": "RESERVATION",
    "dispatches": "DISPATCH",
    "dispatch": "DISPATCH",
    "inventory": "INVENTORY",
    "worker_tasks": "WORKER_TASK",
    "worker_task": "WORKER_TASK",
    "task": "WORKER_TASK",
    "forecasts": "FORECAST",
    "forecast": "FORECAST",
    "users": "USER",
    "user": "USER",
    "stock_transfers": "STOCK_TRANSFER",
    "stock_transfer": "STOCK_TRANSFER",
}


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(tok in lowered for tok in _SENSITIVE_KEY_TOKENS)


def _scrub_string(val: str) -> str:
    return _URI_CREDENTIALS_PATTERN.sub(r"\1://[REDACTED]@", val)


def _sanitize_value(value: Any) -> Any:
    """
    Recursively sanitize nested dicts, lists, tuples, and convert non-BSON types
    (such as Decimal and date) into safe BSON-compatible representations.
    """
    if isinstance(value, dict):
        sanitized: Dict[str, Any] = {}
        for k, v in value.items():
            key_str = str(k)
            if _is_sensitive_key(key_str):
                sanitized[key_str] = "[REDACTED]"
            else:
                sanitized[key_str] = _sanitize_value(v)
        return sanitized
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return _scrub_string(value)
    return value


def _normalize_entity_type(entity_type: str) -> str:
    cleaned = entity_type.strip().lower()
    return _ENTITY_TYPE_NORMALIZATION.get(cleaned, entity_type.strip().upper())


def _safe_error_message(exc: Exception) -> str:
    return _scrub_string(f"{type(exc).__name__}: {exc}")


class AuditLogService:
    """
    Secondary non-blocking audit logging service backed by MongoDB.
    - PostgreSQL remains the primary source of truth.
    - Always called post-commit; MongoDB failures never roll back committed PostgreSQL writes.
    - Uses a single reusable PyMongo client with connection/selection timeouts and indexes.
    - Never logs or exposes MONGODB_URL or credentials.
    """

    _lock = threading.Lock()
    _client: Any = None
    _client_uri: Optional[str] = None
    _indexes_ready: bool = False

    @classmethod
    def _create_mongo_client(cls, mongodb_url: str, connect_timeout_ms: int, server_selection_timeout_ms: int) -> Any:
        from pymongo import MongoClient

        return MongoClient(
            mongodb_url,
            connectTimeoutMS=connect_timeout_ms,
            serverSelectionTimeoutMS=server_selection_timeout_ms,
            socketTimeoutMS=max(connect_timeout_ms, server_selection_timeout_ms),
            tz_aware=True,
        )

    @classmethod
    def get_client(cls) -> Optional[Any]:
        settings = get_settings()
        mongodb_url = (getattr(settings, "MONGODB_URL", None) or "").strip()
        if not mongodb_url:
            return None

        with cls._lock:
            if cls._client is not None and cls._client_uri == mongodb_url:
                return cls._client

            if cls._client is not None:
                try:
                    cls._client.close()
                except Exception:
                    pass
                cls._client = None
                cls._indexes_ready = False

            cls._client = cls._create_mongo_client(
                mongodb_url=mongodb_url,
                connect_timeout_ms=getattr(settings, "MONGODB_CONNECT_TIMEOUT_MS", 3000),
                server_selection_timeout_ms=getattr(settings, "MONGODB_SERVER_SELECTION_TIMEOUT_MS", 3000),
            )
            cls._client_uri = mongodb_url
            cls._indexes_ready = False
            return cls._client

    @classmethod
    def set_client_for_testing(cls, client: Any, uri: str = "mongomock://test") -> None:
        """Inject a mock/test MongoDB client cleanly for automated tests."""
        with cls._lock:
            cls._client = client
            cls._client_uri = uri
            cls._indexes_ready = False

    @classmethod
    def close_client(cls) -> None:
        """Close the shared MongoDB client cleanly during application shutdown or test teardown."""
        with cls._lock:
            if cls._client is not None:
                try:
                    cls._client.close()
                except Exception as exc:
                    logger.warning("Error closing MongoDB audit client: %s", _safe_error_message(exc))
            cls._client = None
            cls._client_uri = None
            cls._indexes_ready = False

    @classmethod
    def _get_collection(cls) -> Optional[Any]:
        client = cls.get_client()
        if client is None:
            return None
        settings = get_settings()
        db_name = getattr(settings, "MONGODB_DB_NAME", "smart_retail_audit") or "smart_retail_audit"
        col_name = getattr(settings, "MONGODB_COLLECTION_NAME", "audit_logs") or "audit_logs"
        collection = client[db_name][col_name]
        cls.ensure_indexes(collection)
        return collection

    @classmethod
    def ensure_indexes(cls, collection: Any) -> None:
        with cls._lock:
            if cls._indexes_ready:
                return
            try:
                from pymongo import ASCENDING, DESCENDING

                collection.create_index([("event_type", ASCENDING)], name="idx_audit_event_type")
                collection.create_index([("actor_id", ASCENDING)], name="idx_audit_actor_id")
                collection.create_index(
                    [("entity_type", ASCENDING), ("entity_id", ASCENDING)],
                    name="idx_audit_entity",
                )
                collection.create_index([("timestamp", DESCENDING)], name="idx_audit_timestamp")
                collection.create_index([("location_id", ASCENDING)], name="idx_audit_location_id")
                cls._indexes_ready = True
            except Exception as exc:
                logger.warning("MongoDB audit index creation warning: %s", _safe_error_message(exc))

    @classmethod
    def initialize(cls) -> Dict[str, Any]:
        """Initialize reusable client, verify connectivity with ping, and ensure indexes."""
        status_info = cls.ping()
        if status_info.get("connected"):
            try:
                cls._get_collection()
            except Exception as exc:
                logger.warning("MongoDB audit collection initialization warning: %s", _safe_error_message(exc))
        return status_info

    @classmethod
    def ping(cls) -> Dict[str, Any]:
        settings = get_settings()
        db_name = getattr(settings, "MONGODB_DB_NAME", "smart_retail_audit") or "smart_retail_audit"
        col_name = getattr(settings, "MONGODB_COLLECTION_NAME", "audit_logs") or "audit_logs"

        client = cls.get_client()
        if client is None:
            return {
                "configured": False,
                "connected": False,
                "database": db_name,
                "collection": col_name,
                "error": "MONGODB_URL is not configured.",
            }

        try:
            client.admin.command("ping")
            return {
                "configured": True,
                "connected": True,
                "database": db_name,
                "collection": col_name,
            }
        except Exception as exc:
            err = _safe_error_message(exc)
            logger.warning("MongoDB audit ping failed: %s", err)
            return {
                "configured": True,
                "connected": False,
                "database": db_name,
                "collection": col_name,
                "error": err,
            }

    @classmethod
    def build_document(
        cls,
        event_type: str,
        actor_id: Optional[int],
        entity_type: str,
        entity_id: Optional[int],
        details: Optional[Dict[str, Any]] = None,
        actor_role: Optional[str] = None,
        location_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        doc: Dict[str, Any] = {
            "event_type": event_type.strip().upper(),
            "actor_id": actor_id,
            "actor_role": actor_role.strip().upper() if actor_role else None,
            "entity_type": _normalize_entity_type(entity_type),
            "entity_id": entity_id,
            "location_id": location_id,
            "timestamp": datetime.now(timezone.utc),
            "details": _sanitize_value(details or {}),
        }
        if idempotency_key:
            doc["idempotency_key"] = str(idempotency_key)
        return doc

    @classmethod
    def log_event(
        cls,
        event_type: str,
        actor_id: Optional[int],
        entity_type: str,
        entity_id: Optional[int],
        details: Optional[Dict[str, Any]] = None,
        actor_role: Optional[str] = None,
        location_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> bool:
        """
        Persist a sanitized, structured audit event to MongoDB post-commit.

        Returns:
            True ONLY if persisted to MongoDB (or already persisted under the same idempotency_key).
            False if MongoDB is unconfigured or unavailable (never raises, never rolls back PostgreSQL).
        """
        document = cls.build_document(
            event_type=event_type,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            actor_role=actor_role,
            location_id=location_id,
            idempotency_key=idempotency_key,
        )

        try:
            collection = cls._get_collection()
        except Exception as exc:
            logger.warning(
                "MongoDB audit store unavailable; PostgreSQL transaction preserved. Event=%s Error=%s",
                document["event_type"],
                _safe_error_message(exc),
            )
            return False

        if collection is None:
            logger.info(
                "MongoDB audit logging skipped (MONGODB_URL not configured): event=%s entity=%s:%s actor=%s",
                document["event_type"],
                document["entity_type"],
                document["entity_id"],
                document["actor_id"],
            )
            return False

        try:
            if idempotency_key:
                existing = collection.find_one({"idempotency_key": str(idempotency_key)})
                if existing is not None:
                    return True
            collection.insert_one(document)
            return True
        except Exception as exc:
            logger.warning(
                "MongoDB audit insert failed non-critically (PostgreSQL commit preserved). Event=%s Error=%s",
                document["event_type"],
                _safe_error_message(exc),
            )
            return False

    @classmethod
    def query_events(
        cls,
        event_type: Optional[str] = None,
        actor_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        location_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Query MongoDB audit logs with filtering and pagination.
        Raises RuntimeError if MongoDB is unconfigured or unreachable.
        """
        collection = cls._get_collection()
        if collection is None:
            raise RuntimeError("MongoDB audit log store is not configured.")

        query: Dict[str, Any] = {}
        if event_type:
            query["event_type"] = event_type.strip().upper()
        if actor_id is not None:
            query["actor_id"] = actor_id
        if entity_type:
            query["entity_type"] = _normalize_entity_type(entity_type)
        if entity_id is not None:
            query["entity_id"] = entity_id
        if location_id is not None:
            query["location_id"] = location_id

        if start_date is not None or end_date is not None:
            ts_filter: Dict[str, Any] = {}
            if start_date is not None:
                ts_filter["$gte"] = (
                    start_date.replace(tzinfo=timezone.utc)
                    if start_date.tzinfo is None
                    else start_date.astimezone(timezone.utc)
                )
            if end_date is not None:
                ts_filter["$lte"] = (
                    end_date.replace(tzinfo=timezone.utc)
                    if end_date.tzinfo is None
                    else end_date.astimezone(timezone.utc)
                )
            query["timestamp"] = ts_filter

        try:
            from pymongo import DESCENDING

            total = collection.count_documents(query)
            cursor = (
                collection.find(query)
                .sort("timestamp", DESCENDING)
                .skip(skip)
                .limit(limit)
            )
            items: List[Dict[str, Any]] = []
            for doc in cursor:
                ts = doc.get("timestamp")
                if isinstance(ts, datetime) and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                items.append(
                    {
                        "audit_id": str(doc.get("_id")),
                        "event_type": doc.get("event_type"),
                        "actor_id": doc.get("actor_id"),
                        "actor_role": doc.get("actor_role"),
                        "entity_type": doc.get("entity_type"),
                        "entity_id": doc.get("entity_id"),
                        "location_id": doc.get("location_id"),
                        "timestamp": ts,
                        "details": _sanitize_value(doc.get("details") or {}),
                    }
                )
            return total, items
        except Exception as exc:
            raise RuntimeError(f"Failed to query MongoDB audit logs: {_safe_error_message(exc)}") from exc
