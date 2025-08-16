from sqlalchemy import Column, Integer, String, Date, Text
from .database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String(100), nullable=False)
    tanggal_lahir = Column(Date, nullable=False)
    tanggal_kunjungan = Column(Date, nullable=False)
    diagnosis = Column(Text)
    tindakan = Column(Text)
    dokter = Column(String(100))
