"""
Module: backend.models

Defines the SQLAlchemy ORM models used by the application:
- Patient: stores patient personal information only.
- Claim: stores visit/claim information linked to a patient.
- User: stores application users linked to Auth0 via `auth0_sub` and a role.
- Hospital: stores hospital information, as root entity for grouping users & patients.
- Visit: stores visit information linked to a patient.
"""

from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime, Boolean, Enum, JSON, Float, text, Numeric, inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime, date
import uuid
from sqlalchemy.sql import func

# =========================================
# Hospital
# =========================================

class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    kode_hospital = Column(String(20), unique=True, nullable=True)
    nama = Column(String(150), nullable=False)
    tipe_hospital = Column(String(50), nullable=True)
    jenis_hospital = Column(String(50), nullable=True)
    alamat = Column(Text)
    telepon = Column(String(20), nullable=True)
    email = Column(String(120), unique=True, nullable=True)
    status_akreditasi = Column(String(50), nullable=True)
    status_bridging = Column(String(50), nullable=True)
    jumlah_tempat_tidur = Column(Integer, nullable=True)

    # admin_rs user
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # relasi
    admin = relationship("User", back_populates="admin_of_hospital", foreign_keys=[admin_id], post_update=True)
    patients = relationship("Patient", back_populates="hospital", foreign_keys="Patient.hospital_id")
    visits = relationship("Visit", back_populates="hospital", foreign_keys="Visit.hospital_id")
    claims = relationship("Claim", back_populates="hospital", foreign_keys="Claim.hospital_id")
    users = relationship("User", back_populates="hospital", foreign_keys="User.hospital_id")
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data

# =========================================
# Patient
# =========================================

class Patient(Base):
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

    # relasi ke hospital
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    hospital = relationship("Hospital", back_populates="patients", foreign_keys=[hospital_id])
    # Relasi: 1 pasien → banyak kunjungan
    visits = relationship("Visit", back_populates="patient", foreign_keys="Visit.patient_id")
    # Relasi: 1 pasien → banyak klaim
    claims = relationship("Claim", back_populates="patient", foreign_keys="Claim.patient_id")
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))
    def __repr__(self):
        return f"<Patient(id={self.id}, nama={self.nama}, no_rm={self.no_rm})>"
    # relasi ke medical records
    medical_records = relationship("MedicalRecord", back_populates="patient", foreign_keys="MedicalRecord.patient_id")
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data

# =========================================
# Visit
# =========================================

