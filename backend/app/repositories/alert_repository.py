from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.alert import Alert


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, alert_id: int) -> Optional[Alert]:
        return self.db.query(Alert).filter(Alert.alert_id == alert_id).first()

    def list_for_user(
        self,
        user_id: int,
        location_id: Optional[int] = None,
        status: Optional[str] = None,
        alert_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Alert]:
        query = self.db.query(Alert).filter((Alert.user_id == user_id) | (Alert.user_id.is_(None)))
        if location_id:
            query = query.filter(Alert.location_id == location_id)
        if status:
            query = query.filter(Alert.status == status.upper())
        if alert_type:
            query = query.filter(Alert.alert_type == alert_type.upper())
        return query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()

    def list_by_location(
        self,
        location_id: int,
        status: Optional[str] = None,
        alert_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Alert]:
        query = self.db.query(Alert).filter(Alert.location_id == location_id)
        if status:
            query = query.filter(Alert.status == status.upper())
        if alert_type:
            query = query.filter(Alert.alert_type == alert_type.upper())
        return query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()

    def create(self, alert: Alert) -> Alert:
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def update(self, alert: Alert) -> Alert:
        self.db.commit()
        self.db.refresh(alert)
        return alert
