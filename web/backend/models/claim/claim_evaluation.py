from sqlalchemy import (
    Column, Integer, String, Text, Enum, ForeignKey, DateTime, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from ..base import Base, HousekeepingMixin


# =========================================
# DIAGNOSIS EVALUATION
# =========================================
class ClaimDiagnosisEvaluation(Base, HousekeepingMixin):
    """
    Hasil evaluasi AI atau sistem rule terhadap diagnosis.
    Menyimpan validitas, severity, dan informasi grouping INA-CBG.
    """
    __tablename__ = "claim_diagnosis_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))

    validitas = Column(
        Enum("valid", "invalid", "warning", name="eval_status"), nullable=True
    )
    validitas_detail = Column(Text)
    severity = Column(Text)
    kode_ina_cbg = Column(Text)
    estimasi_tarif = Column(Numeric(18, 2))
    syarat_klinis = Column(Text)
    evaluasi_faskes = Column(Text)
    rawat_inap = Column(Text)

    claim = relationship("Claim", back_populates="diagnosis_evaluations")

    def __repr__(self):
        return f"<ClaimDiagnosisEvaluation(claim_id={self.claim_id}, validitas={self.validitas})>"


# =========================================
# PROCEDURE EVALUATION
# =========================================
class ClaimProcedureEvaluation(Base, HousekeepingMixin):
    """
    Hasil evaluasi AI terhadap tindakan/procedure.
    Bisa mencakup wajib/tidaknya tindakan, validasi, dampak tarif, dan konflik antar tindakan.
    """
    __tablename__ = "claim_procedure_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))

    wajib = Column(Text)
    validasi = Column(Text)
    dampak = Column(Text)
    konflik = Column(Text)

    claim = relationship("Claim", back_populates="procedure_evaluations")

    def __repr__(self):
        return f"<ClaimProcedureEvaluation(claim_id={self.claim_id})>"

# =========================================
# COMBO EVALUATION
# =========================================
class ClaimComboEvaluation(Base):
    __tablename__ = "claim_combo_evaluations"
    id = Column(Integer, primary_key=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    aspek_lainnya = Column(Text)
    claim = relationship("Claim", back_populates="combo_evaluations")