class Visit(Base):
    __tablename__ = "visits"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    eksternal_id = Column(String(100), nullable=True)
    sumber = Column(String(100), nullable=True)
    tanggal_kunjungan = Column(Date, nullable=False)
    jenis_kunjungan = Column(String(100), nullable=True)
    poli = Column(String(100), nullable=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    doctor_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    # Relasi ke pasien
    patient = relationship("Patient", back_populates="visits", foreign_keys=[patient_id])
    # Relasi ke rumah sakit
    hospital = relationship("Hospital", back_populates="visits", foreign_keys=[hospital_id])
    # Relasi ke klaim
    claims = relationship("Claim", back_populates="visit", foreign_keys="Claim.visit_id")
    # Relasi ke medical records
    medical_records = relationship("MedicalRecord", back_populates="visit", foreign_keys="MedicalRecord.visit_id")
    # Relasi ke dokter
    doctor = relationship("User", back_populates="visits", foreign_keys=[doctor_id])
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data

# =========================================
# Claim (FINAL MERGE)
# =========================================

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    claim_date = Column(DateTime, default=datetime.utcnow)

    # ===================== Relasi Utama =======================
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    patient = relationship("Patient", back_populates="claims", foreign_keys=[patient_id])

    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=False)
    visit = relationship("Visit", back_populates="claims", foreign_keys=[visit_id])

    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    hospital = relationship("Hospital", back_populates="claims", foreign_keys=[hospital_id])

    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=True)
    medical_record = relationship("MedicalRecord", back_populates="claim", uselist=False)

    # ===================== Status Klaim =======================
    status = Column(String, nullable=False, default="draft")
    is_final = Column(Boolean, nullable=False, server_default=text("false"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))

    # Dokter pembuat klaim
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    doctor = relationship("User", back_populates="claims_as_doctor", foreign_keys=[doctor_id])
    doctor_name = Column(String(100), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    # ===================== Workflow Tracking =======================
    workflow_status = Column(String, default="draft")
    # draft → doctor_submitted → coder_review → coder_verified → verifikator_review → finalized

    doctor_submitted_by = Column(String, nullable=True)
    doctor_submitted_at = Column(DateTime, nullable=True)

    coder_verified_by = Column(String, nullable=True)
    coder_verified_at = Column(DateTime, nullable=True)

    finalized_by = Column(String, nullable=True)
    finalized_at = Column(DateTime, nullable=True)

    ai_medical_resume = Column(Text, nullable=True)

    # ======================= Relasi ===========================
    ai_recommendations = relationship("ClaimAIRecommendation", back_populates="claim", cascade="all, delete-orphan")
    diagnoses = relationship("ClaimDiagnosis", back_populates="claim", cascade="all, delete-orphan")
    procedures = relationship("ClaimProcedure", back_populates="claim", cascade="all, delete-orphan")
    tariffs = relationship("ClaimTariff", back_populates="claim", cascade="all, delete-orphan")
    diagnosis_evaluations = relationship("ClaimDiagnosisEvaluation", back_populates="claim", cascade="all, delete-orphan")
    procedure_evaluations = relationship("ClaimProcedureEvaluation", back_populates="claim", cascade="all, delete-orphan")
    combination_alternatives = relationship("ClaimCombinationAlternative", back_populates="claim", cascade="all, delete-orphan")
    simulations = relationship("ClaimSimulation", back_populates="claim", cascade="all, delete-orphan")
    regulation_details = relationship("ClaimRegulationDetail", back_populates="claim", cascade="all, delete-orphan")
    
    logs = relationship("ClaimLog", back_populates="claim")
    notes = relationship("ClaimNote", back_populates="claim", cascade="all, delete")
    visit_links = relationship("ClaimVisitLink", back_populates="claim", cascade="all, delete-orphan")

    group_id = Column(Integer, ForeignKey("claim_groups.id"), nullable=True)
    group = relationship("ClaimGroup", back_populates="claims")

    @property
    def external_visits(self):
        return [v.external_visit_id for v in self.visit_links]

    # =========================================================
    # 📤 Format Ekspor (termasuk workflow info)
    # =========================================================
    def to_export_dict(self):
        """Format siap ekspor ke Excel + workflow tracking."""
        return {
            "ID Klaim": self.id,
            "Tanggal Klaim": self.claim_date.strftime("%Y-%m-%d") if self.claim_date else "-",
            "Nama Pasien": self.patient_name,
            "No. RM": self.patient.no_rm if self.patient else "-",
            "Rumah Sakit": self.hospital_name,
            "Dokter": self.doctor_display,
            "Status": self.status,
            "Workflow Status": self.workflow_status or "draft",
            "Final": "Ya" if self.is_final else "Tidak",
            "Total Diagnosis": self.total_diagnoses,
            "Total Tindakan": self.total_procedures,
            "ICD10 Utama": self.primary_icd10,
            "ICD9 Utama": self.primary_icd9,
            "Status Verifikasi": "Verified" if self.coder_verified_by else "Pending",
            "Verified By Coder": self.coder_verified_by or "-",
            "Dibuat": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "-",
        }

# =========================================
# Claim AI Recommendations
# =========================================
class ClaimAIRecommendation(Base):
    __tablename__ = "claim_ai_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    stage = Column(String(50), nullable=False)     # admission / daily / discharge
    category = Column(String(50), nullable=False)  # diagnosis / komorbid / komplikasi

    # Tidak lagi simpan klinis/ICD/tindakan mentah2 → gunakan relasi
    diagnosis_id = Column(Integer, ForeignKey("claim_diagnoses.id"), nullable=True)

    confidence_score = Column(Integer, nullable=True)
    child = Column(Boolean, nullable=False, server_default=text("false"))

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    # Relasi
    diagnosis = relationship("ClaimDiagnosis", foreign_keys=[diagnosis_id])
    claim = relationship("Claim", back_populates="ai_recommendations")

    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))

    @property
    def nama_kategori(self):
        return self.diagnosis.diagnosis_text if self.diagnosis else None

    # 🔹 helper property agar gampang dipakai FE
    @property
    def klinis(self):
        if self.diagnosis:
            parts = [self.diagnosis.justifikasi, self.diagnosis.bukti_klinis, self.diagnosis.syarat_klinis]
            return " | ".join([p for p in parts if p])
        return None

    @property
    def icd10_code(self):
        return self.diagnosis.icd10_code if self.diagnosis else None

    @property
    def tindakan(self):
        return self.procedure.procedure_text if self.procedure else None


