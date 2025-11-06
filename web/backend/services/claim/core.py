"""
Module: backend.services.claim.core

Berisi service functions utama untuk manajemen klaim:
- tambah klaim baru
- update draft klaim
- finalisasi klaim

Semua fungsi di sini hanya fokus pada business logic klaim.
HTTP/Template handling dilakukan di claim_router.py.
"""

from fastapi import HTTPException
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from ... import models
from .save_simulation_refactor import save_simulasi
from .ai import store_ai_evaluations
from .. import claim_helper
import json

# ==================================================
# ADD CLAIM
# ==================================================
def add_claim_service(db: Session, visit_id: int, user, hospital_id: int | None = None):
    """
    Buat klaim baru (status draft) + log.
    """
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        return None
    
    # Buat klaim
    claim = models.Claim(
        claim_date=datetime.utcnow(),
        visit_id=visit_id,
        patient_id=visit.patient_id,
        hospital_id=hospital_id,
        doctor_id=user.id,
        doctor_name=user.name,
        medical_record_id=None,
        is_final=False,
        status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=False,
    )
    db.add(claim)
    db.flush()
    db.refresh(claim)

    # Log klaim
    db.add(models.ClaimLog(
        claim_id=claim.id,
        action="CREATED",
        description=f"Klaim {claim.id} dibuat oleh {user.name}",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=False
    ))
    # Buat Rekam Medis
    mr = models.MedicalRecord(
        patient_id=visit.patient_id,
        visit_id=visit_id,
        doctor_id=visit.doctor_id,
        doctor_name=visit.doctor_name,
        record_type="admission",
        is_final=False,
        notes_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=True
    )

    db.add(mr)
    db.flush()
    db.refresh(mr)

    # link-kan ke klaim
    claim.medical_record_id = mr.id

    # rekam medis log
    latest_version = db.query(func.max(models.MedicalRecordLog.version)) \
                       .filter(models.MedicalRecordLog.medical_record_id == mr.id) \
                       .scalar() or 0
    db.add(models.MedicalRecordLog(
        medical_record_id=mr.id,
        action="CREATED",
        description=f"Rekam medis {mr.id} dibuat oleh {user.name}",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        version=latest_version + 1,
        data_snapshot=json.dumps(mr.to_dict() if hasattr(mr, "to_dict") else {}, ensure_ascii=False),
        is_deleted=False,
        is_dummy=False
    ))
    db.commit()
    return claim


