from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from ..base import Base, HousekeepingMixin


# =========================================
# CLAIM DIAGNOSIS
# =========================================
class ClaimDiagnosis(Base, HousekeepingMixin):
    """
    Menyimpan daftar diagnosis (utama, sekunder, komorbid, komplikasi)
    yang diklaim pada pasien.
    """
    __tablename__ = "claim_diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    diagnosis_type = Column(String(50), nullable=False)  # utama / sekunder / komorbid / komplikasi
    diagnosis_text = Column(Text, nullable=False)
    diagnosis_source = Column(String(50), default="manual")  # ai / manual
    icd10_code = Column(String(20))
    justifikasi_klinis = Column(Text)
    syarat_klinis = Column(Text)
    bukti_klinis = Column(Text)
    tingkat_faskes = Column(Text)
    justifikasi_faskes = Column(Text)
    kompetensi_faskes = Column(Text)
    kode_ganda_icd10 = Column(Text)
    z_code_icd10 = Column(Text)
    kode_bpjs_khusus_icd10 = Column(Text)
    klinis = Column(Text)
    lama_rawat_inap = Column(Text)
    kriteria_rawat_inap = Column(Text)
    indikasi_rawat_inap = Column(Text)
    indikasi_rujukan = Column(Text)
    kriteria_rujukan = Column(Text)
    tujuan_rujukan = Column(Text)

    claim = relationship("Claim", back_populates="diagnoses")

    def __repr__(self):
        return f"<ClaimDiagnosis(type={self.diagnosis_type}, icd10={self.icd10_code})>"
