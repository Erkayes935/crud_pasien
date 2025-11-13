from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship
from ..base import Base

class DiagnosisDictionary(Base):
    __tablename__ = "diagnosis_dictionary"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), unique=True, nullable=False)
    icd10_id = Column(Integer, ForeignKey("icd10.id"))
    method = Column(String(50), default="manual")
    created_at = Column(DateTime, server_default=text("now()"))

    icd10 = relationship("ICD10")

class ProcedureDictionary(Base):
    __tablename__ = "procedure_dictionary"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), unique=True, nullable=False)
    icd9_id = Column(Integer, ForeignKey("icd9.id"))
    method = Column(String(50), default="manual")
    created_at = Column(DateTime, server_default=text("now()"))

    icd9 = relationship("ICD9")
