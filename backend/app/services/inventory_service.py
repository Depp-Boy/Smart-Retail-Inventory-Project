from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.product import Product
from app.models.user import User
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.inventory import InventorySummaryResponse
from app.services.audit_service import AuditLogService


class InventoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InventoryRepository(db)

    def _authorize_location_read(self, actor: Optional[User], location_id: int) -> None:
        if actor is None or actor.role == "ADMIN":
            return
        if actor.role in ("SHOP_OWNER", "WAREHOUSE_MANAGER", "WAREHOUSE_WORKER"):
            if actor.location_id is None or actor.location_id != location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: you can only view inventory for your own assigned location.",
                )
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to view location inventory.",
        )

    def _authorize_location_adjust(self, actor: Optional[User], location_id: int) -> None:
        if actor is None or actor.role == "ADMIN":
            return
        if actor.role == "WAREHOUSE_WORKER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workers cannot adjust stock directly.",
            )
        if actor.role in ("SHOP_OWNER", "WAREHOUSE_MANAGER"):
            if actor.location_id is None or actor.location_id != location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only adjust stock for your own assigned location.",
                )
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to adjust inventory.",
        )

    def list_inventory(
        self,
        actor: Optional[User] = None,
        location_id: Optional[int] = None,
        low_stock_only: bool = False,
        out_of_stock_only: bool = False,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Inventory]:
        effective_location_id = location_id
        if actor is not None and actor.role != "ADMIN":
            if actor.role in ("SHOP_OWNER", "WAREHOUSE_MANAGER", "WAREHOUSE_WORKER"):
                if actor.location_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User is not assigned to a location.",
                    )
                if location_id is not None and location_id != actor.location_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: you can only view inventory for your own assigned location.",
                    )
                effective_location_id = actor.location_id
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to inventory listing.",
                )

        return self.repo.list_all(
            location_id=effective_location_id,
            low_stock_only=low_stock_only,
            out_of_stock_only=out_of_stock_only,
            search=search,
            skip=skip,
            limit=limit,
        )

    def list_by_location(
        self,
        location_id: int,
        low_stock_only: bool = False,
        out_of_stock_only: bool = False,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        actor: Optional[User] = None,
    ) -> List[Inventory]:
        self._authorize_location_read(actor, location_id)
        return self.repo.list_by_location(
            location_id=location_id,
            low_stock_only=low_stock_only,
            out_of_stock_only=out_of_stock_only,
            search=search,
            skip=skip,
            limit=limit,
        )

    def get_summary(self, location_id: int, actor: Optional[User] = None) -> InventorySummaryResponse:
        self._authorize_location_read(actor, location_id)

        records = self.repo.list_by_location(location_id=location_id, skip=0, limit=None)
        total_items = len(records)
        total_phys = sum((Decimal(str(r.quantity)) for r in records), Decimal("0.00"))
        total_res = sum((Decimal(str(r.reserved_quantity)) for r in records), Decimal("0.00"))
        total_avail = float(total_phys - total_res)

        low_stock_count = 0
        out_of_stock_count = 0

        for r in records:
            avail = Decimal(str(r.quantity)) - Decimal(str(r.reserved_quantity))
            if avail <= Decimal("0.00"):
                out_of_stock_count += 1
            if r.product is not None and avail <= Decimal(str(r.product.reorder_threshold)):
                low_stock_count += 1

        return InventorySummaryResponse(
            location_id=location_id,
            total_products_count=total_items,
            total_physical_quantity=total_phys,
            total_reserved_quantity=total_res,
            total_available_quantity=total_avail,
            low_stock_count=low_stock_count,
            out_of_stock_count=out_of_stock_count,
        )

    def adjust_stock_controlled(
        self,
        location_id: int,
        product_id: int,
        delta: Decimal,
        actor: Optional[User] = None,
    ) -> Inventory:
        """
        Controlled transactional stock adjustment with row-level locking.
        Enforces authorization, validates delta and location/product existence,
        prevents negative physical/reserved stock or physical < reserved, and avoids
        duplicate (location_id, product_id) rows.
        """
        self._authorize_location_adjust(actor, location_id)

        if delta is None or not isinstance(delta, Decimal):
            try:
                delta = Decimal(str(delta))
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid adjustment delta.",
                ) from exc

        if not delta.is_finite():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adjustment delta must be a finite number.",
            )
        if delta == Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adjustment delta must be non-zero.",
            )

        try:
            location = self.db.query(Location).filter(Location.location_id == location_id).first()
            if not location:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Location {location_id} not found.",
                )

            product = self.db.query(Product).filter(Product.product_id == product_id).first()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {product_id} not found.",
                )

            inv = self.repo.get(location_id=location_id, product_id=product_id, lock=True)
            previous_qty = Decimal("0.00")
            if not inv:
                if delta < 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot deduct stock for non-existent inventory item.",
                    )
                inv = Inventory(
                    location_id=location_id,
                    product_id=product_id,
                    quantity=delta,
                    reserved_quantity=Decimal("0.00"),
                )
                self.db.add(inv)
            else:
                current_qty = Decimal(str(inv.quantity))
                previous_qty = current_qty
                current_res = Decimal(str(inv.reserved_quantity))
                if current_res < Decimal("0.00"):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Inconsistent inventory state: reserved quantity cannot be negative.",
                    )
                new_qty = current_qty + delta
                if new_qty < Decimal("0.00"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Physical quantity cannot become negative.",
                    )
                if new_qty < current_res:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Physical quantity ({new_qty}) cannot be less than "
                            f"reserved quantity ({current_res})."
                        ),
                    )
                inv.quantity = new_qty

            self.db.commit()
            self.db.refresh(inv)
            AuditLogService.log_event(
                event_type="INVENTORY_ADJUSTED",
                actor_id=actor.user_id if actor else None,
                actor_role=actor.role if actor else None,
                entity_type="INVENTORY",
                entity_id=inv.inventory_id,
                location_id=inv.location_id,
                details={
                    "product_id": inv.product_id,
                    "delta": str(delta),
                    "previous_quantity": str(previous_qty),
                    "new_quantity": str(inv.quantity),
                    "reserved_quantity": str(inv.reserved_quantity),
                },
            )
            return inv
        except IntegrityError:
            self.db.rollback()
            # Handle concurrent first-time insert race by re-locking existing record
            try:
                inv = self.repo.get(location_id=location_id, product_id=product_id, lock=True)
                if not inv:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Concurrent inventory modification conflict.",
                    )
                new_qty = Decimal(str(inv.quantity)) + delta
                current_res = Decimal(str(inv.reserved_quantity))
                if new_qty < Decimal("0.00") or new_qty < current_res:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Physical quantity cannot become negative or fall below reserved quantity.",
                    )
                inv.quantity = new_qty
                self.db.commit()
                self.db.refresh(inv)
                return inv
            except Exception:
                self.db.rollback()
                raise
        except Exception:
            self.db.rollback()
            raise
