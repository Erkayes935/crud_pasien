from sqlalchemy import Column, Integer, Text, DateTime, Boolean, text
from .base import Base, HousekeepingMixin

class RulesMaster(Base, HousekeepingMixin):
    __tablename__ = "rules_master"

    id = Column(Integer, primary_key=True, index=True)
    diagnosis = Column(Text, nullable=False)
    field = Column(Text, nullable=False)
    layer = Column(Text, nullable=False)
    isi = Column(Text, nullable=False)
    sumber = Column(Text)
    pdf_file = Column(Text)
    rs_id = Column(Text)
    region_id = Column(Text)
    status = Column(Text, nullable=False, default="unverified")
    created_by = Column(Text)
    approved_by = Column(Text)
    approved_date = Column(DateTime)
    review_notes = Column(Text)
    feedback = Column(Text)
    feedback_by = Column(Text)
    feedback_date = Column(DateTime)

    def __repr__(self):
        return f"<RulesMaster(id={self.id}, diagnosis={self.diagnosis}, layer={self.layer}, status={self.status})>"


class RegionalReports(Base, HousekeepingMixin):
    __tablename__ = "regional_reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    se_file = Column(Text, nullable=False)
    region_id = Column(Text, nullable=False)
    rs_id = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="pending")
    reported_by = Column(Text, nullable=False)
    reviewed_by = Column(Text)
    reviewed_date = Column(DateTime)
    review_notes = Column(Text)
    converted_rules_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<RegionalReports(id={self.id}, title={self.title}, status={self.status})>"
