from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Numeric
)
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..base import Base, HousekeepingMixin


# =========================================
# AI RECOMMENDATIONS
# =========================================
class ClaimAIRecommendation(Base, HousekeepingMixin):
    """
    Menyimpan hasil rekomendasi awal dari AI
    (diagnosis / komorbid / komplikasi) per tahap klaim.
    """
    __tablename__ = "claim_ai_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    stage = Column(String(50), nullable=False)       # admission / daily / discharge
    category = Column(String(50), nullable=False)    # diagnosis / komorbid / komplikasi
    diagnosis_id = Column(Integer, ForeignKey("claim_diagnoses.id"), nullable=True)
    confidence_score = Column(Integer, nullable=True)
    child = Column(Boolean, server_default=text("false"))

    claim = relationship("Claim", back_populates="ai_recommendations")
    diagnosis = relationship("ClaimDiagnosis", foreign_keys=[diagnosis_id])

    @property
    def nama_kategori(self):
        return self.diagnosis.diagnosis_text if self.diagnosis else None

    @property
    def klinis(self):
        """Gabungan justifikasi / bukti / syarat klinis dari diagnosis."""
        if self.diagnosis:
            parts = [
                self.diagnosis.justifikasi_klinis,
                self.diagnosis.bukti_klinis,
                self.diagnosis.syarat_klinis,
            ]
            return " | ".join([p for p in parts if p])
        return None

    @property
    def icd10_code(self):
        return self.diagnosis.icd10_code if self.diagnosis else None


# =========================================
# AI SIMULATIONS
# =========================================
class ClaimSimulation(Base, HousekeepingMixin):
    """
    Menyimpan hasil simulasi AI per tahap klaim,
    termasuk pasangan diagnosis & tindakan yang dihasilkan.
    """
    __tablename__ = "claim_simulations"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    stage = Column(String, nullable=False)  # admission / daily / discharge

    diagnosis_utama_id = Column(Integer, ForeignKey("claim_diagnoses.id"), nullable=True)
    diagnosis_sekunder_id = Column(Integer, ForeignKey("claim_diagnoses.id"), nullable=True)
    tindakan_utama_id = Column(Integer, ForeignKey("claim_procedures.id"), nullable=True)
    tindakan_sekunder_id = Column(Integer, ForeignKey("claim_procedures.id"), nullable=True)

    # ====== Coder Verification ======
    coder_verified = Column(Boolean, default=False)
    coder_verified_by = Column(String)
    coder_verified_at = Column(DateTime)
    coder_notes = Column(Text)

    verified_icd10 = Column(String)
    verified_icd10_name = Column(Text)
    verified_icd9 = Column(String)
    verified_icd9_name = Column(Text)
    is_coder_approved = Column(Boolean, default=False)

    claim = relationship("Claim", back_populates="simulations")
    diagnosis_utama = relationship("ClaimDiagnosis", foreign_keys=[diagnosis_utama_id])
    diagnosis_sekunder = relationship("ClaimDiagnosis", foreign_keys=[diagnosis_sekunder_id])
    tindakan_utama = relationship("ClaimProcedure", foreign_keys=[tindakan_utama_id])
    tindakan_sekunder = relationship("ClaimProcedure", foreign_keys=[tindakan_sekunder_id])


# =========================================
# AI COMBINATION ALTERNATIVES
# =========================================
class ClaimCombinationAlternative(Base, HousekeepingMixin):
    """
    Menyimpan kombinasi alternatif hasil analisis AI
    (hasil penggabungan diagnosis + tindakan untuk perbandingan iDRG/INA-CBG).
    """
    __tablename__ = "claim_combination_alternatives"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    kombinasi_nama = Column(String(255))
    severity = Column(Text)
    kode_ina_cbg = Column(String(50))
    estimasi_tarif = Column(Numeric(18, 2))
    syarat_klinis = Column(Text)
    faskes = Column(Text)
    rawat_inap = Column(Text)
    tindakan_wajib = Column(Text)

    claim = relationship("Claim", back_populates="combination_alternatives")

    def __repr__(self):
        return f"<ClaimCombinationAlternative(claim_id={self.claim_id}, cbg={self.kode_ina_cbg})>"
