from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class ShopWarehouse(Base):
    __tablename__ = "shop_warehouse"

    relationship_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    shop_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=False)
    warehouse_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=False)
    is_preferred = Column(Boolean, nullable=False, default=False)
    priority = Column(Integer, nullable=False, default=1)

    shop = relationship("Location", foreign_keys=[shop_id], backref="warehouse_links")
    warehouse = relationship("Location", foreign_keys=[warehouse_id], backref="shop_links")
