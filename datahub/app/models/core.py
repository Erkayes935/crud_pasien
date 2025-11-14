from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Text, Float, Date, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
import datetime
import uuid

Base = declarative_base()

# =====================================================================
# 📊 DATA INGESTION TABLES (untuk tracking raw data)
# =====================================================================

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
    
    # FASE 2.6: Similarity Info (ALL records, even < 85%)
    similarity_info = Column(JSON, nullable=True)  # {"checked": true, "max_score": 75.5, "closest_record": "REC_123", "confidence": null}
    
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
    duplicate_record_ids = Column(JSON)
    similarity_score = Column(Float)
    duplicate_type = Column(String(20))  # 'exact' atau 'fuzzy'
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


# =====================================================================
# 🔐 ANONYMIZATION & HYBRID SYNC
# =====================================================================

class PatientUUIDMap(Base):
    """
    Mapping hash → UUID untuk hybrid sync (Gateway + DataHub).
    KUNCI UTAMA: name_hash + nik_hash + hospital_id → patient_uuid
    
    Table ini menyimpan HASH ONLY, bukan data asli!
    """
    __tablename__ = "patient_uuid_map"
    
    id = Column(Integer, primary_key=True)
    patient_uuid = Column(String(36), unique=True, nullable=False, index=True)
    
    # Source tracking
    source_type = Column(String(20), nullable=False, index=True)  # "gateway", "manual", "excel"
    hospital_id = Column(String(64), nullable=False, index=True)
    source_record_id = Column(String(64), nullable=True)
    
    # 🔒 HASH ONLY - NEVER store plaintext!
    name_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash
    nik_hash = Column(String(64), nullable=True, index=True)   # SHA256 hash
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    last_synced = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


# =====================================================================
# 👤 PATIENT - Full Structure
# =====================================================================

class Patient(Base):
    """
    Data pasien yang sudah di-anonymize.
    
    GATEWAY (API): Field sensitif sudah DI-MASK
    - Nama: "Sep**** Rid**"
    - NIK: "************3456"
    - No HP: "********7890"
    - Tanggal lahir, alamat, email: TETAP ASLI
    
    DATAHUB (Manual/Excel): Akan di-anonymize saat input
    """
    __tablename__ = "patients"
    
    # Primary keys
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    patient_uuid = Column(String(36), unique=True, nullable=False, index=True)  # Link to PatientUUIDMap
    
    # Hospital relation
    hospital_id = Column(String(64), index=True, nullable=False)
    
    # 🔒 ANONYMIZED FIELDS - Dari Gateway sudah masked
    nama = Column(String(100), nullable=True)           # "Sep**** Rid**" (from Gateway)
    no_ktp = Column(String(20), nullable=True)          # "************3456" (from Gateway)
    no_rm = Column(String(20), nullable=True)           # RM number (bisa masked atau tidak)
    no_bpjs = Column(String(20), nullable=True)         # BPJS number
    
    # 🟢 ORIGINAL DATA - Tetap disimpan (untuk keperluan valid)
    tanggal_lahir = Column(Date, nullable=True)         # Original date (TIDAK diubah ke umur)
    alamat = Column(Text, nullable=True)                # Original address (TIDAK disimplifikasi)
    email = Column(String(120), nullable=True)          # Original email (TETAP disimpan)
    
    # 🔒 MASKED PHONE
    no_hp = Column(String(20), nullable=True)           # "********7890" (from Gateway)
    
    # 🟢 SAFE FIELDS
    jenis_kelamin = Column(String(10), nullable=True)   # "L" / "P" (OK)
    
    # Metadata
    source_type = Column(String(20), default="manual")  # manual, excel, gateway
    eksternal_id = Column(String(100), nullable=True)   # ID dari sistem eksternal
    source = Column(String(100), nullable=True)         # Sumber data
    
    # Soft delete & dummy flags
    is_deleted = Column(Boolean, nullable=False, default=False)
    is_dummy = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    visits = relationship("Visit", back_populates="patient", cascade="all, delete-orphan")
    medical_records = relationship("MedicalRecord", back_populates="patient")

    def __repr__(self):
        return f"<Patient(uuid={self.patient_uuid}, nama={self.nama})>"


# =====================================================================
# 🏥 VISIT - Full Structure
# =====================================================================