# =========================================
# Claim Diagnoses
# =========================================
class ClaimDiagnosis(Base):
    __tablename__ = "claim_diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    diagnosis_type = Column(String(50), nullable=False)  # utama / sekunder
    diagnosis_text = Column(Text, nullable=False)
    diagnosis_source = Column(String(50), default="manual")  # ai/manual
    icd10_code = Column(String(20), nullable=True)
    justifikasi_klinis = Column(Text, nullable=True)
    syarat_klinis = Column(Text, nullable=True)
    bukti_klinis = Column(Text, nullable=True)
    tingkat_faskes = Column(Text, nullable=True)
    justifikasi_faskes = Column(Text, nullable=True)
    kompetensi_faskes = Column(Text, nullable=True)
    kode_ganda_icd10 = Column(Text, nullable=True)
    z_code_icd10 = Column(Text, nullable=True)
    kode_bpjs_khusus_icd10 = Column(Text, nullable=True)
    klinis = Column(Text, nullable=True)
    lama_rawat_inap = Column(Text, nullable=True)
    kriteria_rawat_inap = Column(Text, nullable=True)
    indikasi_rawat_inap = Column(Text, nullable=True)
    indikasi_rujukan = Column(Text, nullable=True)
    kriteria_rujukan = Column(Text, nullable=True)
    tujuan_rujukan = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    claim = relationship("Claim", back_populates="diagnoses")
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data


# =========================================
# Claim Procedures
# =========================================
class ClaimProcedure(Base):
    __tablename__ = "claim_procedures"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    procedure_source = Column(String(50), default="manual")
    procedure_text = Column(Text, nullable=False)
    requirement_flag = Column(Boolean, nullable=False, server_default=text("false"))

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    claim = relationship("Claim", back_populates="procedures")
    procedure_details = relationship("ClaimProcedureDetail", back_populates="procedure", cascade="all, delete-orphan")

    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))
    stage = Column(String(50), nullable=False, default="admission")  # admission / daily / discharge
    icd9_final_by_coder = Column(String(20), nullable=True)   # ICD-9 final yang diketik coder
    verified_by = Column(String(100), nullable=True)          # siapa coder yang verifikasi
    verified_at = Column(DateTime, nullable=True)
    @property
    def description(self):
        if not self.procedure_details:
            return None
        return self.procedure_details[0].description

    @property
    def icd9_code(self):
        """Ambil ICD-9 dari detail pertama jika ada."""
        if self.procedure_details and len(self.procedure_details) > 0:
            return self.procedure_details[0].icd9_tindakan
        return None

# =========================================
# Claim Procedure Details
# =========================================
class ClaimProcedureDetail(Base):
    __tablename__ = "claim_procedure_details"

    id = Column(Integer, primary_key=True, index=True)
    claim_simulation_id = Column(Integer, ForeignKey("claim_simulations.id", ondelete="CASCADE"), nullable=False)

    # satu detail hanya milik satu simulation
    simulation = relationship("ClaimSimulation", back_populates="procedure_details")

    procedure_id = Column(Integer, ForeignKey("claim_procedures.id"), nullable=False)
    procedure = relationship("ClaimProcedure", back_populates="procedure_details")

    icd9_tindakan = Column(String, nullable=False)
    validitas_tindakan = Column(String, nullable=False)
    status_tindakan = Column(String, nullable=True)
    ina_cbg_tindakan = Column(Text, nullable=True)
    faskes_tindakan = Column(Text, nullable=True)
    rawat_inap_tindakan = Column(Text, nullable=True)
    syarat_klinis_tindakan = Column(Text, nullable=True)
    deskripsi_tindakan = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    is_dummy = Column(Boolean, default=False)

    @property
    def description(self):
        parts = [
            f"ICD-9: {self.icd9_tindakan}" if self.icd9_tindakan else "",
            f"Status: {self.status_tindakan}" if self.status_tindakan else "",
            f"INA-CBG: {self.ina_cbg_tindakan}" if self.ina_cbg_tindakan else ""
        ]
        return ", ".join([p for p in parts if p])

