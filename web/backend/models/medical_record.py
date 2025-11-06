from sqlalchemy import (
    Column, Integer, String, Text, Boolean, ForeignKey,
    Date, DateTime
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from sqlalchemy import inspect
from datetime import datetime, date
from .base import Base, HousekeepingMixin
import uuid


# =========================================
# Medical Record
# =========================================
class MedicalRecord(Base, HousekeepingMixin):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)

    record_type = Column(String(50), nullable=False)  # admission / daily / discharge
    is_final = Column(Boolean, nullable=False, server_default=text("false"))
    notes_date = Column(Date, nullable=False, default=datetime.utcnow)

    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_name = Column(String(100), nullable=False)

    # Riwayat
    riwayat_penyakit = Column(Text)
    riwayat_pengobatan = Column(Text)
    riwayat_operasi = Column(Text)
    alergi = Column(Text)
    keluhan = Column(Text)
    gejala_lain = Column(Text)

    # Pemeriksaan Fisik
    tekanan_darah = Column(String(100))
    nadi = Column(String(100))
    pernapasan = Column(String(100))
    suhu = Column(String(100))
    spo2 = Column(String(100))
    berat_badan = Column(String(100))
    tinggi_badan = Column(String(100))

    # Lab & Penunjang
    hemoglobin = Column(String(100))
    leukosit = Column(String(100))
    trombosit = Column(String(100))
    gula_darah = Column(String(100))
    creatinin = Column(String(100))
    rontgen_thorax = Column(Text)
    ct_scan = Column(Text)
    usg = Column(Text)

    # Diagnosis & Tindakan
    diagnosis_awal = Column(Text)
    komorbid = Column(Text)
    komplikasi = Column(Text)
    diagnosis_akhir = Column(Text)
    tindakan = Column(Text)

    # Obat & Catatan
    obat = Column(Text)
    validasi_fornas = Column(Text)
    notes_doctor = Column(Text)

    # Relasi
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=False)

    patient = relationship("Patient", back_populates="medical_records", foreign_keys=[patient_id])
    visit = relationship("Visit", back_populates="medical_records", foreign_keys=[visit_id])
    doctor = relationship("User", back_populates="medical_records", foreign_keys=[doctor_id])
    claim = relationship("Claim", back_populates="medical_record", uselist=False)
    logs = relationship("MedicalRecordLog", back_populates="medical_record", cascade="all, delete-orphan")

    def to_dict(self):
        def normalize(val):
            if isinstance(val, uuid.UUID):
                return str(val)
            if isinstance(val, (datetime, date)):
                return val.isoformat()
            return val
        return {c.key: normalize(getattr(self, c.key)) for c in inspect(self).mapper.column_attrs}

    def to_export_dict(self):
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


# =========================================
# Medical Record Logs (Audit Trail)
# =========================================
class MedicalRecordLog(Base, HousekeepingMixin):
    __tablename__ = "medical_record_logs"

    id = Column(Integer, primary_key=True, index=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    data_snapshot = Column(JSONB, nullable=True)
    action = Column(String(50), nullable=False)  # created / updated / finalized / rejected / recalculated
    description = Column(Text)
    updated_by = Column(Integer, ForeignKey("users.id"))

    medical_record = relationship("MedicalRecord", back_populates="logs")
    user = relationship("User", back_populates="medical_record_logs")
