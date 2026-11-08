from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.alert import AlertCreateRequest, AlertResponse
from app.services.alert_service import AlertService

router = APIRouter()


@router.get("/", response_model=List[AlertResponse], summary="List Alerts for Current User")
def list_my_alerts(
    status_filter: Optional[str] = Query(None, alias="status"),
    alert_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AlertService(db)
    return service.list_alerts_for_user(actor=current_user, status=status_filter, alert_type=alert_type)


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED, summary="Create Alert")
def create_alert(
    req: AlertCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AlertService(db)
    return service.create_alert(req)


@router.patch("/{alert_id}/read", response_model=AlertResponse, summary="Mark Alert as Read")
def mark_alert_read(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AlertService(db)
    return service.mark_as_read(alert_id, actor=current_user)


@router.patch("/{alert_id}/dismiss", response_model=AlertResponse, summary="Dismiss Alert")
def dismiss_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AlertService(db)
    return service.dismiss(alert_id, actor=current_user)
