from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class StockTransfer(Base):
    __tablename__ = "stock_transfers"

    transfer_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    source_location_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=False)
    destination_location_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)
    transfer_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(String(50), nullable=False, default="PENDING")
    # Statuses: PENDING, IN_TRANSIT, COMPLETED, CANCELLED

    source_location = relationship("Location", foreign_keys=[source_location_id])
    destination_location = relationship("Location", foreign_keys=[destination_location_id])
    product = relationship("Product")