# =========================================
# Claim Detail Regulations
# =========================================
class ClaimRegulationDetail(Base):
    __tablename__ = "claim_regulation_details"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    diagnosis_id = Column(Integer, ForeignKey("claim_diagnoses.id"), nullable=True)
    procedure_id = Column(Integer, ForeignKey("claim_procedures.id"), nullable=True)
    diagnosis_evaluation_id = Column(Integer, ForeignKey("claim_diagnosis_evaluations.id"), nullable=True)
    procedure_evaluation_id = Column(Integer, ForeignKey("claim_procedure_evaluations.id"), nullable=True)
    idrg_diagnosis_id = Column(Integer, ForeignKey("claim_idrg_diagnosis.id"), nullable=True)
    idrg_summary_id   = Column(Integer, ForeignKey("claim_idrg_summary.id"), nullable=True)


    judul_regulasi = Column(String(255), nullable=False)   # contoh: PNPK Sepsis 2020
    dasar_hukum    = Column(String(255), nullable=True)    # contoh: Permenkes, PNPK, ICD-10, INA-CBG
    bab_pasal      = Column(String(255), nullable=True)    # contoh: Bab II, Pasal 4 ayat (2)
    isi            = Column(Text, nullable=True)           # isi/penjelasan regulasi

    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"), onupdate=text("now()"))
    is_deleted = Column(Boolean, default=False)
    is_dummy = Column(Boolean, default=False)

    claim = relationship("Claim", back_populates="regulation_details")
    diagnosis = relationship("ClaimDiagnosis")
    procedure = relationship("ClaimProcedure")
    diagnosis_evaluation = relationship("ClaimDiagnosisEvaluation")
    procedure_evaluation = relationship("ClaimProcedureEvaluation")
    idrg_diagnosis = relationship("ClaimIDRGDiagnosis")
    idrg_summary = relationship("ClaimIDRGSummary")


# =========================================
# Claim AI Simulations
# =========================================
class ClaimSimulation(Base):
    __tablename__ = "claim_simulations"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    stage = Column(String, nullable=False)  # admission, daily1, discharge

    diagnosis_utama_id = Column(Integer, ForeignKey("claim_diagnoses.id"), nullable=True)
    diagnosis_sekunder_id = Column(Integer, ForeignKey("claim_diagnoses.id"), nullable=True)
    tindakan_utama_id = Column(Integer, ForeignKey("claim_procedures.id"), nullable=True)
    tindakan_sekunder_id = Column(Integer, ForeignKey("claim_procedures.id"), nullable=True)

    is_dummy = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ================== ✅ Coder Verification ==================
    coder_verified = Column(Boolean, default=False)
    coder_verified_by = Column(String, nullable=True)
    coder_verified_at = Column(DateTime, nullable=True)
    coder_notes = Column(Text, nullable=True)

    verified_icd10 = Column(String, nullable=True)
    verified_icd10_name = Column(Text, nullable=True)
    verified_icd9 = Column(String, nullable=True)
    verified_icd9_name = Column(Text, nullable=True)
    is_coder_approved = Column(Boolean, default=False)

    # 🔗 Relasi
    claim = relationship("Claim", back_populates="simulations")
    diagnosis_utama = relationship("ClaimDiagnosis", foreign_keys=[diagnosis_utama_id])
    diagnosis_sekunder = relationship("ClaimDiagnosis", foreign_keys=[diagnosis_sekunder_id])
    tindakan_utama = relationship("ClaimProcedure", foreign_keys=[tindakan_utama_id])
    tindakan_sekunder = relationship("ClaimProcedure", foreign_keys=[tindakan_sekunder_id])

    procedure_details = relationship(
        "ClaimProcedureDetail",
        back_populates="simulation",
        cascade="all, delete-orphan"
    )

