from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.inventory import Inventory
from app.models.stock_transfer import StockTransfer
from app.models.user import User
from app.repositories.stock_transfer_repository import StockTransferRepository
from app.schemas.stock_transfer import StockTransferCreateRequest, StockTransferStatusUpdate
from app.services.audit_service import AuditLogService


class StockTransferService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StockTransferRepository(db)

    def create_transfer(self, req: StockTransferCreateRequest, actor: User) -> StockTransfer:
        if req.source_location_id == req.destination_location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and destination locations must be different.",
            )

        # Check source inventory has sufficient stock
        source_inv = (
            self.db.query(Inventory)
            .filter_by(location_id=req.source_location_id, product_id=req.product_id)
            .first()
        )
        if not source_inv or (source_inv.quantity - source_inv.reserved_quantity) < req.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient available stock at source location.",
            )

        transfer = StockTransfer(
            source_location_id=req.source_location_id,
            destination_location_id=req.destination_location_id,
            product_id=req.product_id,
            quantity=req.quantity,
            status="PENDING",
        )
        self.db.add(transfer)
        self.db.commit()
        self.db.refresh(transfer)

        AuditLogService.log_event(
            event_type="STOCK_TRANSFER_CREATED",
            actor_id=actor.user_id,
            entity_type="stock_transfers",
            entity_id=transfer.transfer_id,
            details={"quantity": float(req.quantity)},
        )

        return transfer

    def update_status(self, transfer_id: int, req: StockTransferStatusUpdate, actor: User) -> StockTransfer:
        transfer = self.repo.get_by_id(transfer_id, lock=True)
        if not transfer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found.")

        target = req.status.upper()

        if target == "IN_TRANSIT":
            if transfer.status != "PENDING":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Transfer cannot be set to IN_TRANSIT from {transfer.status}.",
                )
            # Deduct source stock exactly once
            source_inv = (
                self.db.query(Inventory)
                .filter_by(location_id=transfer.source_location_id, product_id=transfer.product_id)
                .with_for_update()
                .first()
            )
            if not source_inv or (source_inv.quantity - source_inv.reserved_quantity) < transfer.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient stock at source warehouse to commence transit.",
                )
            source_inv.quantity -= transfer.quantity
            transfer.status = "IN_TRANSIT"

        elif target == "COMPLETED":
            if transfer.status != "IN_TRANSIT":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Only IN_TRANSIT transfers can be COMPLETED. Current: {transfer.status}.",
                )
            # Credit destination stock exactly once
            dest_inv = (
                self.db.query(Inventory)
                .filter_by(location_id=transfer.destination_location_id, product_id=transfer.product_id)
                .with_for_update()
                .first()
            )
            if not dest_inv:
                dest_inv = Inventory(
                    location_id=transfer.destination_location_id,
                    product_id=transfer.product_id,
                    quantity=transfer.quantity,
                    reserved_quantity=Decimal("0.00"),
                )
                self.db.add(dest_inv)
            else:
                dest_inv.quantity += transfer.quantity

            transfer.status = "COMPLETED"

        elif target == "CANCELLED":
            # Rule 2: Strictly reject cancellation of IN_TRANSIT with 409 Conflict
            if transfer.status == "IN_TRANSIT":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Goods have already left the source facility. In-transit transfers cannot be cancelled through ordinary cancellation.",
                )
            if transfer.status != "PENDING":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel transfer in {transfer.status} state.",
                )
            transfer.status = "CANCELLED"

        self.db.commit()
        self.db.refresh(transfer)

        AuditLogService.log_event(
            event_type="STOCK_TRANSFER_UPDATED",
            actor_id=actor.user_id,
            entity_type="stock_transfers",
            entity_id=transfer.transfer_id,
            details={"new_status": transfer.status},
        )

        return transfer

    def list(
        self,
        source_id: Optional[int] = None,
        destination_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[StockTransfer]:
        return self.repo.list(
            source_location_id=source_id,
            destination_location_id=destination_id,
            status=status,
        )
