from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    audit_id: str
    event_type: str
    actor_id: Optional[int] = None
    actor_role: Optional[str] = None
    entity_type: str
    entity_id: Optional[int] = None
    location_id: Optional[int] = None
    timestamp: datetime
    details: Dict[str, Any] = {}


class AuditLogListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[AuditLogResponse] = []


class AuditHealthResponse(BaseModel):
    configured: bool
    connected: bool
    database: str
    collection: str
    error: Optional[str] = None
