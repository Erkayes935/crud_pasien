from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, DateTime, Boolean, func, text

Base = declarative_base()
Base.__allow_unmapped__ = True  # ✅ global bypass

class HousekeepingMixin:
    """Default housekeeping fields for all tables."""
    __allow_unmapped__ = True
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    is_dummy = Column(Boolean, nullable=False, server_default=text("false"))
