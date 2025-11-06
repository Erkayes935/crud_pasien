from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from ..base import Base, HousekeepingMixin


# =========================================
# CLAIM TARIFF (INA-CBG)
# =========================================
class ClaimTariff(Base, HousekeepingMixin):
    """
    Menyimpan hasil grouping tarif INA-CBG berdasarkan kombinasi diagnosis & tindakan.
    """
    __tablename__ = "claim_tariffs"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    cbg_code = Column(String(50))
    description = Column(Text)
    tariff_amount = Column(Integer)
    status = Column(String(20), default="draft")  # draft / final

    claim = relationship("Claim", back_populates="tariffs")

    def __repr__(self):
        return f"<ClaimTariff(claim_id={self.claim_id}, cbg={self.cbg_code})>"
