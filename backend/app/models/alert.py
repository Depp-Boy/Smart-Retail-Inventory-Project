from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    location_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.product_id"), nullable=True)
    alert_type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(String(50), nullable=False, default="UNREAD")
    # Statuses: UNREAD, READ, DISMISSED
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=True)

    location = relationship("Location")
    product = relationship("Product")
    user = relationship("User")
