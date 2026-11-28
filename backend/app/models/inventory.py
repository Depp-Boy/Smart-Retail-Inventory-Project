from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("location_id", "product_id", name="uq_location_product"),
    )

    inventory_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    location_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False, default=0)
    reserved_quantity = Column(Numeric(12, 2), nullable=False, default=0)
    last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    location = relationship("Location", backref="inventory_records")
    product = relationship("Product", backref="inventory_records")

    @property
    def available_quantity(self) -> float:
        return float(self.quantity - self.reserved_quantity)
