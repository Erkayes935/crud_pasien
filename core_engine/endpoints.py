# core_engine/endpoints.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import asyncio

# import services
from services.predict_ddx_service import process_predict_ddx
from services.analyze_diagnosis_service import process_analyze_diagnosis
from services.analyze_procedure_service import process_analyze_procedure
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
async def predict_ddx(payload: dict):
    """
    Expects: { "global_record": {...}, "stage": "admission"|"daily"|"discharge", ... }
    Backward-compat: { "rekam_medis": [ {...} ] }
    Returns: { "diagnosis": [...], "komorbid": [...], "komplikasi": [...], "engine_version": ... }
    """
    print(f"[CORE_ENGINE] Payload diterima di /predict_ddx: {payload}")
    out = process_predict_ddx(payload)
    # engine_version set by service, fallback if missing
    if "engine_version" not in out:
        from datetime import date
        out["engine_version"] = f"predict_ddx@{date.today().isoformat()}"
    return out


@router.post("/analyze_diagnosis")
async def analyze_diagnosis(payload: dict):
    """
    Expects: { "claim_id": int, "disease_name": str, "rekam_medis": [ {...} ] }
    Returns: JSON detail + engine_version
    """
    out = process_analyze_diagnosis(payload)
    from datetime import date
    out["engine_version"] = f"analyze_diagnosis@{date.today().isoformat()}"
    return out

@router.post("/analyze_procedure")
async def analyze_procedure(payload: dict):
    await asyncio.sleep(1)
    return process_analyze_procedure(payload)

@router.post("/generate_claim_combos")
async def generate_claim_combos(payload: dict):
    result = process_generate_claim_combos(payload)
    return result

@router.post("/resume_medis")
async def generate_resume(input_data: ResumeInput):
    return process_resume_medis(input_data.dict(), mode=input_data.mode, settings=input_data.settings or {})
