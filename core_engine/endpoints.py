# core_engine/endpoints.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import asyncio

# import services
from services.predict_ddx_service import process_predict_ddx
from services.analyze_diagnosis_service import process_analyze_diagnosis
from services.analyze_claim_service import process_analyze_claim
from services.generate_claim_combos_service import process_generate_claim_combos

router = APIRouter()

# ---------------------------
# Input Schemas
# ---------------------------
class RMSummary(BaseModel):
    patient_uuid: str
    visit_uuid: str
    keluhan: str | None = None
    diagnosis_akhir: str | None = None
    tindakan: str | None = None
    obat: str | None = None

class ClaimEvalInput(BaseModel):
    primary: str
    secondary: List[str] = []
    procedures: List[str] = []

class DiagnosisInput(BaseModel):
    diagnosis_text: str

# ---------------------------
# Endpoints
# ---------------------------

@router.post("/predict_ddx")
async def predict_ddx(data: RMSummary):
    await asyncio.sleep(1)
    return process_predict_ddx(data)

@router.post("/analyze_diagnosis")
async def analyze_diagnosis(data: DiagnosisInput):
    await asyncio.sleep(1)
    return process_analyze_diagnosis(data)

@router.post("/analyze_claim")
async def analyze_claim(data: ClaimEvalInput):
    await asyncio.sleep(1)
    return process_analyze_claim(data)

@router.post("/generate_claim_combos")
async def generate_claim_combos(data: RMSummary):
    await asyncio.sleep(1)
    return process_generate_claim_combos(data)
