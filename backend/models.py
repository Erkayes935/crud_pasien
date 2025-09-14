"""
Module: backend.models

Defines the SQLAlchemy ORM models used by the application:
- Patient: stores patient personal information only.
- Claim: stores visit/claim information linked to a patient.
- User: stores application users linked to Auth0 via `auth0_sub` and a role.
- Hospital: stores hospital information, as root entity for grouping users & patients.
- Visit: stores visit information linked to a patient.
"""

from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime, Boolean, Enum, JSON, Float, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
import uuid

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
# Claim
# =========================================

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    claim_date = Column(DateTime, default=datetime.utcnow)

    # Relasi ke pasien
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    patient = relationship("Patient", back_populates="claims", foreign_keys=[patient_id])

    # Relasi ke visit
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=False)
    visit = relationship("Visit", back_populates="claims", foreign_keys=[visit_id])

    # Relasi ke rumah sakit
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    hospital = relationship("Hospital", back_populates="claims", foreign_keys=[hospital_id])

    # Relasi ke rekam medis (wajib 1-1)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=False, unique=True)
    medical_record = relationship("MedicalRecord", back_populates="claim", uselist=False)

    simulasi_draft = Column(JSONB, nullable=True)
    summary_draft = Column(JSONB, nullable=True)
    status = Column(String, nullable=False, default="draft")
    # Status boolean → sinkron dengan rekam medis
    is_final = Column(Boolean, nullable=False, server_default=text("false"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data
    # Dokter yang membuat klaim (opsional)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    doctor = relationship("User", back_populates="claims_as_doctor", foreign_keys=[doctor_id])
    doctor_name = Column(String(100), nullable=True)  # audit trail

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))
    ai_recommendations = relationship("ClaimAIRecommendation", back_populates="claim", cascade="all, delete-orphan")
    diagnoses = relationship("ClaimDiagnosis", back_populates="claim", cascade="all, delete-orphan")
    procedures = relationship("ClaimProcedure", back_populates="claim", cascade="all, delete-orphan")
    tariffs = relationship("ClaimTariff", back_populates="claim", cascade="all, delete-orphan")
    ai_recommendations_summary = relationship("ClaimAIRecommendationSummary", back_populates="claim", uselist=False, cascade="all, delete-orphan")

    # logs sebaiknya tanpa delete-orphan, hanya back_populates
    logs = relationship("ClaimLog", back_populates="claim")


# =========================================
# Claim AI Recommendations
# =========================================
class ClaimAIRecommendation(Base):
    __tablename__ = "claim_ai_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    type = Column(String(50), nullable=False)   # diagnosis / procedure
    category = Column(String(50), nullable=False) # ddx / komorbid / komplikasi / pretindakan
    sim_text = Column(Text, nullable=False)          # nama diagnosis/tindakan
    sim_detail = Column(JSONB, nullable=True)        # simpan dict lengkap
    icd10_code = Column(String(20), nullable=True)
    icd9_code = Column(String(20), nullable=True)
    confidence_score = Column(Integer, nullable=True)
    regulation_refs = Column(JSONB, nullable=True)  # CP, PNPK, Fornas, Permenkes

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    claim = relationship("Claim", back_populates="ai_recommendations")
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data


# =========================================
# Claim Diagnoses
# =========================================
class ClaimDiagnosis(Base):
    __tablename__ = "claim_diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    diagnosis_type = Column(String(50), nullable=False)  # utama / sekunder
    subtype = Column(String(50), nullable=True)          # komorbid / komplikasi / none
    diagnosis_text = Column(Text, nullable=False)
    icd10_code = Column(String(20), nullable=True)

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

    procedure_type = Column(String(50), nullable=False)  # utama / sekunder
    procedure_text = Column(Text, nullable=False)
    icd9_code = Column(String(20), nullable=True)
    requirement_flag = Column(Boolean, nullable=False, server_default=text("false"))    # wajib/tidak

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))

    claim = relationship("Claim", back_populates="procedures")
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data


# =========================================
# Claim Tariffs (INA-CBGs result)
# =========================================
class ClaimTariff(Base):
    __tablename__ = "claim_tariffs"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    cbg_code = Column(String(50), nullable=True)
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

# ===========================
# Rekomendasi AI untuk Klaim
# ===========================
class ClaimAIRecommendationSummary(Base):
    __tablename__ = "claim_ai_recommendations_summary"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    category = Column(Enum("medis","regulasi","tarif", name="recommendation_category"), nullable=False)
    target = Column(JSONB, nullable=True)   # contoh: ["Sepsis","ARDS"]
    status = Column(Enum("valid","warning","invalid", name="recommendation_status"), nullable=False)
    message = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, default=text("now()"), onupdate=text("now()"))

    claim = relationship("Claim", back_populates="ai_recommendations_summary")
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
    td = Column(String(100), nullable=True)
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
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "diagnosis_awal": self.diagnosis_awal or "",
            "komorbid": self.komorbid or "",
            "komplikasi": self.komplikasi or "",
            "tindakan": self.tindakan or "",
            "is_final": self.is_final,
            "notes_date": self.notes_date.isoformat() if self.notes_date else None,
        }
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data

# =========================================
# Medical Record Logs (Audit Trail)
# =========================================

class MedicalRecordLog(Base):
    __tablename__ = "medical_record_logs"

    id = Column(Integer, primary_key=True, index=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=False)
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

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    auth0_sub = Column(String, unique=True, index=True, nullable=True)  # sinkron ke Auth0 user_id
    email = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=True)  # ✅ Wajib, untuk identitas user
    role = Column(String(50), nullable=True, default="doctor")
    jabatan = Column(String, nullable=True)   # khusus dokter/admin
    sip_number = Column(String, nullable=True) # khusus dokter
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)  # kalau admin_rs

    hospital = relationship("Hospital", back_populates="users", foreign_keys=[hospital_id])
    admin_of_hospital = relationship("Hospital", back_populates="admin", foreign_keys=[Hospital.admin_id])
    claims_as_doctor = relationship("Claim", back_populates="doctor", foreign_keys=[Claim.doctor_id])
    visits = relationship("Visit", back_populates="doctor", foreign_keys=[Visit.doctor_id])
    medical_records = relationship("MedicalRecord", back_populates="doctor", foreign_keys=[MedicalRecord.doctor_id])
    medical_record_logs = relationship("MedicalRecordLog", back_populates="user", foreign_keys=[MedicalRecordLog.updated_by])
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))   # soft delete flag
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))     # tandai dummy data