def update_claim_draft_service(db: Session, claim_id: int, user, form_data: dict):
    """Update klaim dalam status draft."""
    claim = db.get(models.Claim, claim_id)
    if not claim:
        return None

    # --- Parse simulasi & summary ---
    sim_data = form_data.get("simulasi")
    summ_data = form_data.get("summary")

    def safe_parse(data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
                if isinstance(data, str):
                    data = json.loads(data)
            except Exception:
                data = {}
        return data or {}

    sim_data = safe_parse(sim_data)
    summ_data = safe_parse(summ_data)

    # --- Simpan simulasi ---
    if sim_data:
        try:
            save_simulasi(db, claim.id, sim_data, form_data)
        except Exception as e:
            db.rollback()
            print(f"[UPDATE_DRAFT] ❌ Error in save_simulasi: {e}")
            raise

    # --- Simpan evaluasi ---
    if summ_data:
        try:
            store_ai_evaluations(db, claim.id, summ_data)
        except Exception as e:
            db.rollback()
            print(f"[UPDATE_DRAFT] ❌ Error in store_ai_evaluations: {e}")
            raise

    # --- Update rekam medis ---
    if claim.medical_record:
        claim_helper.update_medical_record_fields(
            claim.medical_record, form_data, user.id, db, "draft"
        )

    # --- Update status ---
    claim.is_final = False
    claim.status = "draft"
    claim.updated_at = datetime.utcnow()

    # --- Log klaim ---
    db.add(models.ClaimLog(
        claim_id=claim.id,
        action="UPDATED",
        description="Draft klaim diperbarui",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=False
    ))

    db.commit()
    db.refresh(claim)
    return claim



# ==================================================
# FINALIZE CLAIM
# ==================================================
def finalize_claim_service(db: Session, claim_id: int, user, form_data: dict):
    """
    Finalisasi klaim:
    - update simulasi
    - update evaluasi (summary)
    - update rekam medis
    - set status final
    """
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        return None

    sim_data = form_data.get("simulasi")
    summ_data = form_data.get("summary")

    if isinstance(sim_data, str):
        try:
            sim_data = json.loads(sim_data)
        except Exception:
            sim_data = {}
    if isinstance(summ_data, str):
        try:
            summ_data = json.loads(summ_data)
        except Exception:
            summ_data = {}

    if sim_data:
        save_simulasi(db, claim.id, sim_data)
    if summ_data:
        store_ai_evaluations(db, claim.id, summ_data)

    if claim.medical_record:
        claim_helper.update_medical_record_fields(claim.medical_record, form_data, user.id, db, "finalized")

    claim.is_final = True
    claim.status = "final"
    claim.updated_at = datetime.utcnow()

    db.add(models.ClaimLog(
        claim_id=claim.id,
        action="FINALIZED",
        description="Klaim difinalisasi",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=False
    ))
    db.commit()
    db.refresh(claim)
    return claim

# ======================================================
# WORKFLOW STATUS & RETURN TO DOCTOR SERVICES
# ======================================================

def get_workflow_status(db, claim_id: int):
    """Ambil status workflow terkini dari klaim"""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    return {
        "claim_id": claim_id,
        "workflow_status": claim.workflow_status or "draft",
        "created_by": claim.created_by,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "doctor_submitted_by": getattr(claim, "doctor_submitted_by", None),
        "doctor_submitted_at": getattr(claim, "doctor_submitted_at", None).isoformat()
            if getattr(claim, "doctor_submitted_at", None) else None,
        "coder_verified_by": getattr(claim, "coder_verified_by", None),
        "coder_verified_at": getattr(claim, "coder_verified_at", None).isoformat()
            if getattr(claim, "coder_verified_at", None) else None,
        "finalized_by": getattr(claim, "finalized_by", None),
        "finalized_at": getattr(claim, "finalized_at", None).isoformat()
            if getattr(claim, "finalized_at", None) else None,
    }


def return_to_doctor(db, claim_id: int, reason: str, user):
    """Kembalikan klaim ke dokter untuk revisi"""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Tambah catatan alasan
    note = models.ClaimNote(
        claim_id=claim_id,
        item_id="0",
        role=user.role_names[0] if hasattr(user, "role_names") and user.role_names else "unknown",
        user_id=user.id,
        note_text=f"RETURNED TO DOCTOR: {reason}",
        timestamp=datetime.now()
    )
    db.add(note)

    # Reset workflow
    claim.workflow_status = "draft"
    db.commit()
    return {"status": "success", "message": "Claim returned to doctor"}

# ======================================================
# VERIFY STORAGE SERVICE
# ======================================================

def verify_storage(db, claim_id: int):
    """Verifikasi isi penyimpanan data klaim"""
    try:
        result = {
            "claim_id": claim_id,
            "timestamp": datetime.now().isoformat(),
            "storage_verification": {}
        }

        # 1. ClaimAIRecommendation
        ai_recs = db.query(models.ClaimAIRecommendation).filter_by(
            claim_id=claim_id, is_deleted=False
        ).count()
        result["storage_verification"]["ai_recommendations"] = {
            "count": ai_recs,
            "status": "✅ OK" if ai_recs > 0 else "⚠️ Empty"
        }

        # 2. ClaimDiagnosis
        diagnoses = db.query(models.ClaimDiagnosis).filter_by(
            claim_id=claim_id, is_deleted=False
        ).all()
        result["storage_verification"]["diagnoses"] = {
            "count": len(diagnoses),
            "types": [d.diagnosis_type for d in diagnoses],
            "status": "✅ OK" if diagnoses else "⚠️ Empty"
        }

        # 3. ClaimProcedure
        procedures = db.query(models.ClaimProcedure).filter_by(
            claim_id=claim_id, is_deleted=False
        ).all()
        modal_procs = [p for p in procedures if p.procedure_source in ["modal_diagnosis", "modal_procedure"]]
        result["storage_verification"]["procedures"] = {
            "total_count": len(procedures),
            "modal_count": len(modal_procs),
            "modal_types": [p.procedure_source for p in modal_procs],
            "status": "✅ OK" if modal_procs else "⚠️ No modal procedures"
        }

        # 4. ClaimProcedureDetail
        proc_details = db.query(models.ClaimProcedureDetail).filter(
            models.ClaimProcedureDetail.procedure_id.in_([p.id for p in procedures])
        ).count()
        result["storage_verification"]["procedure_details"] = {
            "count": proc_details,
            "status": "✅ OK" if proc_details > 0 else "⚠️ Empty"
        }

        # 5. ClaimRegulationDetail
        regs = db.query(models.ClaimRegulationDetail).filter_by(claim_id=claim_id).count()
        result["storage_verification"]["regulations"] = {
            "count": regs,
            "status": "✅ OK" if regs > 0 else "⚠️ Empty"
        }

        # 6. ClaimIDRGDiagnosis
        idrg_diag = db.query(models.ClaimIDRGDiagnosis).filter_by(claim_id=claim_id, is_deleted=False).count()
        result["storage_verification"]["idrg_diagnosis"] = {
            "count": idrg_diag,
            "status": "✅ OK" if idrg_diag > 0 else "⚠️ Empty"
        }

        # 7. ClaimIDRGSummary
        idrg_sum = db.query(models.ClaimIDRGSummary).filter_by(claim_id=claim_id, is_deleted=False).count()
        result["storage_verification"]["idrg_summary"] = {
            "count": idrg_sum,
            "status": "✅ OK" if idrg_sum > 0 else "⚠️ Empty (normal untuk doctor)"
        }

        # 8. ClaimSimulation
        sims = db.query(models.ClaimSimulation).filter_by(claim_id=claim_id, is_deleted=False).count()
        result["storage_verification"]["simulations"] = {
            "count": sims,
            "status": "✅ OK" if sims > 0 else "⚠️ Empty"
        }

        # Overall summary
        issues = [k for k, v in result["storage_verification"].items()
                  if "⚠️" in v["status"] and k not in ["idrg_summary"]]
        result["overall_status"] = "✅ ALL GOOD" if not issues else f"⚠️ Issues: {', '.join(issues)}"
        result["next_step"] = "Ready for STEP 3" if not issues else "Need to test endpoints"
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")

# ======================================================
# 🖼️ RENDER CLAIM LIST (FE LEGACY)
# ======================================================

from backend.utils.templates import templates
from fastapi import HTTPException
from fastapi.responses import HTMLResponse

def render_claim_list(
    request, db, claims, user,
    page=1, limit=20,
    total_count=0, total_pages=0,
    workflow_counts=None,
    total_ai_alerts=0,
    total_tarif=0,
    filters=None,
):
    """
    Render halaman daftar klaim (legacy template).
    """
    try:
        return templates.TemplateResponse(
            "claim_list.html",
            {
                "request": request,
                "claims": claims,
                "user": user,
                "current_user": user,
                "csrf_token": getattr(request.state, "csrf_token", None),
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "total_count": total_count,
                "workflow_counts": workflow_counts or {},
                "total_ai_alerts": total_ai_alerts,
                "total_tarif": total_tarif,
                **(filters or {}),
            },
        )
    except Exception as e:
        print(f"[render_claim_list] ❌ Template error: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal render halaman klaim: {e}")

