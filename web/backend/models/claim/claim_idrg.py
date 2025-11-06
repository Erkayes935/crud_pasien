from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime
)
from sqlalchemy.orm import relationship
from datetime import datetime
from ..base import Base, HousekeepingMixin


# =========================================
# i-DRG DIAGNOSIS
# =========================================
class ClaimIDRGDiagnosis(Base, HousekeepingMixin):
    """
    Hasil grouping i-DRG per diagnosis.
    Disimpan per modal detail diagnosis (bisa beberapa per klaim).
    """
    __tablename__ = "claim_idrg_diagnosis"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    group_idrg = Column(String(50))
    severity_index = Column(String(50))
    checklist = Column(Text)
    faktor_severity = Column(Text)
    ungroupable_alert = Column(Text)
    simulasi_tarif = Column(String(50))
    gap_analysis = Column(String(50))

    claim = relationship("Claim")

    def __repr__(self):
        return f"<ClaimIDRGDiagnosis(claim_id={self.claim_id}, group={self.group_idrg})>"


# =========================================
# i-DRG SUMMARY
# =========================================
class ClaimIDRGSummary(Base, HousekeepingMixin):
    """
    Ringkasan hasil kombinasi i-DRG per klaim.
    Disusun oleh verifikator sebagai hasil akhir grouping.
    """
    __tablename__ = "claim_idrg_summary"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    group_idrg_kombinasi = Column(String(50))
    severity_kombinasi = Column(Text)
    checklist_kombinasi = Column(Text)
    faktor_severity = Column(Text)
    risiko_ungroupable = Column(Text)
    estimasi_tarif = Column(String(50))
    gap_inacbg_vs_idrg = Column(String(50))
    rekomendasi_ai = Column(Text)

    claim = relationship("Claim")

    def __repr__(self):
        return f"<ClaimIDRGSummary(claim_id={self.claim_id}, group={self.group_idrg_kombinasi})>"
