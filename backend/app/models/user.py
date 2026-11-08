from sqlalchemy import BigInteger, Column, ForeignKey, String
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class User(Base):
    __tablename__ = "users"

    user_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # SHOP_OWNER, WAREHOUSE_MANAGER, WAREHOUSE_WORKER, ADMIN
    location_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=True)
    phone = Column(String(50), nullable=True)

    location = relationship("Location", backref="users")