class Visit(Base):
    """
    Data kunjungan pasien.
    Tidak ada PII kecuali nama dokter (yang sudah di-mask dari Gateway).
    """
    __tablename__ = "visits"
    
    # Primary keys
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    visit_uuid = Column(String(36), unique=True, nullable=False, index=True)
    
    # Relations
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    hospital_id = Column(String(64), index=True, nullable=False)
    
    # Visit details (SAFE - no PII)
    eksternal_id = Column(String(100), nullable=True)       # ID eksternal
    episode_id = Column(String(64), nullable=True)          # Episode rawat
    visit_no = Column(Integer, default=1)                   # Kunjungan ke-berapa
    
    # Visit info
    tanggal_kunjungan = Column(Date, nullable=False)
    jenis_kunjungan = Column(String(100), nullable=True)    # Rawat Inap/Jalan
    jenis_rawat = Column(String(50), default="Rawat Inap")
    lama_rawat = Column(Integer, default=1)                 # Dalam hari
    
    # Clinical info (safe for research)
    poli = Column(String(100), nullable=True)               # Poliklinik
    gejala = Column(Text, nullable=True)                    # Keluhan
    riwayat = Column(Text, nullable=True)                   # Riwayat penyakit
    
    # Doctor info (anonymized dari Gateway)
    doctor_id = Column(String(100), nullable=True)          # Doctor ID
    doctor_name = Column(String(100), nullable=True)        # "Dr. Sep****" (MASKED from Gateway)
    
    # Metadata
    source_type = Column(String(20), default="manual")
    sumber = Column(String(100), nullable=True)
    
    # Soft delete & dummy flags
    is_deleted = Column(Boolean, nullable=False, default=False)
    is_dummy = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="visits")
    medical_records = relationship("MedicalRecord", back_populates="visit", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Visit(uuid={self.visit_uuid}, patient_id={self.patient_id})>"


# =====================================================================
# 📋 MEDICAL RECORD - Full Structure
# =====================================================================

class MedicalRecord(Base):
    """
    Rekam medis pasien (clinical data - safe for research).
    Tidak ada PII, hanya data klinis.
    Nama dokter sudah di-mask dari Gateway.
    """
    __tablename__ = "medical_records"
    
    # Primary keys
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    record_uuid = Column(String(36), unique=True, nullable=False, index=True)
    
    # Relations
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=False)
    hospital_id = Column(String(64), index=True, nullable=False)
    
    # Record type & status
    record_type = Column(String(50), nullable=False)  # admission / daily / discharge
    is_final = Column(Boolean, nullable=False, default=False)
    notes_date = Column(Date, nullable=False, default=datetime.datetime.utcnow)
    
    # Doctor info (anonymized dari Gateway)
    doctor_id = Column(String(100), nullable=True)        # Anonymized ID
    doctor_name = Column(String(100), nullable=True)      # "Dr. Sep****" (MASKED from Gateway)
    
    # ========== RIWAYAT (SAFE - Clinical Data) ==========
    riwayat_penyakit = Column(Text, nullable=True)
    riwayat_pengobatan = Column(Text, nullable=True)
    riwayat_operasi = Column(Text, nullable=True)
    alergi = Column(Text, nullable=True)
    keluhan = Column(Text, nullable=True)
    gejala_lain = Column(Text, nullable=True)
    
    # ========== PEMERIKSAAN FISIK (SAFE) ==========
    tekanan_darah = Column(String(100), nullable=True)
    nadi = Column(String(100), nullable=True)
    pernapasan = Column(String(100), nullable=True)
    suhu = Column(String(100), nullable=True)
    spo2 = Column(String(100), nullable=True)
    berat_badan = Column(String(100), nullable=True)
    tinggi_badan = Column(String(100), nullable=True)
    
    # ========== LAB & PENUNJANG (SAFE) ==========
    hemoglobin = Column(String(100), nullable=True)
    leukosit = Column(String(100), nullable=True)
    trombosit = Column(String(100), nullable=True)
    gula_darah = Column(String(100), nullable=True)
    creatinin = Column(String(100), nullable=True)
    rontgen_thorax = Column(Text, nullable=True)
    ct_scan = Column(Text, nullable=True)
    usg = Column(Text, nullable=True)
    
    # ========== DIAGNOSIS & TINDAKAN (SAFE) ==========
    diagnosis_awal = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)             # Alias untuk diagnosis_awal
    komorbid = Column(Text, nullable=True)
    komplikasi = Column(Text, nullable=True)
    diagnosis_akhir = Column(Text, nullable=True)
    tindakan = Column(Text, nullable=True)
    
    # ========== OBAT & VALIDASI (SAFE) ==========
    obat = Column(Text, nullable=True)
    validasi_fornas = Column(Text, nullable=True)
    notes_doctor = Column(Text, nullable=True)
    
    # Metadata
    source_type = Column(String(20), default="manual")
    status = Column(String(50), default="ready_for_ai")
    
    # Soft delete & dummy flags
    is_deleted = Column(Boolean, nullable=False, default=False)
    is_dummy = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="medical_records")
    visit = relationship("Visit", back_populates="medical_records")

    def __repr__(self):
        return f"<MedicalRecord(uuid={self.record_uuid}, type={self.record_type})>"
    
    def to_export_dict(self):
        """Format rekam medis siap untuk ekspor ke Excel."""
        def val(v):
            if v is None or v == "":
                return "-"
            if isinstance(v, (datetime.datetime, datetime.date)):
                return v.strftime("%Y-%m-%d")
            return str(v)

        return {
            "ID Rekam Medis": self.id,
            "UUID": str(self.uuid),
            "Patient UUID": self.patient.patient_uuid if self.patient else "-",
            "Tanggal Catatan": val(self.notes_date),
            "Jenis Rekam": self.record_type or "-",
            "Nama Pasien": self.patient.nama if self.patient else "-",  # Already masked
            "Dokter": self.doctor_name or "-",
            "Keluhan": self.keluhan or "-",
            "Diagnosis Awal": self.diagnosis_awal or "-",
            "Diagnosis Akhir": self.diagnosis_akhir or "-",
            "Tindakan": self.tindakan or "-",
            "Obat": self.obat or "-",
            "Catatan Dokter": self.notes_doctor or "-",
            "Status": self.status or "-",
        }