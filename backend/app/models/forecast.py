from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class Forecast(Base):
    __tablename__ = "forecasts"

    forecast_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    shop_id = Column(BigInteger, ForeignKey("locations.location_id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.product_id"), nullable=False)
    forecasted_demand = Column(Numeric(12, 2), nullable=False)
    forecast_period = Column(Date, nullable=False)
    model_used = Column(String(100), nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    shop = relationship("Location")
    product = relationship("Product")
