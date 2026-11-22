from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.user import User
from app.repositories.alert_repository import AlertRepository
from app.schemas.alert import AlertCreateRequest


class AlertService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AlertRepository(db)

    def create_alert(self, req: AlertCreateRequest) -> Alert:
        alert = Alert(
            location_id=req.location_id,
            product_id=req.product_id,
            alert_type=req.alert_type.upper(),
            message=req.message,
            status="UNREAD",
            user_id=req.user_id,
        )
        return self.repo.create(alert)

    def list_alerts_for_user(
        self,
        actor: User,
        status: Optional[str] = None,
        alert_type: Optional[str] = None,
    ) -> List[Alert]:
        return self.repo.list_for_user(
            user_id=actor.user_id,
            location_id=actor.location_id,
            status=status,
            alert_type=alert_type,
        )

    def mark_as_read(self, alert_id: int, actor: User) -> Alert:
        alert = self.repo.get_by_id(alert_id)
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
        if alert.user_id and alert.user_id != actor.user_id and actor.role != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to private alert.")

        alert.status = "READ"
        return self.repo.update(alert)

    def dismiss(self, alert_id: int, actor: User) -> Alert:
        alert = self.repo.get_by_id(alert_id)
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
        if alert.user_id and alert.user_id != actor.user_id and actor.role != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to private alert.")

        alert.status = "DISMISSED"
        return self.repo.update(alert)