# =========================================
# Claim AI Recommendations Summary
# =========================================
class ClaimDiagnosisEvaluation(Base):
    __tablename__ = "claim_diagnosis_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))

    validitas = Column(Enum("valid", "invalid", "warning", name="eval_status"), nullable=True)
    validitas_detail = Column(String(255), nullable=True)
    severity = Column(String(50), nullable=True)
    kode_ina_cbg = Column(String(50), nullable=True)
    estimasi_tarif = Column(Numeric(18, 2), nullable=True)
    syarat_klinis = Column(Text, nullable=True)
    evaluasi_faskes = Column(Text, nullable=True)
    rawat_inap = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"), onupdate=text("now()"))
    is_deleted = Column(Boolean, default=False)
    is_dummy = Column(Boolean, default=False)

    claim = relationship("Claim", back_populates="diagnosis_evaluations")



class ClaimProcedureEvaluation(Base):
    __tablename__ = "claim_procedure_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))

    validitas = Column(Enum("valid", "invalid", "warning", name="eval_status_proc"), nullable=True)
    validitas_detail = Column(String(255), nullable=True)

    status_tindakan = Column(String(50), nullable=True)   # wajib / opsional / minor
    tarif_impact = Column(Numeric(18, 2), nullable=True)
    faskes = Column(Text, nullable=True)
    rawat_inap = Column(Text, nullable=True)
    syarat_klinis = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"), onupdate=text("now()"))
    is_deleted = Column(Boolean, default=False)
    is_dummy = Column(Boolean, default=False)

    claim = relationship("Claim", back_populates="procedure_evaluations")


class ClaimCombinationAlternative(Base):
    __tablename__ = "claim_combination_alternatives"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))

    kombinasi_nama = Column(String(255), nullable=True)
    severity = Column(String(50), nullable=True)
    kode_ina_cbg = Column(String(50), nullable=True)
    estimasi_tarif = Column(Numeric(18, 2), nullable=True)
    syarat_klinis = Column(Text, nullable=True)
    faskes = Column(Text, nullable=True)
    rawat_inap = Column(Text, nullable=True)
    tindakan_wajib = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"), onupdate=text("now()"))
    is_deleted = Column(Boolean, default=False)
    is_dummy = Column(Boolean, default=False)

    claim = relationship("Claim", back_populates="combination_alternatives")

# =========================================
# i-DRG Diagnosis (per modal detail diagnosis)
# =========================================
class ClaimIDRGDiagnosis(Base):
    __tablename__ = "claim_idrg_diagnosis"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    group_idrg = Column(String(50))
    severity_index = Column(String(50))
    checklist = Column(Text)
    faktor_severity = Column(Text)
    ungroupable_alert = Column(Text)
    simulasi_tarif = Column(String(50))
    gap_analysis = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    is_dummy = Column(Boolean, default=False)


# =========================================
# i-DRG Summary (hasil kombinasi verifikator)
# =========================================
class ClaimIDRGSummary(Base):
    __tablename__ = "claim_idrg_summary"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    group_idrg_kombinasi = Column(String(50))
    severity_kombinasi = Column(String(50))
    checklist_kombinasi = Column(Text)
    faktor_severity = Column(Text)
    risiko_ungroupable = Column(Text)
    estimasi_tarif = Column(String(50))
    gap_inacbg_vs_idrg = Column(String(50))
    rekomendasi_ai = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    is_dummy = Column(Boolean, default=False)

# =========================================
# Claim Tariffs (INA-CBGs result)
# =========================================
class ClaimTariff(Base):
    __tablename__ = "claim_tariffs"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    cbg_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    tariff_amount = Column(Integer, nullable=True)
    status = Column(String(20), default="draft")   # draft / final

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    claim = relationship("Claim", back_populates="tariffs")
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data


# =========================================
# Claim Logs (Audit Trail)
# =========================================
class ClaimLog(Base):
    __tablename__ = "claim_logs"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    action = Column(String(50), nullable=False)   # created / updated / finalized / rejected / recalculated
    description = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="logs")
    user = relationship("User")
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data

