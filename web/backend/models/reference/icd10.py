from sqlalchemy import Column, Integer, String, Text, DateTime, text
from ..base import Base

class ICD10(Base):
    __tablename__ = "icd10"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(Text, nullable=False)
    category = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=True, default="ICD-10 2024")

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))
