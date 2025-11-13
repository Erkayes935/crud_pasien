from sqlalchemy import (
    Column, Integer, String, Text, Boolean, ForeignKey, DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from ..base import Base, HousekeepingMixin
from datetime import datetime


# =========================================
# CLAIM PROCEDURE
# =========================================
class ClaimProcedure(Base, HousekeepingMixin):
    """
    Menyimpan daftar tindakan/prosedur medis dalam klaim.
    Bisa dikaitkan dengan diagnosis tertentu atau hasil evaluasi AI.
    """
    __tablename__ = "claim_procedures"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    procedure_source = Column(String(50), default="manual")
    procedure_text = Column(Text, nullable=False)
    icd9_code = Column(String(20))
    requirement_flag = Column(Boolean, server_default=text("false"))
    stage = Column(String(50), default="admission")  # admission / daily / discharge
    icd9_final_by_coder = Column(String(20))
    verified_by = Column(String(100))
    verified_at = Column(DateTime)

    claim = relationship("Claim", back_populates="procedures")
    procedure_details = relationship(
        "ClaimProcedureDetail", back_populates="procedure", cascade="all, delete-orphan"
    )

    @property
    def description(self):
        if self.procedure_details:
            return self.procedure_details[0].description
        return None


# =========================================
# CLAIM PROCEDURE DETAIL
# =========================================
class ClaimProcedureDetail(Base, HousekeepingMixin):
    """
    Detail tambahan setiap tindakan, termasuk validitas,
    dampak INA-CBG, dan persyaratan klinis.
    """
    __tablename__ = "claim_procedure_details"

    id = Column(Integer, primary_key=True, index=True)
    procedure_id = Column(Integer, ForeignKey("claim_procedures.id"), nullable=False)
    icd9_tindakan = Column(String, nullable=False)
    validitas_tindakan = Column(String)
    status_tindakan = Column(String)
    ina_cbg_tindakan = Column(Text)
    faskes_tindakan = Column(Text)
    rawat_inap_tindakan = Column(Text)
    syarat_klinis_tindakan = Column(Text)
    deskripsi_tindakan = Column(Text)
    aspek_lainnya = Column(Text)

    procedure = relationship("ClaimProcedure", back_populates="procedure_details")

    @property
    def description(self):
        parts = [
            f"ICD-9: {self.icd9_tindakan}" if self.icd9_tindakan else "",
            f"Status: {self.status_tindakan}" if self.status_tindakan else "",
            f"INA-CBG: {self.ina_cbg_tindakan}" if self.ina_cbg_tindakan else "",
        ]
        return ", ".join([p for p in parts if p])