# =========================================
# Medical Record
# =========================================

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)

    record_type = Column(String(50), nullable=False)  # admission / daily / discharge
    

    # Status rekam medis → sinkron dengan klaim
    is_final = Column(Boolean, nullable=False, server_default=text("false"))

    notes_date = Column(Date, nullable=False, default=datetime.utcnow)

    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_name = Column(String(100), nullable=False)

    # Bagian Riwayat
    riwayat_penyakit = Column(Text, nullable=True)
    riwayat_pengobatan = Column(Text, nullable=True)
    riwayat_operasi = Column(Text, nullable=True)
    alergi = Column(Text, nullable=True)
    keluhan = Column(Text, nullable=True)
    gejala_lain = Column(Text, nullable=True)

    # Pemeriksaan Fisik
    tekanan_darah = Column(String(100), nullable=True)
    nadi = Column(String(100), nullable=True)
    pernapasan = Column(String(100), nullable=True)
    suhu = Column(String(100), nullable=True)
    spo2 = Column(String(100), nullable=True)
    berat_badan = Column(String(100), nullable=True)
    tinggi_badan = Column(String(100), nullable=True)

    # Lab & Penunjang
    hemoglobin = Column(String(100), nullable=True)
    leukosit = Column(String(100), nullable=True)
    trombosit = Column(String(100), nullable=True)
    gula_darah = Column(String(100), nullable=True)
    creatinin = Column(String(100), nullable=True)
    rontgen_thorax = Column(Text, nullable=True)
    ct_scan = Column(Text, nullable=True)
    usg = Column(Text, nullable=True)

    # Diagnosis & Tindakan
    diagnosis_awal = Column(Text, nullable=True)
    komorbid = Column(Text, nullable=True)
    komplikasi = Column(Text, nullable=True)
    diagnosis_akhir = Column(Text, nullable=True)
    tindakan = Column(Text, nullable=True)

    # Obat & Catatan
    obat = Column(Text, nullable=True)
    validasi_fornas = Column(Text, nullable=True)
    notes_doctor = Column(Text, nullable=True)

    # Relasi ke pasien
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    patient = relationship("Patient", back_populates="medical_records", foreign_keys=[patient_id])

    # Relasi ke kunjungan
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=False)
    visit = relationship("Visit", back_populates="medical_records", foreign_keys=[visit_id])

    # Relasi ke dokter
    doctor = relationship("User", back_populates="medical_records", foreign_keys=[doctor_id])

    # Relasi ke klaim (1-1)
    claim = relationship("Claim", back_populates="medical_record", uselist=False)

    # Relasi ke log perubahan
    logs = relationship("MedicalRecordLog", back_populates="medical_record", foreign_keys="MedicalRecordLog.medical_record_id")

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    def to_dict(self):
        def normalize(val):
            if isinstance(val, uuid.UUID):
                return str(val)                   # UUID jadi string
            if isinstance(val, (datetime, date)):
                return val.isoformat()            # Date/Datetime ke ISO string
            return val

        return {
            c.key: normalize(getattr(self, c.key))
            for c in inspect(self).mapper.column_attrs
        }
    def to_export_dict(self):
        """Format rekam medis siap untuk ekspor ke Excel."""
        def val(v):
            if v is None or v == "":
                return "-"
            if isinstance(v, (datetime, date)):
                return v.strftime("%Y-%m-%d")
            return str(v)

        return {
            "ID Rekam Medis": self.id,
            "Tanggal Catatan": val(self.notes_date),
            "Jenis Rekam": self.record_type or "-",
            "Nama Pasien": self.patient.nama if self.patient else "-",
            "No. RM": self.patient.no_rm if self.patient else "-",
            "Jenis Kelamin": self.patient.jenis_kelamin if self.patient else "-",
            "Tanggal Lahir": val(self.patient.tanggal_lahir if self.patient else None),
            "Dokter": self.doctor_name or (self.doctor.name if self.doctor else "-"),
            "Rumah Sakit": (
                self.patient.hospital.nama
                if self.patient and self.patient.hospital
                else "-"
            ),
            "Keluhan": self.keluhan or "-",
            "Diagnosis Awal": self.diagnosis_awal or "-",
            "Diagnosis Akhir": self.diagnosis_akhir or "-",
            "Tindakan": self.tindakan or "-",
            "Obat": self.obat or "-",
            "Catatan Dokter": self.notes_doctor or "-",
            "Validasi Fornas": self.validasi_fornas or "-",
        }

    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data

# =========================================
# Medical Record Logs (Audit Trail)
# =========================================

