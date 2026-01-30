from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Date
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from datetime import datetime
from ..base import Base, HousekeepingMixin
import uuid


# =========================================
# CLAIM UTAMA
# =========================================
class Claim(Base, HousekeepingMixin):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    claim_date = Column(DateTime, default=datetime.utcnow)

    # ==== RELASI UTAMA ====
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=True)

    patient = relationship("Patient", back_populates="claims")
    visit = relationship("Visit", back_populates="claims")
    hospital = relationship("Hospital", back_populates="claims")
    medical_record = relationship("MedicalRecord", back_populates="claim", uselist=False)

    # ==== STATUS & WORKFLOW ====
    status = Column(String, default="draft")
    workflow_status = Column(String, default="draft")
    is_final = Column(Boolean, server_default=text("false"))

    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    doctor_name = Column(String(100), nullable=True)
    doctor = relationship("User", back_populates="claims_as_doctor")

    doctor_submitted_by = Column(String)
    doctor_submitted_at = Column(DateTime)
    coder_verified_by = Column(String)
    coder_verified_at = Column(DateTime)
    finalized_by = Column(String)
    finalized_at = Column(DateTime)
    ai_medical_resume = Column(Text)

    # ==== RELASI ANAK ====
    diagnoses = relationship("ClaimDiagnosis", back_populates="claim", cascade="all, delete-orphan")
    procedures = relationship("ClaimProcedure", back_populates="claim", cascade="all, delete-orphan")
    tariffs = relationship("ClaimTariff", back_populates="claim", cascade="all, delete-orphan")
    ai_recommendations = relationship("ClaimAIRecommendation", back_populates="claim", cascade="all, delete-orphan")
    diagnosis_evaluations = relationship("ClaimDiagnosisEvaluation", back_populates="claim", cascade="all, delete-orphan")
    procedure_evaluations = relationship("ClaimProcedureEvaluation", back_populates="claim", cascade="all, delete-orphan")
    simulations = relationship("ClaimSimulation", back_populates="claim", cascade="all, delete-orphan")
    combination_alternatives = relationship("ClaimCombinationAlternative", back_populates="claim", cascade="all, delete-orphan")
    regulation_details = relationship("ClaimRegulationDetail", back_populates="claim", cascade="all, delete-orphan")

    logs = relationship("ClaimLog", back_populates="claim", cascade="all, delete-orphan")
    notes = relationship("ClaimNote", back_populates="claim", cascade="all, delete-orphan")
    visit_links = relationship("ClaimVisitLink", back_populates="claim", cascade="all, delete-orphan")

    group_id = Column(Integer, ForeignKey("claim_groups.id"), nullable=True)
    group = relationship("ClaimGroup", back_populates="claims")

    combo_evaluations = relationship("ClaimComboEvaluation", back_populates="claim", cascade="all, delete-orphan")

    # ==== Helper Property ====
    @property
    def external_visits(self):
        return [v.external_visit_id for v in self.visit_links]

    def to_export_dict(self):
        """Format ekspor sederhana ke Excel"""
        return {
            "ID Klaim": self.id,
            "Tanggal Klaim": self.claim_date.strftime("%Y-%m-%d") if self.claim_date else "-",
            "Nama Pasien": self.patient.nama if self.patient else "-",
            "No. RM": self.patient.no_rm if self.patient else "-",
            "Rumah Sakit": self.hospital.nama if self.hospital else "-",
            "Dokter": self.doctor_name or "-",
            "Status": self.status,
            "Workflow": self.workflow_status,
            "Final": "Ya" if self.is_final else "Tidak",
        }


# =========================================
# CLAIM LOG (AUDIT TRAIL)
# =========================================
class ClaimLog(Base, HousekeepingMixin):
    __tablename__ = "claim_logs"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    action = Column(String(50), nullable=False)   # created / updated / finalized / rejected / recalculated
    description = Column(Text)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    claim = relationship("Claim", back_populates="logs")
    user = relationship("User")

    def __repr__(self):
        return f"<ClaimLog(action={self.action}, claim_id={self.claim_id})>"


# =========================================
# CLAIM VISIT LINK (Hubungan eksternal)
# =========================================
class ClaimVisitLink(Base, HousekeepingMixin):
    __tablename__ = "claim_visit_links"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    external_visit_id = Column(String(100), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    is_primary = Column(Boolean, server_default=text("false"))
    note = Column(String(255), nullable=True)

    claim = relationship("Claim", back_populates="visit_links")
    hospital = relationship("Hospital")

    def __repr__(self):
        return f"<ClaimVisitLink(claim_id={self.claim_id}, external_visit_id={self.external_visit_id})>"


# =========================================
# CLAIM GROUP
# =========================================
class ClaimGroup(Base, HousekeepingMixin):
    __tablename__ = "claim_groups"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    kode_group = Column(String(50), nullable=False, unique=True)
    nama_group = Column(String(255), nullable=False)
    deskripsi = Column(Text)
    tanggal_mulai = Column(Date)
    tanggal_selesai = Column(Date)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    created_by = Column(String(100))

    claims = relationship("Claim", back_populates="group", cascade="all, delete-orphan")
    patient = relationship("Patient")
    hospital = relationship("Hospital")

    def __repr__(self):
        return f"<ClaimGroup(kode={self.kode_group}, nama={self.nama_group})>"


# =========================================
# CLAIM NOTE (Catatan Dokter / Verifikator)
# =========================================
class ClaimNote(Base, HousekeepingMixin):
    __tablename__ = "claim_notes"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    author = Column(String(100))
    role = Column(String(50))        # doctor / coder / verifikator / admin
    note = Column(Text, nullable=False)
    stage = Column(String(50))       # admission / daily / discharge
    visible_to = Column(String(100)) # optional: limit visibility

    claim = relationship("Claim", back_populates="notes")

    def __repr__(self):
        return f"<ClaimNote(author={self.author}, claim_id={self.claim_id})>"
