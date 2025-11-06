from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base, HousekeepingMixin
import uuid

class Patient(Base, HousekeepingMixin):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)

    no_rm = Column(String(20), unique=True, nullable=True)
    no_ktp = Column(String(20), unique=True, nullable=True)
    no_bpjs = Column(String(20), unique=True, nullable=True)
    nama = Column(String(100), nullable=False)
    tanggal_lahir = Column(Date)
    alamat = Column(Text)
    email = Column(String(120), unique=True, nullable=True)
    no_hp = Column(String(20), nullable=True)
    jenis_kelamin = Column(String(10), nullable=True)
    eksternal_id = Column(String(100), unique=True, nullable=True)
    source = Column(String(100), nullable=True)

    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    hospital = relationship("Hospital", back_populates="patients", foreign_keys=[hospital_id])

    visits = relationship("Visit", back_populates="patient", foreign_keys="Visit.patient_id")
    claims = relationship("Claim", back_populates="patient", foreign_keys="Claim.patient_id")
    medical_records = relationship("MedicalRecord", back_populates="patient", foreign_keys="MedicalRecord.patient_id")

    def __repr__(self):
        return f"<Patient(id={self.id}, nama={self.nama}, no_rm={self.no_rm})>"
