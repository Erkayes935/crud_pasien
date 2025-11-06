"""
routers/claim/claim_core_router.py
Versi clean — menggunakan helper dari _utils.py
Berisi endpoint inti (core): list, export, visit, move, delete, workflow.
"""

from fastapi import (
    APIRouter, Depends, Query, Form, HTTPException, Request
)
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import get_db
from backend.auth import require_roles_session, issue_csrf_token
from backend.crud import claim as claim_crud
from backend import models
from backend.services.claim import core as claim_service
from backend.utils.templates import templates

# 🔧 impor helper dari file utils
from backend.utils.claim_utils import (
    normalize_str,
    parse_int,
    build_base_query,
    apply_filters,
    eagerload_relations,
    aggregate_ai_notifications,
    get_primary_diagnosis,
    get_secondary_diagnoses,
    get_primary_procedure,
    get_tariffs_optimized,
    calculate_length_of_stay,
)

router = APIRouter(tags=["Claim Core"])

# ======================================================
# 📋 LIST & FILTER CLAIMS
# ======================================================

@router.get("/", response_class=HTMLResponse)
def list_claims(
    request: Request,
    status: str | None = Query(None),
    tanggal_kunjungan: str | None = Query(None),
    patient_name: str | None = Query(None),
    claim_id: str | None = Query(None),
    visit_id: str | None = Query(None),
    workflow_status: str | None = Query(None),
    diagnosis: str | None = Query(None),
    tindakan: str | None = Query(None),
    doctor_name: str | None = Query(None),
    ai_status: str | None = Query(None),
    tarif_cbg_min: str | None = Query(None),
    tarif_cbg_max: str | None = Query(None),
    los_min: str | None = Query(None),
    los_max: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """
    Daftar klaim (versi refactor dari kode lama).
    Menggunakan helper SQL di claim_utils + render FE lama.
    """
    from backend.utils import claim_utils as utils
    from backend.services.claim import core as claim_service
    from sqlalchemy import func

    # --- Normalisasi parameter ---
    f = lambda v: utils.normalize_str(v)
    status = f(status)
    tanggal_kunjungan = f(tanggal_kunjungan)
    patient_name = f(patient_name)
    workflow_status = f(workflow_status)
    diagnosis = f(diagnosis)
    tindakan = f(tindakan)
    doctor_name = f(doctor_name)
    ai_status = f(ai_status)

    tarif_cbg_min = utils.parse_int(tarif_cbg_min)
    tarif_cbg_max = utils.parse_int(tarif_cbg_max)
    los_min = utils.parse_int(los_min)
    los_max = utils.parse_int(los_max)

    # --- Query utama ---
    query, joined = utils.build_base_query(db, user)

    query, joined = utils.apply_filters(query, {
        "status": status,
        "tanggal_kunjungan": tanggal_kunjungan,
        "patient_name": patient_name,
        "claim_id": claim_id,
        "visit_id": visit_id,
        "workflow_status": workflow_status,
        "diagnosis": diagnosis,
        "tindakan": tindakan,
        "doctor_name": doctor_name,
    }, joined)

    query = utils.eagerload_relations(query, joined)

    # --- Statistik global ---
    total_count = query.order_by(None).distinct(models.Claim.id).count()

    # --- Statistik workflow ---
    workflow_counts = utils.count_workflow_status(db, query)

    # --- Statistik AI & Tarif ---
    total_ai_alerts = utils.count_ai_alerts(db, user)
    total_tarif = utils.sum_total_tarif(db, user)

    # --- Pagination ---
    total_pages = (total_count + limit - 1) // limit
    offset = (page - 1) * limit

    # --- Fetch data ---
    # 💡 ambil dulu ID-nya aja biar query kecil
    claim_ids = (
        db.query(models.Claim.id)
        .filter(*query._whereclause.clauses if hasattr(query, "_whereclause") else [])
        .order_by(models.Claim.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    claim_ids = [c.id for c in claim_ids]

    # 💡 baru fetch full data tapi by ID list
    claims_raw = (
        db.query(models.Claim)
        .filter(models.Claim.id.in_(claim_ids))
        .all()
    )

    # --- Batch processing ---
    claims = utils.enrich_claim_data(db, claims_raw, ai_status, tarif_cbg_min, tarif_cbg_max, los_min, los_max)

    # --- Render ke template lama ---
    return claim_service.render_claim_list(
        request, db, claims, user,
        page=page,
        limit=limit,
        total_count=total_count,
        total_pages=total_pages,
        workflow_counts=workflow_counts,
        total_ai_alerts=total_ai_alerts,
        total_tarif=total_tarif,
        filters={
            "status": status,
            "workflow_status": workflow_status,
            "tanggal_kunjungan": tanggal_kunjungan,
            "patient_name": patient_name,
            "claim_id": claim_id,
            "visit_id": visit_id,
            "diagnosis": diagnosis,
            "tindakan": tindakan,
            "doctor_name": doctor_name,
            "ai_status": ai_status,
            "tarif_cbg_min": tarif_cbg_min,
            "tarif_cbg_max": tarif_cbg_max,
            "los_min": los_min,
            "los_max": los_max,
        },
    )
    # return response

# ======================================================
# 📋 GET VISITS
# ======================================================

@router.get("/{claim_id}/visits")
def get_visits_for_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """Ambil daftar visit terkait satu pasien"""
    try:
        visits = claim_service.get_visits_by_claim(db, claim_id)
        return {"status": "ok", "data": visits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal ambil visit: {e}")


# ======================================================
# 🔁 MOVE VISIT / CLAIM
# ======================================================

@router.post("/move-visit")
def move_visit(
    source_claim_id: int = Form(...),
    target_visit_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs", "superadmin")),
):
    """Pindahkan klaim ke visit lain"""
    try:
        result = claim_service.move_visit(db, source_claim_id, target_visit_id)
        return {
            "status": "ok",
            "message": f"Klaim {source_claim_id} dipindah ke visit {target_visit_id}",
            "data": result,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal pindah klaim: {e}")


@router.post("/{claim_id}/move-to-group")
def move_to_group(
    claim_id: int,
    new_group_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs", "superadmin")),
):
    """Pindahkan klaim ke group lain"""
    try:
        claim_service.move_to_group(db, claim_id, new_group_id)
        return {"status": "ok", "message": f"Klaim {claim_id} dipindah ke group {new_group_id}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal pindah group: {e}")


# ======================================================
# 🗑️ DELETE CLAIM
# ======================================================

@router.post("/{claim_id}/delete")
def delete_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs", "superadmin")),
):
    """Hapus satu klaim"""
    try:
        claim_service.delete_claim(db, claim_id)
        return {"status": "ok", "message": f"Klaim {claim_id} dihapus"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal hapus klaim: {e}")


# ======================================================
# 🔄 RETURN TO DOCTOR
# ======================================================

@router.post("/{claim_id}/return-to-doctor")
def return_to_doctor(
    claim_id: int,
    reason: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("coder", "verifikator", "admin_rs", "superadmin")),
):
    """Kembalikan klaim ke dokter untuk revisi"""
    try:
        claim_service.return_to_doctor(db, claim_id, reason, user)
        return {"status": "ok", "message": f"Klaim {claim_id} dikembalikan ke dokter"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal return-to-doctor: {e}")


# ======================================================
# 📊 WORKFLOW STATUS
# ======================================================

@router.get("/{claim_id}/workflow-status")
def get_workflow_status(
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """Ambil status workflow klaim"""
    try:
        status = claim_service.get_workflow_status(db, claim_id)
        return {"status": "ok", "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal ambil workflow status: {e}")

# ======================================================
# 🧪 VERIFY STORAGE
# ======================================================

@router.get("/{claim_id}/verify-storage", name="verify_claim_storage")
def verify_claim_storage(
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """Test endpoint untuk verify semua data storage dari STEP 1 fixes."""
    try:
        result = claim_service.verify_storage(db, claim_id)
        return {"status": "ok", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")

# ==================================================
# ✅ VERIFY CLAIM GROUP (DEBUGGING & ADMIN TOOL)
# ==================================================
@router.get("/{claim_id}/verify-group", name="verify_claim_group")
def verify_claim_group(
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "admin_rs", "superadmin")),
):
    """
    Endpoint debugging/admin:
    Verifikasi apakah klaim sudah masuk ke group (episode) yang benar.
    - Menampilkan info group & patient terkait.
    - Juga daftar semua group milik pasien tersebut.
    """
    try:
        claim = db.query(models.Claim).filter_by(id=claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")

        # Get group info
        group = db.query(models.ClaimGroup).filter_by(id=claim.group_id).first() if claim.group_id else None
        patient = db.query(models.Patient).filter_by(id=claim.patient_id).first()

        # Get all groups for this patient
        all_groups = db.query(models.ClaimGroup).filter_by(patient_id=claim.patient_id).all()

        return {
            "status": "success",
            "claim": {
                "id": claim.id,
                "workflow_status": claim.workflow_status,
                "created_by": claim.created_by,
                "group_id": claim.group_id,
            },
            "group_info": {
                "id": group.id if group else None,
                "kode_group": getattr(group, "kode_group", None),
                "nama_group": getattr(group, "nama_group", None),
                "patient_id": getattr(group, "patient_id", None),
            } if group else None,
            "patient_info": {
                "id": patient.id if patient else None,
                "nama": getattr(patient, "nama", None),
                "no_rm": getattr(patient, "no_rm", None),
            } if patient else None,
            "all_patient_groups": [
                {
                    "id": g.id,
                    "kode_group": g.kode_group,
                    "nama_group": g.nama_group,
                    "claim_count": len(g.claims) if g.claims else 0,
                }
                for g in all_groups
            ],
            "summary_status": "✅ OK (Has group)" if claim.group_id else "⚠️ NO GROUP ASSIGNED",
        }

    except Exception as e:
        print(f"[VERIFY_GROUP] ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Gagal verifikasi group klaim: {e}")

# ==================================================
# 🔐 CSRF TOKEN REFRESH
# ==================================================

@router.get("/csrf/refresh")
def refresh_csrf_token(request: Request):
    """Endpoint untuk refresh token CSRF via AJAX (FE)."""
    from ...auth import issue_csrf_token
    return {"csrf_token": issue_csrf_token(request)}

# ======================================================
# 🚦 REDIRECT HANDLER: /claims → /claims/
# ======================================================
from fastapi.responses import RedirectResponse

@router.get("/redirect", include_in_schema=False)
def redirect_claims_root():
    """Redirect /claims ke /claims/ agar tidak 307 redirect dari browser"""
    return RedirectResponse(url="/claims/", status_code=307)

