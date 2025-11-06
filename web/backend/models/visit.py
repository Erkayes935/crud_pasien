from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base, HousekeepingMixin
import uuid

class Visit(Base, HousekeepingMixin):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    eksternal_id = Column(String(100), nullable=True)
    sumber = Column(String(100), nullable=True)
    tanggal_kunjungan = Column(Date, nullable=False)
    jenis_kunjungan = Column(String(100), nullable=True)
    poli = Column(String(100), nullable=True)
    doctor_name = Column(String(100), nullable=True)

    # relasi
    patient = relationship("Patient", back_populates="visits", foreign_keys=[patient_id])
    hospital = relationship("Hospital", back_populates="visits", foreign_keys=[hospital_id])
    doctor = relationship("User", back_populates="visits", foreign_keys=[doctor_id])
    claims = relationship("Claim", back_populates="visit", foreign_keys="Claim.visit_id")
    medical_records = relationship("MedicalRecord", back_populates="visit", foreign_keys="MedicalRecord.visit_id")

    def __repr__(self):
        return f"<Visit(id={self.id}, pasien={self.patient.nama}, tanggal={self.tanggal_kunjungan})>"
