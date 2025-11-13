from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Boolean, Text

Base = declarative_base()

class DataHubSource(Base):
    __tablename__ = "data_hub_sources"
    id = Column(Integer, primary_key=True)
    type = Column(String(20))  # manual, import_excel, gateway
    filename = Column(String(255), nullable=True)
    uploader = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    records = relationship("DataHubRecord", back_populates="source")

class DataHubRecord(Base):
    __tablename__ = "data_hub_records"
    id = Column(Integer, primary_key=True)
    record_id = Column(String(64), unique=True, index=True)
    hospital_id = Column(String(64), index=True)
    source_id = Column(Integer, ForeignKey("data_hub_sources.id"))
    json_data = Column(JSON, nullable=False)
    status = Column(String(50), default="ingested")
    
    # FASE 1.1: Duplicate Detection Fields
    content_hash = Column(String(64), index=True, nullable=True)  # MD5 hash untuk exact match
    similarity_fingerprint = Column(Text, nullable=True)  # Text fingerprint untuk fuzzy match
    
    created_at = Column(DateTime, server_default=func.now())

    source = relationship("DataHubSource", back_populates="records")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    record_id = Column(String(64), index=True)
    source = Column(String(50))
    level = Column(String(10))
    message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())



class DuplicateGroup(Base):
    __tablename__ = "duplicate_groups"
    id = Column(Integer, primary_key=True)
    master_record_id = Column(String(64), ForeignKey("data_hub_records.record_id"), index=True)
    duplicate_record_ids = Column(JSON)  # Array of duplicate record IDs
    similarity_score = Column(Float)  # 0-100 similarity percentage
    duplicate_type = Column(String(20))  # 'exact' atau 'fuzzy'
    status = Column(String(20), default="pending")  # pending, merged, ignored
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())



class PatientUUIDMap(Base):
    __tablename__ = "patient_uuid_map"
    id = Column(Integer, primary_key=True)
    patient_uuid = Column(String(36), unique=True, nullable=False, index=True)
    source_type = Column(String(20), nullable=False, index=True)  # "manual" or "excel"
    source_record_id = Column(String(64), nullable=True)
    name_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash (NOT plaintext!)
    nik_hash = Column(String(64), nullable=True, index=True)   # SHA256 hash (NOT plaintext!)
    created_at = Column(DateTime, server_default=func.now())
