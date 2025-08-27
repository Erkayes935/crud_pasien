"""
Module: backend.models

Defines the SQLAlchemy ORM models used by the application:
- Patient: stores patient personal information only.
- Claim: stores visit/claim information linked to a patient.
- User: stores application users linked to Auth0 via `auth0_sub` and a role.
- Hospital: stores hospital information, as root entity for grouping users & patients.
- Visit: stores visit information linked to a patient.
"""

from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    kode_hospital = Column(String(20), unique=True, nullable=True)
    nama = Column(String(150), nullable=True)
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
    admin = relationship("User", back_populates="hospital_admin", foreign_keys=[admin_id])
    patients = relationship("Patient", back_populates="hospital", cascade="all, delete-orphan")
    visits = relationship("Visit", back_populates="hospital", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="hospital", cascade="all, delete-orphan")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
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
    hospital = relationship("Hospital", back_populates="patients")
    # Relasi: 1 pasien → banyak kunjungan
    visits = relationship("Visit", back_populates="patient", cascade="all, delete-orphan")
    # Relasi: 1 pasien → banyak klaim
    claims = relationship("Claim", back_populates="patient", cascade="all, delete-orphan")
    created_at = Column(DateTime, default=datetime.utcnow)


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    tanggal_kunjungan = Column(Date, nullable=True)
    tanggal_claim = Column(Date, nullable=True)
    dokter = Column(String(100), nullable=True)
    diagnosis_awal = Column(Text)
    kode_icd = Column(String(20))
    tindakan = Column(Text)
    obat = Column(Text)
    status = Column(String(50), default="draft")
    hasil = Column(Text)

    # Relasi ke pasien
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    patient = relationship("Patient", back_populates="claims")

    # Relasi ke visit
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=True)
    visit = relationship("Visit", back_populates="claims")

    # Relasi ke rumah sakit
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    hospital = relationship("Hospital", back_populates="claims")

    # Relasi ke user (siapa yg buat klaim)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    creator = relationship("User", back_populates="claims")


class Visit(Base):
    __tablename__ = "visits"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    eksternal_id = Column(String(100), nullable=True)
    sumber = Column(String(100), nullable=True)
    tanggal_kunjungan = Column(Date, nullable=True)
    jenis_kunjungan = Column(String(100), nullable=True)
    poli = Column(String(100), nullable=True)
    dokter = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relasi ke pasien
    patient = relationship("Patient", back_populates="visits")
    # Relasi ke rumah sakit
    hospital = relationship("Hospital", back_populates="visits")
    # Relasi ke klaim
    claims = relationship("Claim", back_populates="visit", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    auth0_sub = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False, default="doctor")
    password = Column(String, nullable=True)
    jabatan = Column(String, nullable=True)
    dokter_id = Column(String, nullable=True)

    # kalau dia admin_rs, relasinya ke hospital
    hospital_admin = relationship("Hospital", back_populates="admin", uselist=False, foreign_keys=[Hospital.admin_id])

    # Relasi: 1 user bisa bikin banyak klaim
    claims = relationship("Claim", back_populates="creator")
