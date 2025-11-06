"""
backend.main - FastAPI entrypoint
Fokus: init app, middleware, static, dan register routers.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from . import config
from .database import engine, Base
from .routers import (
    dashboard_router,
    auth_router,
    patient_router,
    user_router,
    hospital_router,
    medical_record_router,
    visit_router,
    resume_router,
    ai_meta_router,
    export_router,
)

from .routers.claim import (
    claim_core_router,
    claim_diagnosis_router,
    claim_procedure_router,
    claim_ai_router,
    claim_evaluation_router,
    claim_regulation_router,
    claim_regulation_admin_router,
    claim_regulation_feedback_router,
    claim_management_router,
    claim_export_router,
    claim_idrg_router,
    claim_note_router,
    claim_coder_router,
)

# 🧱 Import error handler terpusat
from .error_handlers import register_error_handlers

# ======================================================
# Init Database
# ======================================================
Base.metadata.create_all(bind=engine)

# ======================================================
# Init FastAPI App
# ======================================================
app = FastAPI(title="AI-Claim", version="2.0", openapi_tags=[
    {"name": "Claims", "description": "Semua endpoint terkait klaim (AI, regulation, coder, dsb)."},
])

# Static files (pastikan folder sesuai)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# ======================================================
# Middleware
# ======================================================
app.add_middleware(SessionMiddleware,
    secret_key=config.SESSION_SECRET,
    same_site="lax",
    https_only=False
)
app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
@app.get("/force-error")
def force_error():
    raise Exception("Testing 500 handler")
# ======================================================
# Routers
# ======================================================

# 🏠 Dashboard (berisi route "/dashboard" dan root "/")
app.include_router(dashboard_router.router, prefix="", tags=["dashboard"])

# 🧠 Klaim (modular, semua prefix dimulai dari /claims)
from .routers.claim_router import router as claim_router
app.include_router(claim_router, prefix="/claims", tags=["claims"])

# 🩺 Coder (verifikasi ICD)
from .routers.claim import claim_coder_router
app.include_router(claim_coder_router, prefix="/claims", tags=["coder"])

# 🔹 Router lain
app.include_router(auth_router.router, tags=["auth"])
app.include_router(patient_router.router, tags=["patients"])
app.include_router(user_router.router, tags=["users"])
app.include_router(hospital_router.router, tags=["hospitals"])
app.include_router(medical_record_router.router, tags=["medical_records"])
app.include_router(visit_router.router, tags=["visits"])
app.include_router(resume_router.router, tags=["resumes"])
app.include_router(ai_meta_router.router, tags=["ai-meta"])
app.include_router(export_router.router, tags=["export"])

# ======================================================
# Global Error Handlers
# ======================================================
register_error_handlers(app)