class MedicalRecordLog(Base):
    __tablename__ = "medical_record_logs"

    id = Column(Integer, primary_key=True, index=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    data_snapshot = Column(JSONB, nullable=True)
    action = Column(String(50), nullable=False)   # created / updated / finalized / rejected / recalculated
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_by = Column(Integer, ForeignKey("users.id"))

    medical_record = relationship("MedicalRecord", back_populates="logs")
    user = relationship("User", back_populates="medical_record_logs")
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data


# =========================================
# User Management
# =========================================

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, text

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    auth0_sub = Column(String, unique=True, index=True, nullable=True)  # Auth0 user_id
    email = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)
    jabatan = Column(String, nullable=True)
    sip_number = Column(String, nullable=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)

    # legacy single-role
    role = Column(String(50), nullable=True, default="doctor")

    # new multi-role system
    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        overlaps="user_roles"
    )
    user_roles = relationship(
        "UserRole",
        back_populates="user",
        overlaps="roles,users"
    )

    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    is_deleted = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_dummy = Column(Boolean, nullable=False, default=False, server_default=text("false"))

    # relationships
    hospital = relationship("Hospital", back_populates="users", foreign_keys=[hospital_id])
    admin_of_hospital = relationship("Hospital", back_populates="admin", foreign_keys=[Hospital.admin_id])
    claims_as_doctor = relationship("Claim", back_populates="doctor", foreign_keys=[Claim.doctor_id])
    visits = relationship("Visit", back_populates="doctor", foreign_keys=[Visit.doctor_id])
    medical_records = relationship("MedicalRecord", back_populates="doctor", foreign_keys=[MedicalRecord.doctor_id])
    medical_record_logs = relationship("MedicalRecordLog", back_populates="user", foreign_keys=[MedicalRecordLog.updated_by])

    # === Helper Methods ===
    @property
    def role_names(self):
        """Return list of role names (multi-role aware)."""
        if self.roles and len(self.roles) > 0:
            return [r.name for r in self.roles]
        elif self.role:
            return [self.role]
        return []

    def has_role(self, role_name: str) -> bool:
        """Check if user has specific role."""
        return role_name in self.role_names

    def __repr__(self):
        return f"<User(name={self.name}, roles={self.role_names})>"

from sqlalchemy import Table, Column, Integer, String, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship

# =========================================
# Role Table
# =========================================

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)   # doctor, coder, verificator, admin_rs, dll
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime, server_default=text("now()"))

    # Relasi ke users
    users = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        overlaps="user_roles"
    )
    user_roles = relationship(
        "UserRole",
        back_populates="role",
        overlaps="roles,users"
    )

    def __repr__(self):
        return f"<Role(name={self.name})>"


# =========================================
# UserRoles (Bridge Table)
# =========================================

class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(DateTime, server_default=text("now()"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))

    # Relasi opsional

    user = relationship(
        "User",
        back_populates="user_roles",
        overlaps="roles,users"
    )
    role = relationship(
        "Role",
        back_populates="user_roles",
        overlaps="roles,users"
    )

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class ClaimNote(Base):
    __tablename__ = "claim_notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"))
    item_id = Column(Integer, nullable=True)   # bisa diagnosis/procedure ID
    role = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    note_text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.timezone("Asia/Jakarta")))
    parent_id = Column(Integer, ForeignKey("claim_notes.id", ondelete="CASCADE"), nullable=True)
    field_key = Column(String, nullable=True)  # <--- untuk primary_diagnosis / primary_action, dll
    stage = Column(String, nullable=True)      # <--- admission, daily-0, discharge, dst.
    origin_item_id = Column(Integer, nullable=True)
    
    # relasi
    claim = relationship("Claim", back_populates="notes")
    user = relationship("User")


# =========================================
# Rules Master - Multi Layer Rule System
# =========================================

