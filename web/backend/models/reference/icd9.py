from sqlalchemy import Column, Integer, String, Text, DateTime, text
from ..base import Base

class ICD9(Base):
    __tablename__ = "icd9"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(Text, nullable=False)
    category = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=True, default="ICD-9-CM 2024")

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))
