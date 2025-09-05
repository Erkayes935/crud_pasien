# core_engine/endpoints.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import asyncio
import random

router = APIRouter()

# ---------------------------
# Input Schemas
# ---------------------------
class RMSummary(BaseModel):
    patient_uuid: str
    visit_uuid: str
    keluhan: str | None = None
    riwayat_penyakit: str | None = None
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
    return {
        "diagnosis": [
            {
                "kategori": "Diagnosis",
                "klinis": "Demam Berdarah Dengue",
                "icd": "A91",
                "score": 0.92,
                "tindakan": "Infus cairan, monitoring laboratorium",
                "detail_modal": {
                    "aspek_klinis": ["Demam tinggi 3-5 hari", "Trombosit menurun", "Nyeri kepala"],
                    "tindakan_disarankan": ["Cairan IV", "Monitoring Ht & Trombosit"],
                    "referensi": {"PNPK": "PNPK-DBD-2022", "Fornas": "FORNAS-2023", "Permenkes": "PMK 52/2016"}
                }
            },
            {
                "kategori": "Diagnosis",
                "klinis": "Tifoid",
                "icd": "A01.0",
                "score": 0.75,
                "tindakan": "Antibiotik, monitoring suhu",
                "detail_modal": {}
            },
            {
                "kategori": "Diagnosis",
                "klinis": "Infeksi Virus Nonspesifik",
                "icd": "B34.9",
                "score": 0.60,
                "tindakan": "Observasi, istirahat cukup",
                "detail_modal": {}
            }
        ],
        "komorbid": [
            {
                "kategori": "Komorbid",
                "klinis": "Hipertensi",
                "icd": "I10",
                "score": 0.65,
                "tindakan": "Kontrol tekanan darah",
                "detail_modal": {}
            },
            {
                "kategori": "Komorbid",
                "klinis": "Diabetes Mellitus",
                "icd": "E11",
                "score": 0.58,
                "tindakan": "Kontrol gula darah",
                "detail_modal": {}
            },
            {
                "kategori": "Komorbid",
                "klinis": "Penyakit Ginjal Kronis",
                "icd": "N18",
                "score": 0.40,
                "tindakan": "Monitoring fungsi ginjal",
                "detail_modal": {}
            }
        ],
        "komplikasi": [
            {
                "kategori": "Komplikasi",
                "klinis": "Syok Dengue",
                "icd": "A91.1",
                "score": 0.55,
                "tindakan": "Resusitasi cairan",
                "detail_modal": {}
            },
            {
                "kategori": "Komplikasi",
                "klinis": "Perdarahan GI",
                "icd": "K92.2",
                "score": 0.35,
                "tindakan": "Transfusi darah",
                "detail_modal": {}
            }
        ]
    }

@router.post("/analyze_diagnosis")
async def analyze_diagnosis(data: DiagnosisInput):
    await asyncio.sleep(1)
    return {
        "diagnosis": data.diagnosis_text,
        "icd10": "A91",
        "justification": {
            "aspek_klinis": ["Demam tinggi 3-5 hari", "Trombosit menurun", "Nyeri kepala"],
            "tindakan_disarankan": ["Cairan IV", "Monitoring Ht & Trombosit"],
            "rawat_inap": True,
            "rujukan": False
        },
        "referensi": {
            "PNPK": "PNPK-DBD-2022",
            "Fornas": "FORNAS-2023",
            "Permenkes": "PMK 52/2016"
        }
    }

@router.post("/analyze_claim")
async def analyze_claim(data: ClaimEvalInput):
    await asyncio.sleep(1)
    return {
        "simulasi": {
            "diagnosis_utama": data.primary,
            "diagnosis_sekunder": data.secondary,
            "tindakan_utama": data.procedures[0] if data.procedures else "Infus cairan",
            "tindakan_sekunder": data.procedures[1:] if len(data.procedures) > 1 else ["Monitoring laboratorium"],
            "tarif_draft": random.randint(3_000_000, 8_000_000)
        },
        "summary": {
            "status": "valid",
            "message": "Kombinasi valid secara medis dan sesuai regulasi.",
            "confidence": 0.95,
            "target": "Klaim disetujui",
            "medis": ["Diagnosis dan tindakan sesuai PNPK"],
            "regulasi": ["Sesuai regulasi BPJS"],
            "tarif": ["Tarif sesuai standar"]
        }
    }

@router.post("/generate_claim_combos")
async def generate_claim_combos(data: RMSummary):
    await asyncio.sleep(1)
    return {
        "rekomendasi": [
            {
                "diagnosis_utama": "Demam Berdarah Dengue",
                "diagnosis_sekunder": ["Hipertensi"],
                "tindakan_utama": "Pemeriksaan Laboratorium",
                "tindakan_sekunder": [],
                "tarif_draft": 3500000,
                "status": "valid"
            },
            {
                "diagnosis_utama": "Demam Berdarah Dengue",
                "diagnosis_sekunder": ["Diabetes Mellitus"],
                "tindakan_utama": "Rawat Inap",
                "tindakan_sekunder": [],
                "tarif_draft": 4200000,
                "status": "warning"
            },
            {
                "diagnosis_utama": "Infeksi Virus Nonspesifik",
                "diagnosis_sekunder": [],
                "tindakan_utama": None,
                "tindakan_sekunder": [],
                "tarif_draft": 0,
                "status": "invalid"
            }
        ]
    }
