import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AuditLogService:
    """
    Secondary non-blocking audit logging service for MongoDB.
    Always executed post-commit. Failures never roll back PostgreSQL transactions.
    """

    @staticmethod
    def log_event(
        event_type: str,
        actor_id: Optional[int],
        entity_type: str,
        entity_id: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        settings = get_settings()
        mongodb_url = getattr(settings, "MONGODB_URL", None)

        record = {
            "event_type": event_type,
            "actor_id": actor_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        }

        # Sanitize sensitive fields
        for sensitive_key in ("password", "password_hash", "token", "secret", "access_token"):
            if sensitive_key in record["details"]:
                record["details"][sensitive_key] = "[REDACTED]"

        if not mongodb_url:
            logger.info("MongoDB audit log (local/console): %s", record)
            return True

        try:
            # Attempt non-blocking MongoDB insert if driver is present
            from pymongo import MongoClient

            client = MongoClient(mongodb_url, serverSelectionTimeoutMS=2000)
            db_name = getattr(settings, "MONGODB_DB_NAME", "smart_retail_audit")
            db = client[db_name]
            db.audit_logs.insert_one(record)
            client.close()
            return True
        except Exception as exc:
            logger.warning("MongoDB audit logging failed non-critically: %s", exc)
            return False
