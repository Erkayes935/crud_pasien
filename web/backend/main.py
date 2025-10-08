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
    dashboard_router, auth_router, patient_router, user_router,
    hospital_router, medical_record_router, claim_router, visit_router, resume_router, regulation_router, claim_note_router
)

# Init DB
Base.metadata.create_all(bind=engine)

# Init FastAPI
app = FastAPI(title="AI-Claim")
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Middleware
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET, same_site="lax", https_only=False)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Routers
app.include_router(dashboard_router.router, tags=["dashboard"])
app.include_router(auth_router.router, tags=["auth"])
app.include_router(patient_router.router, tags=["patients"])
app.include_router(user_router.router, tags=["users"])
app.include_router(hospital_router.router, tags=["hospitals"])
app.include_router(medical_record_router.router, tags=["medical_records"])
app.include_router(visit_router.router, tags=["visits"])
app.include_router(claim_router.router, tags=["claims"])
app.include_router(resume_router.router, tags=["resumes"])
app.include_router(regulation_router.router, tags=["regulations"])
app.include_router(claim_note_router.router)