# core_engine/endpoints.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import asyncio

# import services
from services.predict_ddx_service import process_predict_ddx
from services.analyze_diagnosis_service import process_analyze_diagnosis
from services.analyze_procedure_service import process_analyze_procedure
from services.generate_claim_combos_service import process_generate_claim_combos, process_generate_alternatives
from services.resume_service import process_resume_medis
from services.regulation_service import process_regulation_detail
from services.idrg_service import predict_idrg

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
    """
    Generate evaluasi diagnosis dan tindakan tanpa alternatif kombinasi.
    
    Expects: {
      "claim_id": int,
      "primary_claim": str,
      "secondary_claims": list[str],
      "primary_action": str,
      "secondary_actions": list[str]
    }
    
    Returns: {
      "evaluasi_diagnosis": {...},
      "evaluasi_tindakan": {...},
      "alternatif": [],  # Kosong, akan diisi melalui request terpisah
      "engine_version": str
    }
    """
    result = process_generate_claim_combos(payload)
    return result

@router.post("/generate_alternatives")
async def generate_alternatives(payload: dict):
    """
    Generate hanya alternatif kombinasi diagnosis-tindakan.
    
    Expects: {
      "claim_id": int,
      "primary_claim": str,
      "secondary_claims": list[str],
      "primary_action": str,
      "secondary_actions": list[str]
    }
    
    Returns: {
      "alternatif": [
        {
          "judul": str,
          "catatan": str,
          "syarat": str,
          "tindakan": list[str]
        },
        ...
      ],
      "engine_version": str
    }
    """
    result = process_generate_alternatives(payload)
    return result

@router.post("/resume_medis")
async def generate_resume(input_data: ResumeInput):
    return process_resume_medis(input_data.dict(), mode=input_data.mode, settings=input_data.settings or {})

@router.post("/regulation_detail")
async def regulation_detail(payload: dict):
    field = payload.get("field", "")
    return process_regulation_detail(payload, field)

@router.post("/predict_idrg")
async def predict_idrg_endpoint(payload: dict):
    """
    Endpoint untuk prediksi i-DRG (single atau combo)
    
    Expects:
      - payload["mode"] = "single" | "combo"  
      - payload = data sesuai mode dari frontend
    
    Returns:
      - JSON prediksi i-DRG + engine_version
    """
    mode = payload.get("mode", "single")
    print(f"[CORE_ENGINE] Predicting i-DRG mode: {mode}")
    out = predict_idrg(mode, payload)
    return out

