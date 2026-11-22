from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.sale import Sale, SaleItem
from app.models.user import User
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.sale_repository import SaleRepository
from app.schemas.sale import SaleCreateRequest


class SaleService:
    def __init__(self, db: Session):
        self.db = db
        self.sale_repo = SaleRepository(db)
        self.prod_repo = ProductRepository(db)
        self.inv_repo = InventoryRepository(db)

    def record_sale(self, user: User, req: SaleCreateRequest) -> Sale:
        # Determine shop ID and enforce authorization
        shop_id = req.shop_id or user.location_id
        if not shop_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shop location ID must be specified or associated with user.")
        if user.role == "SHOP_OWNER" and user.location_id != shop_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Shop owners can only record sales for their own shop.")

        subtotal = Decimal("0.00")
        sale_items_to_create = []

        # Lock inventory rows and validate stock availability in a single transaction
        for item in req.items:
            product = self.prod_repo.get_by_id(item.product_id)
            if not product:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {item.product_id} not found.")

            inv = self.inv_repo.get(location_id=shop_id, product_id=item.product_id, lock=True)
            avail_stock = Decimal("0.00")
            if inv:
                avail_stock = inv.quantity - inv.reserved_quantity

            if avail_stock < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient available stock for product '{product.product_name}'. Requested: {item.quantity}, Available: {avail_stock}.",
                )

            unit_price = item.unit_price if item.unit_price is not None else product.price
            line_subtotal = item.quantity * unit_price
            subtotal += line_subtotal

            # Deduct inventory atomically
            inv.quantity -= item.quantity
            self.db.add(inv)

            sale_items_to_create.append(
                SaleItem(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=unit_price,
                )
            )

        tax_amount = req.tax_amount or Decimal("0.00")
        discount_amount = req.discount_amount or Decimal("0.00")
        total_amount = subtotal + tax_amount - discount_amount
        if total_amount < 0:
            total_amount = Decimal("0.00")

        sale = Sale(
            shop_id=shop_id,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            status="COMPLETED",
            payment_method=req.payment_method.upper() if req.payment_method else "CASH",
            customer_name=req.customer_name.strip() if req.customer_name else None,
            customer_phone=req.customer_phone.strip() if req.customer_phone else None,
            items=sale_items_to_create,
        )
        return self.sale_repo.create(sale)

    def cancel_or_refund_sale(self, user: User, sale_id: int, action: str) -> Sale:
        sale = self.sale_repo.get_by_id(sale_id)
        if not sale:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sale {sale_id} not found.")

        if user.role == "SHOP_OWNER" and user.location_id != sale.shop_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify sales from another shop.")

        action = action.upper()
        if action not in ("CANCELLED", "REFUNDED"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be CANCELLED or REFUNDED.")

        # Idempotency check: never restore stock twice
        if sale.status in ("CANCELLED", "REFUNDED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sale {sale_id} is already marked as {sale.status}. Stock will not be restored again.",
            )

        # Restore physical inventory
        for item in sale.items:
            inv = self.inv_repo.get(location_id=sale.shop_id, product_id=item.product_id, lock=True)
            if inv:
                inv.quantity += item.quantity
                self.db.add(inv)
            else:
                inv = Inventory(
                    location_id=sale.shop_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    reserved_quantity=Decimal("0.00"),
                )
                self.db.add(inv)

        sale.status = action
        return self.sale_repo.update(sale)

    def get_by_id(self, user: User, sale_id: int) -> Sale:
        sale = self.sale_repo.get_by_id(sale_id)
        if not sale:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sale {sale_id} not found.")
        if user.role == "SHOP_OWNER" and user.location_id != sale.shop_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to sales from another shop.")
        return sale

    def list(self, user: User, shop_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> List[Sale]:
        if user.role == "SHOP_OWNER":
            shop_id = user.location_id
        return self.sale_repo.list(shop_id=shop_id, skip=skip, limit=limit)
