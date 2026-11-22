from sqlalchemy import BigInteger, Column, Numeric, String, Text
from app.models.base import Base, PK_TYPE


class Product(Base):
    __tablename__ = "products"

    product_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    product_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    unit = Column(String(50), nullable=False)
    price = Column(Numeric(12, 2), nullable=False, default=0)
    reorder_threshold = Column(Numeric(12, 2), nullable=False, default=0)
    sku = Column(String(100), unique=True, nullable=True, index=True)
    cost_price = Column(Numeric(12, 2), nullable=True)
    description = Column(Text, nullable=True)
    storage_conditions = Column(Text, nullable=True)
