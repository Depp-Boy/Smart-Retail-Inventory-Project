from datetime import date, datetime, time, timezone
from typing import Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.schemas.audit import AuditHealthResponse, AuditLogListResponse, AuditLogResponse
from app.services.audit_service import AuditLogService

router = APIRouter()


def _parse_date_bound(raw: Optional[str], end_of_day: bool = False) -> Optional[datetime]:
    if raw is None or not raw.strip():
        return None
    text = raw.strip()
    try:
        # Handle pure YYYY-MM-DD dates as well as full ISO datetimes
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            parsed_date = date.fromisoformat(text)
            bound_time = time(23, 59, 59, 999999) if end_of_day else time(0, 0, 0)
            return datetime.combine(parsed_date, bound_time, tzinfo=timezone.utc)
        parsed_dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed_dt.tzinfo is None:
            return parsed_dt.replace(tzinfo=timezone.utc)
        return parsed_dt.astimezone(timezone.utc)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ISO date/datetime filter '{raw}'.",
        ) from exc


@router.get("/health", response_model=AuditHealthResponse, summary="MongoDB Audit Store Health Check")
def audit_health(
    current_user: User = Depends(require_roles("ADMIN")),
):
    """Verify MongoDB audit store connectivity via ping without exposing connection URIs."""
    return AuditLogService.ping()


@router.get("/", response_model=AuditLogListResponse, summary="Query Audit Logs")
def list_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event_type"),
    actor_id: Optional[int] = Query(None, description="Filter by actor_id"),
    entity_type: Optional[str] = Query(None, description="Filter by entity_type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity_id"),
    location_id: Optional[int] = Query(None, description="Filter by location_id"),
    start_date: Optional[str] = Query(None, description="Inclusive start ISO date or datetime (UTC)"),
    end_date: Optional[str] = Query(None, description="Inclusive end ISO date or datetime (UTC)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    """
    Query MongoDB audit history with role-based scoping:
    - ADMIN: unrestricted access across all locations.
    - WAREHOUSE_MANAGER: scoped strictly to their assigned warehouse.
    - SHOP_OWNER: scoped strictly to their assigned shop.
    - WAREHOUSE_WORKER: forbidden.
    """
    if current_user.role == "WAREHOUSE_WORKER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Warehouse workers are not authorized to access audit history.",
        )

    effective_location_id = location_id
    if current_user.role in ("WAREHOUSE_MANAGER", "SHOP_OWNER"):
        if current_user.location_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not assigned to a location.",
            )
        if location_id is not None and location_id != current_user.location_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you can only query audit logs for your own assigned location.",
            )
        effective_location_id = current_user.location_id
    elif current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{current_user.role}' is not authorized to access audit logs.",
        )

    start_dt = _parse_date_bound(start_date, end_of_day=False)
    end_dt = _parse_date_bound(end_date, end_of_day=True)
    if start_dt is not None and end_dt is not None and start_dt > end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date.",
        )

    try:
        total, items = AuditLogService.query_events(
            event_type=event_type,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            location_id=effective_location_id,
            start_date=start_dt,
            end_date=end_dt,
            skip=skip,
            limit=limit,
        )
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit log store is currently unavailable.",
        )

    return AuditLogListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[AuditLogResponse(**it) for it in items],
    )
