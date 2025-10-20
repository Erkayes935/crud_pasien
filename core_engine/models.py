"""
Module: models

Model RulesMaster untuk core_engine agar bisa akses rules dari database.
"""

from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime, Boolean, Enum, JSON, Float, text, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime
from database_connection import Base

class RulesMaster(Base):
    __tablename__ = "rules_master"

    id = Column(Integer, primary_key=True, index=True)
    diagnosis = Column(Text, nullable=False)       # Nama diagnosis: "Pneumonia", "DM Tipe 2", dll
    field = Column(Text, nullable=False)           # Field aturan: "rawat_inap.lama_rawat", dll
    layer = Column(Text, nullable=False)           # Layer: "permenkes", "nasional", "ppk", "regional", "rs", "bridging", "fraud", "temporary"
    isi = Column(Text, nullable=False)             # Isi aturan: "LOS ≥ 2 hari", dll
    sumber = Column(Text, nullable=True)           # Sumber: "PNPK Pneumonia 2023", "PPK RS Notopuro 2024", dll
    pdf_file = Column(Text, nullable=True)         # Nama file PDF: "ppk_hipertensi_2024.pdf", null jika tidak ada
    rs_id = Column(Text, nullable=True)            # ID RS: "rs_notopuro", null untuk rules global
    region_id = Column(Text, nullable=True)        # ID wilayah: "jatim", null untuk rules global
    status = Column(Text, nullable=False, default="unverified")  # Status: "unverified", "official", "active", "rejected"
    created_by = Column(Text, nullable=True)       # Pembuat: "admin_rs_notopuro", "ai_meta_admin", dll
    approved_by = Column(Text, nullable=True)      # Yang approve: "ai_meta_reviewer_1", dll
    approved_date = Column(DateTime, nullable=True) # Tanggal approval
    review_notes = Column(Text, nullable=True)     # Catatan reviewer AI META
    feedback = Column(Text, nullable=True)         # Feedback dari RS tentang aturan ini
    feedback_by = Column(Text, nullable=True)      # Yang beri feedback: "admin_rs_notopuro", dll
    feedback_date = Column(DateTime, nullable=True) # Tanggal feedback
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"), onupdate=text("now()"))
    scope = Column(String(50), nullable=True)       # diagnosis / tindakan / idrg / kombinasi / umum
    procedure = Column(Text, nullable=True)         # nama tindakan, misal 'X-Ray Thorax', 'Antibiotik IV'

    def __repr__(self):
        return f"<RulesMaster(id={self.id}, diagnosis={self.diagnosis}, layer={self.layer}, status={self.status})>"