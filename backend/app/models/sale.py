from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class Sale(Base):
    __tablename__ = "sales"

    sale_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    shop_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=False)
    sale_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    customer_name = Column(String(255), nullable=True)
    customer_phone = Column(String(50), nullable=True)
    payment_method = Column(String(50), nullable=True)  # CASH, UPI, CARD, OTHER
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(50), nullable=False, default="COMPLETED")  # COMPLETED, CANCELLED, REFUNDED

    shop = relationship("Location", backref="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")


class SaleItem(Base):
    __tablename__ = "sale_items"

    sale_item_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    sale_id = Column(BigInteger, ForeignKey("sales.sale_id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")
