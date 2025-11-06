# backend/services/claim_helper.py
"""
Module: backend.services.claim_helper

Helper khusus untuk integrasi klaim ↔ core_engine.
Berbeda dari claim/helper.py (utility kecil untuk update model).
"""

from fastapi import HTTPException, Body, Depends
from functools import wraps
from backend import models
from backend.database import SessionLocal, get_db
from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy import func
from datetime import datetime
import json
import traceback
import inspect

# ==================================================
# UPDATE MEDICAL RECORD (FULL) + LOG
# ==================================================
def update_medical_record_fields(mr, payload: dict, user_id: int, db: Session, action: str):
    """
    Update semua kolom medical_record dari payload + buat log ke MedicalRecordLog.
    Digunakan saat draft/finalize klaim.
    """
    field_map = {
        "riwayat_penyakit": payload.get("riwayat_penyakit"),
        "riwayat_pengobatan": payload.get("riwayat_pengobatan"),
        "riwayat_operasi": payload.get("riwayat_operasi"),
        "alergi": payload.get("alergi"),
        "keluhan": payload.get("keluhan"),
        "gejala_lain": payload.get("gejala_lain"),
        "tekanan_darah": payload.get("tekanan_darah") or payload.get("td"),
        "nadi": payload.get("nadi"),
        "pernapasan": payload.get("pernapasan"),
        "suhu": payload.get("suhu"),
        "spo2": payload.get("spo2"),
        "berat_badan": payload.get("berat_badan"),
        "tinggi_badan": payload.get("tinggi_badan"),
        "hemoglobin": payload.get("hemoglobin"),
        "leukosit": payload.get("leukosit"),
        "trombosit": payload.get("trombosit"),
        "gula_darah": payload.get("gula_darah"),
        "creatinin": payload.get("creatinin"),
        "rontgen_thorax": payload.get("rontgen_thorax"),
        "ct_scan": payload.get("ct_scan"),
        "usg": payload.get("usg"),
        "diagnosis_awal": payload.get("diagnosis_awal"),
        "komorbid": payload.get("komorbid"),
        "komplikasi": payload.get("komplikasi"),
        "diagnosis_akhir": payload.get("diagnosis_akhir"),
        "tindakan": payload.get("tindakan"),
        "obat": payload.get("obat"),
        "validasi_fornas": payload.get("validasi_fornas"),
        "notes_doctor": payload.get("notes_doctor"),
        "doctor_id": payload.get("doctor_id"),
        "doctor_name": payload.get("doctor_name"),
    }

    record_type = (
        payload.get("record_type")
        or payload.get("stage")
        or getattr(mr, "record_type", None)
        or "claim"
    )
    mr.record_type = record_type

    for field, value in field_map.items():
        if value is not None:
            setattr(mr, field, value)

    mr.updated_at = datetime.utcnow()

    # Log versi rekam medis
    latest_version = db.query(func.max(models.MedicalRecordLog.version)) \
                       .filter(models.MedicalRecordLog.medical_record_id == mr.id) \
                       .scalar() or 0

    db.add(models.MedicalRecordLog(
        medical_record_id=mr.id,
        action=action.upper(),
        description=f"Rekam medis diperbarui via {action.lower()} klaim",
        updated_by=user_id,
        updated_at=datetime.utcnow(),
        version=latest_version + 1,
        data_snapshot=json.dumps(mr.to_dict() if hasattr(mr, "to_dict") else {}, ensure_ascii=False),
        is_deleted=False,
        is_dummy=False
    ))
    return mr


