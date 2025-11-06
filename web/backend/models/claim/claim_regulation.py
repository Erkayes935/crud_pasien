from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from ..base import Base, HousekeepingMixin


# =========================================
# CLAIM REGULATION DETAIL
# =========================================
class ClaimRegulationDetail(Base, HousekeepingMixin):
    """
    Menyimpan detail regulasi yang berlaku untuk item klaim tertentu.
    Bisa terhubung ke diagnosis, procedure, evaluation, maupun i-DRG summary.
    """
    __tablename__ = "claim_regulation_details"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    # entitas sumber regulasi
    diagnosis_id = Column(Integer, ForeignKey("claim_diagnoses.id"), nullable=True)
    procedure_id = Column(Integer, ForeignKey("claim_procedures.id"), nullable=True)
    diagnosis_evaluation_id = Column(Integer, ForeignKey("claim_diagnosis_evaluations.id"), nullable=True)
    procedure_evaluation_id = Column(Integer, ForeignKey("claim_procedure_evaluations.id"), nullable=True)
    idrg_diagnosis_id = Column(Integer, ForeignKey("claim_idrg_diagnosis.id"), nullable=True)
    idrg_summary_id = Column(Integer, ForeignKey("claim_idrg_summary.id"), nullable=True)

    entry_field = Column(String(100), nullable=True)  # contoh: "syarat_klinis", "justifikasi", "icd10_code"
    judul_regulasi = Column(String(255), nullable=False)  # contoh: PNPK Sepsis 2020
    dasar_hukum = Column(String(255))  # contoh: Permenkes, PNPK, ICD-10, INA-CBG
    isi = Column(Text)  # isi/penjelasan regulasi

    claim = relationship("Claim", back_populates="regulation_details")

    # hubungan opsional lintas domain
    diagnosis = relationship("ClaimDiagnosis")
    procedure = relationship("ClaimProcedure")
    diagnosis_evaluation = relationship("ClaimDiagnosisEvaluation")
    procedure_evaluation = relationship("ClaimProcedureEvaluation")
    idrg_diagnosis = relationship("ClaimIDRGDiagnosis")
    idrg_summary = relationship("ClaimIDRGSummary")

    def __repr__(self):
        return f"<ClaimRegulationDetail(claim_id={self.claim_id}, judul={self.judul_regulasi})>"
