"""
routers/claim/claim_coder_router.py
Modularisasi endpoint Coder (verifikasi ICD).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from backend.database import get_db
from backend.auth import require_roles_session, issue_csrf_token
from backend import models
from backend.services.claim import simulation as sim_service
from backend.services.claim import coder_service
from backend.utils.flash import flash  # pastikan ada flash helper

router = APIRouter(tags=["Claim Coder"])


# ==================================================
# CODER REVIEW PAGE
# ==================================================
@router.get("/{claim_id}", response_class=HTMLResponse)
def coder_review_page(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("coder")),
):
    """Halaman verifikasi ICD oleh coder"""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Validasi workflow
    if claim.workflow_status not in ["doctor_submitted", "coder_review", "coder_verified"]:
        flash(request, "⚠️ Klaim belum siap untuk review coder", "warning")
        return RedirectResponse(url="/claims", status_code=303)

    stages = sim_service.get_simulations_for_coder(db, claim_id)
    csrf_token = issue_csrf_token(request)

    return coder_service.render_coder_template(
        request, claim, stages, csrf_token, user
    )


# ==================================================
# SUBMIT CODER VERIFICATION
# ==================================================
@router.post("/{claim_id}")
async def coder_submit_verification(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("coder")),
):
    """Simpan hasil verifikasi ICD coder dan update workflow"""
    form_data = await request.form()

    # Simpan hasil verifikasi
    updated = sim_service.save_coder_verification(db, claim_id, form_data, user.name)

    # 🔹 Update semua ClaimSimulation terkait
    db.query(models.ClaimSimulation).filter(
        models.ClaimSimulation.claim_id == claim_id
    ).update({
        models.ClaimSimulation.coder_verified: True,
        models.ClaimSimulation.is_coder_approved: True,
        models.ClaimSimulation.coder_verified_by: user.name,
        models.ClaimSimulation.coder_verified_at: datetime.utcnow(),
    })

    # 🔹 Update juga status di Claim utama
    claim = db.query(models.Claim).get(claim_id)
    if claim:
        claim.workflow_status = "coder_verified"
        claim.coder_verified_by = user.name
    claim.coder_verified_at = datetime.utcnow()

    db.commit()

    flash(request, f"✅ {updated} entri berhasil diverifikasi oleh coder. Klaim siap untuk verifikator.", "success")
    return RedirectResponse(url="/claims", status_code=303)


# ==================================================
# EDIT VIEW UNTUK CODER (VERSI DETAIL)
# ==================================================
@router.get("/{claim_id}/edit", name="edit_coder_view")
def edit_coder_view(
    claim_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("coder", "verifikator", "doctor", "admin_rs", "superadmin")),
):
    """
    View halaman verifikasi ICD untuk coder.
    Mengirim: claim, stages (dict of {stage: {diagnosis:[], procedure:[]}}).
    """
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim tidak ditemukan")

    # Ambil semua diagnosis & procedure klaim
    diags = db.query(models.ClaimDiagnosis).filter(
        models.ClaimDiagnosis.claim_id == claim_id,
        models.ClaimDiagnosis.is_deleted == False
    ).all()

    procs = db.query(models.ClaimProcedure).filter(
        models.ClaimProcedure.claim_id == claim_id,
        models.ClaimProcedure.is_deleted == False
    ).all()

    # Ambil simulation data (opsional)
    sims = db.query(models.ClaimSimulation).filter(
        models.ClaimSimulation.claim_id == claim_id,
        models.ClaimSimulation.is_deleted == False
    ).all()

    # Map simulation by diagnosis ID
    sim_by_diag_id = {}
    for s in sims:
        if s.diagnosis_utama_id:
            sim_by_diag_id[s.diagnosis_utama_id] = s
        if s.diagnosis_sekunder_id:
            sim_by_diag_id[s.diagnosis_sekunder_id] = s

    # Gunakan helper untuk struktur stage
    stages = coder_service.empty_stages()

    # Diagnosis mapping
    for d in diags:
        stages["admission"]["diagnosis"].append(coder_service.map_diag_for_coder(d, sim_by_diag_id))

    # Procedure mapping
    for p in procs:
        stage_key = p.stage if p.stage in stages else "admission"
        stages[stage_key]["procedure"].append(coder_service.map_proc_for_coder(p, db))

    return coder_service.render_coder_template(
        request, claim, stages, issue_csrf_token(request), user
    )
