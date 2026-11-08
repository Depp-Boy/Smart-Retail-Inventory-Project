from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class StockReservation(Base):
    __tablename__ = "stock_reservations"

    reservation_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    allocation_id = Column(BigInteger, ForeignKey("order_allocations.allocation_id"), nullable=False)
    quantity_reserved = Column(Numeric(12, 2), nullable=False)
    reserved_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="ACTIVE")
    # Statuses: ACTIVE, CONFIRMED, RELEASED, EXPIRED

    allocation = relationship("OrderAllocation", back_populates="reservations")
