from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.stock_transfer import StockTransfer


class StockTransferRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, transfer_id: int, lock: bool = False) -> Optional[StockTransfer]:
        query = self.db.query(StockTransfer).filter(StockTransfer.transfer_id == transfer_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def list(
        self,
        source_location_id: Optional[int] = None,
        destination_location_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[StockTransfer]:
        query = self.db.query(StockTransfer)
        if source_location_id:
            query = query.filter(StockTransfer.source_location_id == source_location_id)
        if destination_location_id:
            query = query.filter(StockTransfer.destination_location_id == destination_location_id)
        if status:
            query = query.filter(StockTransfer.status == status.upper())
        return query.order_by(StockTransfer.transfer_date.desc()).offset(skip).limit(limit).all()

    def create(self, transfer: StockTransfer) -> StockTransfer:
        self.db.add(transfer)
        self.db.commit()
        self.db.refresh(transfer)
        return transfer

    def update(self, transfer: StockTransfer) -> StockTransfer:
        self.db.commit()
        self.db.refresh(transfer)
        return transfer
