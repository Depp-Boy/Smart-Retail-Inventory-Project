from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class Dispatch(Base):
    __tablename__ = "dispatches"

    dispatch_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    dispatch_code = Column(String(100), unique=True, nullable=False, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.order_id"), nullable=False)
    source_location_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=False)
    created_by_user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    # Statuses: PENDING, PACKING, READY, IN_TRANSIT, DELIVERED, CANCELLED
    dispatch_date = Column(DateTime(timezone=True), nullable=True)
    tracking_reference = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    order = relationship("Order", backref="dispatches")
    source_location = relationship("Location")
    created_by = relationship("User")
    items = relationship("DispatchItem", back_populates="dispatch", cascade="all, delete-orphan")
    tasks = relationship("WorkerTask", back_populates="dispatch")


class DispatchItem(Base):
    __tablename__ = "dispatch_items"

    dispatch_item_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    dispatch_id = Column(BigInteger, ForeignKey("dispatches.dispatch_id"), nullable=False)
    allocation_id = Column(BigInteger, ForeignKey("order_allocations.allocation_id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)

    dispatch = relationship("Dispatch", back_populates="items")
    allocation = relationship("OrderAllocation", back_populates="dispatch_items")
    product = relationship("Product")
