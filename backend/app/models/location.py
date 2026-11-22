from sqlalchemy import BigInteger, Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class Location(Base):
    __tablename__ = "locations"

    location_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    location_name = Column(String(255), nullable=False)
    location_type = Column(String(50), nullable=False)  # MAIN_WAREHOUSE, SUB_WAREHOUSE, SHOP
    address = Column(Text, nullable=False)
    parent_location_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=True)

    parent_location = relationship("Location", remote_side=[location_id], backref="sub_locations")
