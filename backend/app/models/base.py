from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()
PK_TYPE = BigInteger().with_variant(Integer, "sqlite")
