"""
Module: backend.models
This module only imports and exposes all ORM models
from the modularized structure under `models/`.
"""

# base database metadata
from .base import Base, HousekeepingMixin

# master data
from .hospital import Hospital
from .patient import Patient
from .visit import Visit
from .medical_record import MedicalRecord, MedicalRecordLog
from .user_management import User, Role, UserRole
from .rule_engine import RulesMaster, RegionalReports

# claim modular models
from .claim import (
    Claim,
    ClaimGroup,
    ClaimVisitLink,
    ClaimLog,
    ClaimNote,
    ClaimDiagnosis,
    ClaimProcedure,
    ClaimProcedureDetail,
    ClaimAIRecommendation,
    ClaimSimulation,
    ClaimCombinationAlternative,
    ClaimDiagnosisEvaluation,
    ClaimProcedureEvaluation,
    ClaimRegulationDetail,
    ClaimIDRGDiagnosis,
    ClaimIDRGSummary,
    ClaimTariff,
)

# INA-CBG models
from .inacbg import INACBGTariff
