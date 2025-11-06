"""Module: backend.models
This module only imports and exposes all ORM models
from the modularized structure under `models/`.
"""

# backend/models/__init__.py
from .base import Base, HousekeepingMixin
from .hospital import Hospital
from .patient import Patient
from .visit import Visit
from .medical_record import MedicalRecord, MedicalRecordLog
from .user_management import User, Role, UserRole
from .rule_engine import RulesMaster, RegionalReports
from .claim import *  # noqa

__all__ = [
    "Base",
    "HousekeepingMixin",
    "Hospital",
    "Patient",
    "Visit",
    "MedicalRecord",
    "MedicalRecordLog",
    "User",
    "Role",
    "UserRole",
    "RulesMaster",
    "RegionalReports",
]