from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.order import Order, OrderItem
from app.models.user import User
from app.repositories.location_repository import ShopWarehouseRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderCreateRequest
from app.services.audit_service import AuditLogService


class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.prod_repo = ProductRepository(db)
        self.sw_repo = ShopWarehouseRepository(db)

    def create_order(self, user: User, req: OrderCreateRequest) -> Order:
        shop_id = req.shop_id or user.location_id
        if not shop_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shop location ID must be specified.")
        if user.role == "SHOP_OWNER" and user.location_id != shop_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Shop owners can only create orders for their own shop.")

        # Identify preferred warehouse via shop_warehouse relationship
        preferred_wh = self.sw_repo.get_preferred_warehouse(shop_id)
        # Note on schema limitation: the orders table does not store warehouse_id directly;
        # the fulfillment relationship is routed via shop_warehouse and subsequent order_allocations.

        total_amount = Decimal("0.00")
        order_items_to_create = []

        for item in req.items:
            product = self.prod_repo.get_by_id(item.product_id)
            if not product:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {item.product_id} not found.")

            line_cost = item.quantity_requested * product.price
            total_amount += line_cost

            order_items_to_create.append(
                OrderItem(
                    product_id=item.product_id,
                    quantity_requested=item.quantity_requested,
                    quantity_allocated=Decimal("0.00"),
                )
            )

        order = Order(
            shop_id=shop_id,
            status="PENDING",
            total_amount=total_amount,
            expected_delivery=req.expected_delivery,
            items=order_items_to_create,
        )
        created = self.order_repo.create(order)
        AuditLogService.log_event(
            event_type="ORDER_CREATED",
            actor_id=user.user_id,
            actor_role=user.role,
            entity_type="ORDER",
            entity_id=created.order_id,
            location_id=created.shop_id,
            details={
                "total_amount": str(created.total_amount),
                "item_count": len(created.items),
                "status": created.status,
            },
        )
        return created

    def cancel_order(self, user: User, order_id: int) -> Order:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order {order_id} not found.")
        if user.role == "SHOP_OWNER" and user.location_id != order.shop_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot cancel orders belonging to another shop.")

        if order.status not in ("PENDING", "PROCESSING"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order in status '{order.status}' cannot be cancelled.",
            )

        previous_status = order.status
        order.status = "CANCELLED"
        updated = self.order_repo.update(order)
        AuditLogService.log_event(
            event_type="ORDER_CANCELLED",
            actor_id=user.user_id,
            actor_role=user.role,
            entity_type="ORDER",
            entity_id=updated.order_id,
            location_id=updated.shop_id,
            details={"previous_status": previous_status, "new_status": "CANCELLED"},
        )
        return updated

    def get_by_id(self, user: User, order_id: int) -> Order:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order {order_id} not found.")
        if user.role == "SHOP_OWNER" and user.location_id != order.shop_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to order.")
        return order

    def list(self, user: User, shop_id: Optional[int] = None, status: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[Order]:
        if user.role == "SHOP_OWNER":
            shop_id = user.location_id
        return self.order_repo.list(shop_id=shop_id, status=status, skip=skip, limit=limit)
