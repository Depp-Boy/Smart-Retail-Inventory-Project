from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    shop_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=False)
    order_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(String(50), nullable=False, default="PENDING")
    # Statuses: PENDING, PROCESSING, PARTIALLY_FULFILLED, FULFILLED, REJECTED, CANCELLED
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    expected_delivery = Column(DateTime(timezone=True), nullable=True)

    shop = relationship("Location", backref="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, ForeignKey("orders.order_id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.product_id"), nullable=False)
    quantity_requested = Column(Numeric(12, 2), nullable=False)
    quantity_allocated = Column(Numeric(12, 2), nullable=False, default=0)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
