from sqlalchemy import BigInteger, Column, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class OrderAllocation(Base):
    __tablename__ = "order_allocations"

    allocation_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    order_item_id = Column(BigInteger, ForeignKey("order_items.order_item_id"), nullable=False)
    source_location_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=False)
    allocated_quantity = Column(Numeric(12, 2), nullable=False)
    status = Column(String(50), nullable=False, default="ALLOCATED")
    # Statuses: ALLOCATED, RESERVED, DISPATCHED, DELIVERED, CANCELLED

    order_item = relationship("OrderItem", backref="allocations")
    source_location = relationship("Location")
    reservations = relationship("StockReservation", back_populates="allocation", cascade="all, delete-orphan")
    dispatch_items = relationship("DispatchItem", back_populates="allocation")
    tasks = relationship("WorkerTask", back_populates="allocation")