class RulesMaster(Base):
    __tablename__ = "rules_master"

    id = Column(Integer, primary_key=True, index=True)
    diagnosis = Column(Text, nullable=False)       # Nama diagnosis: "Pneumonia", "DM Tipe 2", dll
    field = Column(Text, nullable=False)           # Field aturan: "rawat_inap.lama_rawat", dll
    layer = Column(Text, nullable=False)           # Layer: "permenkes", "nasional", "ppk", "regional", "rs", "bridging", "fraud", "temporary"
    isi = Column(Text, nullable=False)             # Isi aturan: "LOS ≥ 2 hari", dll
    sumber = Column(Text, nullable=True)           # Sumber: "PNPK Pneumonia 2023", "PPK RS Notopuro 2024", dll
    pdf_file = Column(Text, nullable=True)         # Nama file PDF: "ppk_hipertensi_2024.pdf", null jika tidak ada
    rs_id = Column(Text, nullable=True)            # ID RS: "rs_notopuro", null untuk rules global
    region_id = Column(Text, nullable=True)        # ID wilayah: "jatim", null untuk rules global
    status = Column(Text, nullable=False, default="unverified")  # Status: "unverified", "official", "active", "rejected"
    created_by = Column(Text, nullable=True)       # Pembuat: "admin_rs_notopuro", "ai_meta_admin", dll
    approved_by = Column(Text, nullable=True)      # Yang approve: "ai_meta_reviewer_1", dll
    approved_date = Column(DateTime, nullable=True) # Tanggal approval
    review_notes = Column(Text, nullable=True)     # Catatan reviewer AI META
    feedback = Column(Text, nullable=True)         # Feedback dari RS tentang aturan ini
    feedback_by = Column(Text, nullable=True)      # Yang beri feedback: "admin_rs_notopuro", dll
    feedback_date = Column(DateTime, nullable=True) # Tanggal feedback
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    def __repr__(self):
        return f"<RulesMaster(id={self.id}, diagnosis={self.diagnosis}, layer={self.layer}, status={self.status})>"


class RegionalReports(Base):
    __tablename__ = "regional_reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)           # Judul laporan: "SE BPJS Jatim No.01/2024"
    description = Column(Text, nullable=True)      # Deskripsi edaran
    se_file = Column(Text, nullable=False)         # Nama file SE PDF yang diupload
    region_id = Column(Text, nullable=False)       # ID wilayah: "jatim", "jabar", dll
    rs_id = Column(Text, nullable=False)           # ID RS pelapor: "rs_2", dll
    status = Column(Text, nullable=False, default="pending")  # Status: "pending", "reviewed", "converted", "rejected"
    reported_by = Column(Text, nullable=False)     # Pelapor: "admin_rs_notopuro"
    reviewed_by = Column(Text, nullable=True)      # AI META reviewer
    reviewed_date = Column(DateTime, nullable=True) # Tanggal review
    review_notes = Column(Text, nullable=True)     # Catatan AI META
    converted_rules_count = Column(Integer, nullable=True, default=0)  # Jumlah rules yang dihasilkan
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    def __repr__(self):
        return f"<RegionalReports(id={self.id}, title={self.title}, status={self.status})>"
# 🔗 Claim <-> Visit (External Link)
# =========================================
class ClaimVisitLink(Base):
    """
    Bridge table untuk menghubungkan klaim lokal (AI-Claim)
    dengan visit yang tersimpan di server rumah sakit.
    Tidak ada foreign key ke tabel Visit karena itu berada di luar sistem ini.
    """
    __tablename__ = "claim_visit_links"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)

    # visit_id berasal dari sistem RS, jadi hanya disimpan sebagai integer/string mentah
    external_visit_id = Column(String(100), nullable=False)

    # optional metadata
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    is_primary = Column(Boolean, nullable=False, server_default=text("false"))
    note = Column(String(255), nullable=True)

    # Relasi lokal
    claim = relationship("Claim", back_populates="visit_links")
    hospital = relationship("Hospital")

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))

    def __repr__(self):
        return f"<ClaimVisitLink(claim_id={self.claim_id}, external_visit_id={self.external_visit_id})>"

class ClaimGroup(Base):
    __tablename__ = "claim_groups"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    kode_group = Column(String(50), nullable=False, unique=True)  # ex: E001
    nama_group = Column(String(255), nullable=False)              # ex: Pneumonia
    deskripsi = Column(Text, nullable=True)
    tanggal_mulai = Column(Date, nullable=True)
    tanggal_selesai = Column(Date, nullable=True)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"), onupdate=text("now()"))

    # 🔗 Relasi
    claims = relationship("Claim", back_populates="group")
    patient = relationship("Patient", foreign_keys=[patient_id])
    hospital = relationship("Hospital", foreign_keys=[hospital_id])
