from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from ... import models
import json


# ========== HELPER ==========

def _update_diag_fields(diag, data: dict):
    """Helper update field diagnosis"""
    diag.icd10_code = data.get("icd") or diag.icd10_code
    diag.justifikasi = data.get("label") or diag.justifikasi
    diag.bukti_klinis = data.get("bukti_klinis") or diag.bukti_klinis
    diag.syarat_klinis = data.get("syarat_klinis") or diag.syarat_klinis
    diag.kode_ganda = data.get("kode_ganda") or diag.kode_ganda
    diag.z_code = data.get("z_code") or diag.z_code
    diag.kode_bpjs_khusus = data.get("kode_bpjs_khusus") or diag.kode_bpjs_khusus
    diag.indikasi = data.get("indikasi") or diag.indikasi
    diag.lama_rawat = data.get("lama_rawat") or diag.lama_rawat
    diag.perpanjangan = data.get("perpanjangan") or diag.perpanjangan
    diag.kesesuaian_rs = data.get("kesesuaian_rs") or diag.kesesuaian_rs
    diag.syarat = data.get("syarat") or diag.syarat
    diag.kelayakan = data.get("kelayakan") or diag.kelayakan
    diag.struktur_icd10 = data.get("struktur_icd10") or diag.struktur_icd10
    diag.updated_at = datetime.utcnow()

def _update_or_create_procedure(db, claim, data: dict, proc_type: str, sim_id: int | None = None):
    """Insert/update ClaimProcedure + ClaimProcedureDetail (pasti set sim_id)."""
    proc = db.query(models.ClaimProcedure).filter_by(
        claim_id=claim.id, procedure_text=data["name"]
    ).first()

    if not proc:
        proc = models.ClaimProcedure(
            claim_id=claim.id,
            procedure_type=proc_type,
            procedure_text=data["name"],
            requirement_flag=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
            is_dummy=True,
        )
        db.add(proc)
        db.flush()

    # detail selalu cek lagi
    detail = db.query(models.ClaimProcedureDetail).filter_by(
        procedure_id=proc.id, is_deleted=False
    ).first()

    if not detail:
        detail = models.ClaimProcedureDetail(
            procedure_id=proc.id,
            claim_simulation_id=sim_id,   # ✅ wajib isi, biar gak null
            icd9_tindakan=data.get("icd") or "47.09",
            validitas_tindakan=data.get("validitas") or "valid",
            status_tindakan=data.get("status") or "valid",
            ina_cbg_tindakan=data.get("ina_cbg") or "valid",
            faskes_tindakan=data.get("faskes") or "valid",
            rawat_inap_tindakan=data.get("rawat_inap") or "valid",
            syarat_klinis_tindakan=data.get("syarat_klinis") or "valid",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
            is_dummy=True,
        )
        db.add(detail)
        db.flush()
    else:
        detail.icd9_tindakan = data.get("icd") or detail.icd9_tindakan
        detail.updated_at = datetime.utcnow()

    return proc.id

def _update_medical_record_from_form(db: Session, claim, user, form_data: dict, action="UPDATED"):
    """Helper untuk update rekam medis dengan semua field"""
    if not claim.medical_record:
        return

    mr = claim.medical_record
    for field in [
        "riwayat_penyakit", "riwayat_pengobatan", "riwayat_operasi", "alergi",
        "keluhan", "gejala_lain", "tekanan_darah", "nadi", "pernapasan", "suhu",
        "spo2", "berat_badan", "tinggi_badan", "hemoglobin", "leukosit",
        "trombosit", "gula_darah", "creatinin", "rontgen_thorax", "ct_scan",
        "usg", "diagnosis_awal", "komorbid", "komplikasi", "diagnosis_akhir",
        "tindakan", "obat", "validasi_fornas", "notes_doctor"
    ]:
        if field in form_data and form_data[field] is not None:
            setattr(mr, field, form_data[field])

    record_type = (
        form_data.get("record_type")
        or form_data.get("stage")
        or getattr(mr, "record_type", None)
        or "claim"
    )

    mr.record_type = record_type

    mr.updated_at = datetime.utcnow()

    latest_version = db.query(func.max(models.MedicalRecordLog.version)) \
        .filter(models.MedicalRecordLog.medical_record_id == mr.id) \
        .scalar() or 0

    db.add(models.MedicalRecordLog(
        medical_record_id=mr.id,
        action=action,
        description="Rekam medis diperbarui via draft klaim" if action == "UPDATED"
        else "Rekam medis difinalisasi via klaim",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        version=latest_version + 1,
        data_snapshot=json.dumps(mr.to_dict() if hasattr(mr, "to_dict") else {}, ensure_ascii=False),
        is_deleted=False,
        is_dummy=False
    ))

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