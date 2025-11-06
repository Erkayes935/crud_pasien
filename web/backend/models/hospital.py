from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base, HousekeepingMixin
import uuid

class Hospital(Base, HousekeepingMixin):
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
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    admin = relationship("User", back_populates="admin_of_hospital", foreign_keys=[admin_id])
    patients = relationship("Patient", back_populates="hospital", foreign_keys="Patient.hospital_id")
    visits = relationship("Visit", back_populates="hospital", foreign_keys="Visit.hospital_id")
    claims = relationship("Claim", back_populates="hospital", foreign_keys="Claim.hospital_id")
    users = relationship("User", back_populates="hospital", foreign_keys="User.hospital_id")
