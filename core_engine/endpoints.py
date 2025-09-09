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
from services.resume_service import process_resume_medis

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


class ResumeInput(BaseModel):
    pasien: dict
    visit: dict
    diagnosis: dict
    tindakan: dict
    obat: list = []
    regulasi: list = []
    dokter: dict
    mode: str = "list"
    settings: dict = {}

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

@router.post("/resume_medis")
async def generate_resume(input_data: ResumeInput):
    return process_resume_medis(input_data.dict(), mode=input_data.mode, settings=input_data.settings or {})