# ==================================================
# GLOBAL RECORD (KIRIM KE CORE_ENGINE)
# ==================================================
def build_global_record(db: Session, claim_id: int) -> dict:
    """
    Build payload lengkap untuk dikirim ke core_engine.

    - Pertahankan struktur lama dari main.py:
        {
          "admission": {...},
          "daily": [],
          "discharge": {}
        }
    - Tambahan konteks aman: patient, visit, context
    """
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Admission record (jika ada)
    adm = None
    if getattr(claim, "medical_record_id", None):
        adm = db.query(models.MedicalRecord).get(claim.medical_record_id)

    # Helper to_dict (versi lama)
    def to_dict(r):
        if not r:
            return {}
        return {
            "riwayat_penyakit": getattr(r, "riwayat_penyakit", None),
            "riwayat_operasi": getattr(r, "riwayat_operasi", None),
            "alergi": getattr(r, "alergi", None),
            "keluhan": getattr(r, "keluhan", None),
            "td": getattr(r, "td", None),
            "nadi": getattr(r, "nadi", None),
            "pernapasan": getattr(r, "pernapasan", None),
            "suhu": getattr(r, "suhu", None),
            "spo2": getattr(r, "spo2", None),
            "berat_badan": getattr(r, "berat_badan", None),
            "tinggi_badan": getattr(r, "tinggi_badan", None),
            "hemoglobin": getattr(r, "hemoglobin", None),
            "leukosit": getattr(r, "leukosit", None),
            "trombosit": getattr(r, "trombosit", None),
            "gula_darah": getattr(r, "gula_darah", None),
            "creatinin": getattr(r, "creatinin", None),
            "rontgen_thorax": getattr(r, "rontgen_thorax", None),
            "ct_scan": getattr(r, "ct_scan", None),
            "usg": getattr(r, "usg", None),
            "diagnosis_awal": getattr(r, "diagnosis_awal", None),
            "komorbid": getattr(r, "komorbid", None),
            "komplikasi": getattr(r, "komplikasi", None),
            "diagnosis_akhir": getattr(r, "diagnosis_akhir", None),
            "tindakan": getattr(r, "tindakan", None),
            "obat": getattr(r, "obat", None),
        }

    payload = {
        "admission": to_dict(adm),
        "daily": [],
        "discharge": {},
    }

    # Tambahan konteks aman
    visit = getattr(claim, "visit", None)
    patient = getattr(visit, "patient", None) if visit else None

    payload.update({
        "claim_id": claim.id,
        "patient": {
            "id": getattr(patient, "id", None),
            "nama": getattr(patient, "nama", None),
            "gender": getattr(patient, "gender", None),
            "dob": str(getattr(patient, "tanggal_lahir", "")) if getattr(patient, "tanggal_lahir", None) else None,
        } if patient else {},
        "visit": {
            "id": getattr(visit, "id", None),
            "admission_date": str(getattr(visit, "admission_date", "")) if getattr(visit, "admission_date", None) else None,
            "discharge_date": str(getattr(visit, "discharge_date", "")) if getattr(visit, "discharge_date", None) else None,
        } if visit else {},
        "context": {
            "is_final": getattr(claim, "is_final", False),
            "created_by": getattr(claim, "created_by", None),
        },
    })
    return payload


# ==================================================
# OTHER HELPERS
# ==================================================
def map_icd10_code(code: str) -> str:
    if not code:
        return ""
    return code.strip().upper()


def build_procedure_context(db: Session, claim_id: int, stage: str) -> dict:
    """
    Ambil context dari ClaimSimulation untuk analyze_procedure.
    """
    sim = db.query(models.ClaimSimulation).filter_by(claim_id=claim_id, stage=stage).first()
    if not sim:
        return {}

    ctx = {
        "primary_claim": getattr(sim.diagnosis_utama, "diagnosis_text", None),
        "secondary_claims": [getattr(sim.diagnosis_sekunder, "diagnosis_text", None)]
            if getattr(sim, "diagnosis_sekunder", None) and getattr(sim.diagnosis_sekunder, "diagnosis_text", None) else [],
        "primary_action": getattr(sim.tindakan_utama, "procedure_text", None),
        "secondary_actions": [getattr(sim.tindakan_sekunder, "procedure_text", None)]
            if getattr(sim, "tindakan_sekunder", None) and getattr(sim.tindakan_sekunder, "procedure_text", None) else [],
    }
    return {k: v for k, v in ctx.items() if v and (not isinstance(v, list) or len(v))}

def normalize_predict_ddx(raw_resp: dict) -> dict:
    def map_item(item, is_child=False):
        return {
            "kategori": item.get("parent") if not is_child else item.get("name"),
            "klinis": item.get("parent") if not is_child else item.get("name"),
            "icd10_code": "",  # AI belum isi, biarkan kosong
            "procedure_text": "",
            "score": item.get("confidence", 0),
            "child": is_child
        }

    diagnosis = []
    for d in raw_resp.get("diagnosis", []):
        parent = map_item(d, False)
        parent["children"] = [map_item(ch, True) for ch in d.get("children", [])]
        diagnosis.append(parent)

    komorbid = []
    for k in raw_resp.get("komorbid", []):
        parent = map_item(k, False)
        parent["children"] = [map_item(ch, True) for ch in k.get("children", [])]
        komorbid.append(parent)

    komplikasi = []
    for c in raw_resp.get("komplikasi", []):
        parent = map_item(c, False)
        parent["children"] = [map_item(ch, True) for ch in c.get("children", [])]
        komplikasi.append(parent)

    return {
        "diagnosis": diagnosis,
        "komorbid": komorbid,
        "komplikasi": komplikasi
    }

# ==================================================
# PARSING UTILITIES
# ==================================================
def parse_number(val):
    """Helper parse angka dari string 'Rp xx.xxx' atau int/float langsung."""
    if not val:
        return None
    if isinstance(val, (int, float)):
        return val
    cleaned = str(val).replace("Rp", "").replace(",", "").replace(".", "").strip()
    if cleaned in ["", "-", "None", "nan"]:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None
