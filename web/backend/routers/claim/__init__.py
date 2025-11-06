"""
routers/claim/__init__.py
Menggabungkan semua sub-router klaim agar bisa di-import sekaligus dari main.py
"""

from .claim_core_router import router as claim_core_router
from .claim_management_router import router as claim_management_router
from .claim_export_router import router as claim_export_router
from .claim_diagnosis_router import router as claim_diagnosis_router
from .claim_procedure_router import router as claim_procedure_router
from .claim_ai_router import router as claim_ai_router
from .claim_evaluation_router import router as claim_evaluation_router
from .claim_regulation_router import router as claim_regulation_router
from .claim_regulation_admin_router import router as claim_regulation_admin_router
from .claim_regulation_feedback_router import router as claim_regulation_feedback_router
from .claim_idrg_router import router as claim_idrg_router
from .claim_note_router import router as claim_note_router   # ✅ notes ikut disatukan
from .claim_coder_router import router as claim_coder_router

__all__ = [
    "claim_core_router",
    "claim_management_router",
    "claim_export_router",
    "claim_diagnosis_router",
    "claim_procedure_router",
    "claim_ai_router",
    "claim_evaluation_router",
    "claim_regulation_router",
    "claim_regulation_admin_router",
    "claim_regulation_feedback_router",
    "claim_idrg_router",
    "claim_note_router",
    "claim_coder_router",
]
