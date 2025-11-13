"""
claim_router.py
Aggregator utama untuk seluruh endpoint klaim:
Doctor, Coder, Verifikator, AI, Regulation, Management, Notes, Export, dll.
"""

from fastapi import APIRouter

# Import semua sub-router modular dari folder `claim`
from .claim.claim_core_router import router as core_router
from .claim.claim_management_router import router as management_router
from .claim.claim_export_router import router as export_router
from .claim.claim_diagnosis_router import router as diagnosis_router
from .claim.claim_procedure_router import router as procedure_router
from .claim.claim_ai_router import router as ai_router
from .claim.claim_evaluation_router import router as evaluation_router
from .claim.claim_regulation_router import router as regulation_router
from .claim.claim_regulation_admin_router import router as regulation_admin_router
from .claim.claim_regulation_feedback_router import router as regulation_feedback_router
from .claim.claim_idrg_router import router as idrg_router
from .claim.claim_note_router import router as note_router
from .claim.claim_coder_router import router as coder_router

# Buat router utama
router = APIRouter(tags=["Claims"])

# Gabungkan semua subrouter

# 1️⃣ AI duluan (karena paling banyak overlap dengan endpoint umum)
router.include_router(ai_router, prefix="")

# 2️⃣ Baru manajemen & inti
router.include_router(management_router)
router.include_router(core_router)
router.include_router(export_router)

# 3️⃣ Diagnosis & prosedur
router.include_router(diagnosis_router)
router.include_router(procedure_router)

# 4️⃣ Evaluasi & regulasi
router.include_router(evaluation_router)
router.include_router(regulation_router)
router.include_router(regulation_admin_router)
router.include_router(regulation_feedback_router)

# 5️⃣ IDRG, Notes, Coder
router.include_router(idrg_router)
router.include_router(note_router)
router.include_router(coder_router)

# Final exported router
__all__ = ["router"]
