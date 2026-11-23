from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.product import Product
from app.models.sale import Sale, SaleItem
from app.models.user import User
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.sale_repository import SaleRepository
from app.schemas.sale import SaleCreateRequest
from app.services.audit_service import AuditLogService

TWO_PLACES = Decimal("0.01")
VALID_PAYMENT_METHODS: Set[str] = {"CASH", "UPI", "CARD", "OTHER"}
VALID_SALE_STATUSES: Set[str] = {"COMPLETED", "CANCELLED", "REFUNDED"}
ALLOWED_SALE_TRANSITIONS: Dict[str, Set[str]] = {
    "COMPLETED": {"CANCELLED", "REFUNDED"},
    "CANCELLED": set(),
    "REFUNDED": set(),
}


def _to_decimal(value: object, field_name: str) -> Decimal:
    try:
        dec = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decimal value for {field_name}.",
        ) from exc
    if not dec.is_finite():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a finite decimal.",
        )
    return dec


class SaleService:
    def __init__(self, db: Session):
        self.db = db
        self.sale_repo = SaleRepository(db)
        self.prod_repo = ProductRepository(db)
        self.inv_repo = InventoryRepository(db)

    def _require_sales_role(self, user: User) -> None:
        if user.role not in ("SHOP_OWNER", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not authorized to access or manage sales.",
            )

    def record_sale(self, user: User, req: SaleCreateRequest) -> Sale:
        self._require_sales_role(user)

        # Determine shop ID and enforce strict shop isolation
        if user.role == "SHOP_OWNER":
            if user.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Shop owner is not assigned to a shop location.",
                )
            if req.shop_id is not None and req.shop_id != user.location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Shop owners can only record sales for their own shop.",
                )
            shop_id = user.location_id
        else:
            shop_id = req.shop_id or user.location_id
            if not shop_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Shop location ID must be specified or associated with user.",
                )

        if not req.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sale must contain at least one item.",
            )

        payment_method = (req.payment_method or "CASH").strip().upper()
        if payment_method not in VALID_PAYMENT_METHODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payment method '{payment_method}'. Allowed: {', '.join(sorted(VALID_PAYMENT_METHODS))}.",
            )

        tax_amount = _to_decimal(req.tax_amount, "tax_amount") if req.tax_amount is not None else Decimal("0.00")
        discount_amount = _to_decimal(req.discount_amount, "discount_amount") if req.discount_amount is not None else Decimal("0.00")
        if tax_amount < Decimal("0.00"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tax amount cannot be negative.")
        if discount_amount < Decimal("0.00"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount amount cannot be negative.")
        tax_amount = tax_amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        discount_amount = discount_amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        for item in req.items:
            qty = _to_decimal(item.quantity, "quantity")
            if qty <= Decimal("0.00"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sale item quantity must be greater than zero.")
            if item.unit_price is not None:
                up = _to_decimal(item.unit_price, "unit_price")
                if up < Decimal("0.00"):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit price cannot be negative.")

        try:
            # Verify shop exists and is actually a SHOP (never allow sales against warehouse inventory)
            shop_loc = self.db.query(Location).filter(Location.location_id == shop_id).first()
            if not shop_loc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shop location {shop_id} not found.")
            if shop_loc.location_type != "SHOP":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Location {shop_id} is not a SHOP; retail sales can only be recorded for shop locations.",
                )

            # Validate every product exists
            product_ids = sorted({item.product_id for item in req.items})
            products = self.db.query(Product).filter(Product.product_id.in_(product_ids)).all()
            products_by_id = {p.product_id: p for p in products}
            for item in req.items:
                if item.product_id not in products_by_id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Product {item.product_id} not found.",
                    )

            # Lock inventory rows in deterministic order (location_id, product_id ASC)
            locked_inventories = (
                self.db.query(Inventory)
                .filter(
                    Inventory.location_id == shop_id,
                    Inventory.product_id.in_(product_ids),
                )
                .order_by(Inventory.location_id.asc(), Inventory.product_id.asc())
                .with_for_update()
                .all()
            )
            inv_by_product = {inv.product_id: inv for inv in locked_inventories}

            # Validate stock availability (cumulatively per product) and pricing before any mutation
            cumulative_qty: Dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
            subtotal = Decimal("0.00")
            sale_items_to_create: List[SaleItem] = []

            for item in req.items:
                product = products_by_id[item.product_id]
                qty = _to_decimal(item.quantity, "quantity")
                cumulative_qty[item.product_id] += qty

                inv = inv_by_product.get(item.product_id)
                if not inv:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Insufficient available stock: product '{product.product_name}' "
                            f"has no inventory record at shop {shop_id}."
                        ),
                    )

                phys_qty = Decimal(str(inv.quantity))
                res_qty = Decimal(str(inv.reserved_quantity))
                if res_qty < Decimal("0.00") or phys_qty < res_qty:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Inconsistent inventory state for product '{product.product_name}'.",
                    )

                avail_stock = phys_qty - res_qty
                if avail_stock < cumulative_qty[item.product_id]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Insufficient available stock for product '{product.product_name}'. "
                            f"Requested: {cumulative_qty[item.product_id]}, Available: {avail_stock}."
                        ),
                    )

                catalog_price = Decimal(str(product.price)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                if item.unit_price is not None:
                    supplied_price = _to_decimal(item.unit_price, "unit_price").quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                    if supplied_price != catalog_price and user.role != "ADMIN":
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=(
                                f"Unauthorized unit price override for product '{product.product_name}'. "
                                f"Expected {catalog_price}, got {supplied_price}."
                            ),
                        )
                    unit_price = supplied_price
                else:
                    unit_price = catalog_price

                line_subtotal = (qty * unit_price).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                subtotal += line_subtotal

                sale_items_to_create.append(
                    SaleItem(
                        product_id=item.product_id,
                        quantity=qty,
                        unit_price=unit_price,
                    )
                )

            subtotal = subtotal.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            total_amount = (subtotal + tax_amount - discount_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if total_amount < Decimal("0.00"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Discount amount cannot exceed subtotal plus tax; total amount cannot be negative.",
                )

            # Deduct physical inventory exactly once per product; never alter reserved_quantity
            for pid in sorted(cumulative_qty.keys()):
                inv = inv_by_product[pid]
                qty_to_deduct = cumulative_qty[pid]
                new_qty = Decimal(str(inv.quantity)) - qty_to_deduct
                res_qty = Decimal(str(inv.reserved_quantity))
                if new_qty < Decimal("0.00") or new_qty < res_qty:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Sale deduction would violate inventory non-negative/reservation constraints.",
                    )
                inv.quantity = new_qty

            sale = Sale(
                shop_id=shop_id,
                subtotal=subtotal,
                tax_amount=tax_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                status="COMPLETED",
                payment_method=payment_method,
                customer_name=req.customer_name.strip() if req.customer_name else None,
                customer_phone=req.customer_phone.strip() if req.customer_phone else None,
                items=sale_items_to_create,
            )
            self.db.add(sale)
            self.db.commit()
            self.db.refresh(sale)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type="SALE_CREATED",
            actor_id=user.user_id,
            actor_role=user.role,
            entity_type="SALE",
            entity_id=sale.sale_id,
            location_id=shop_id,
            details={
                "subtotal": str(sale.subtotal),
                "tax_amount": str(sale.tax_amount),
                "discount_amount": str(sale.discount_amount),
                "total_amount": str(sale.total_amount),
                "item_count": len(sale.items),
                "payment_method": sale.payment_method,
                "status": sale.status,
            },
        )

        return sale

    def cancel_or_refund_sale(self, user: User, sale_id: int, action: str) -> Sale:
        self._require_sales_role(user)

        target_status = action.strip().upper()
        if target_status not in ("CANCELLED", "REFUNDED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action must be CANCELLED or REFUNDED.",
            )

        try:
            # Lock Sale row first to guarantee idempotent single-execution restoration
            sale = self.sale_repo.get_by_id(sale_id, lock=True)
            if not sale:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sale {sale_id} not found.")

            if user.role == "SHOP_OWNER":
                if user.location_id is None or user.location_id != sale.shop_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot modify sales from another shop.",
                    )

            # Enforce valid sale status transitions (only COMPLETED -> CANCELLED/REFUNDED)
            if sale.status in ("CANCELLED", "REFUNDED"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sale {sale_id} is already marked as {sale.status}. Stock will not be restored again.",
                )
            if target_status not in ALLOWED_SALE_TRANSITIONS.get(sale.status, set()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid sale status transition from {sale.status} to {target_status}.",
                )

            # Aggregate quantities per product and lock Inventory rows in deterministic order
            qty_by_product: Dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
            for item in sale.items:
                qty_by_product[item.product_id] += Decimal(str(item.quantity))

            product_ids = sorted(qty_by_product.keys())
            if product_ids:
                locked_inventories = (
                    self.db.query(Inventory)
                    .filter(
                        Inventory.location_id == sale.shop_id,
                        Inventory.product_id.in_(product_ids),
                    )
                    .order_by(Inventory.location_id.asc(), Inventory.product_id.asc())
                    .with_for_update()
                    .all()
                )
                inv_by_product = {inv.product_id: inv for inv in locked_inventories}

                # Restore ONLY physical quantity exactly once; never modify reserved_quantity
                for pid in product_ids:
                    restore_qty = qty_by_product[pid]
                    inv = inv_by_product.get(pid)
                    if inv:
                        phys_qty = Decimal(str(inv.quantity))
                        res_qty = Decimal(str(inv.reserved_quantity))
                        if phys_qty < Decimal("0.00") or res_qty < Decimal("0.00"):
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail="Cannot restore stock: existing inventory record is inconsistent.",
                            )
                        new_qty = phys_qty + restore_qty
                        if new_qty < res_qty:
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail="Inconsistent inventory state: physical quantity remains below reserved quantity.",
                            )
                        inv.quantity = new_qty
                    else:
                        new_inv = Inventory(
                            location_id=sale.shop_id,
                            product_id=pid,
                            quantity=restore_qty,
                            reserved_quantity=Decimal("0.00"),
                        )
                        self.db.add(new_inv)
                        inv_by_product[pid] = new_inv

            sale.status = target_status
            self.db.commit()
            self.db.refresh(sale)
        except Exception:
            self.db.rollback()
            raise

        AuditLogService.log_event(
            event_type=f"SALE_{target_status}",
            actor_id=user.user_id,
            actor_role=user.role,
            entity_type="SALE",
            entity_id=sale.sale_id,
            location_id=sale.shop_id,
            details={
                "previous_status": "COMPLETED",
                "new_status": target_status,
                "item_count": len(sale.items),
            },
        )

        return sale

    def get_by_id(self, user: User, sale_id: int) -> Sale:
        self._require_sales_role(user)
        sale = self.sale_repo.get_by_id(sale_id)
        if not sale:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sale {sale_id} not found.")
        if user.role == "SHOP_OWNER" and (user.location_id is None or user.location_id != sale.shop_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to sales from another shop.",
            )
        return sale

    def list(self, user: User, shop_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> List[Sale]:
        self._require_sales_role(user)
        if user.role == "SHOP_OWNER":
            if user.location_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Shop owner is not assigned to a shop location.",
                )
            if shop_id is not None and shop_id != user.location_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Shop owners can only list sales for their own shop.",
                )
            shop_id = user.location_id
        return self.sale_repo.list(shop_id=shop_id, skip=skip, limit=limit)
