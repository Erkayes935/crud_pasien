from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, text
from ..base import Base

class ICD9Procedures(Base):
    __tablename__ = "icd9_procedures"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    description_id = Column(Text, nullable=True)
    is_pharmacologic = Column(Boolean, nullable=True)
    pharmacologic_confidentiality = Column(String, nullable=True)
    drug_category = Column(String, nullable=True)
    detection_method = Column(String, nullable=True)
    fornas_required = Column(Boolean, nullable=True)
    created_at = Column(DateTime, nullable=True, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=True, server_default=text("now()"), onupdate=text("now()"))
