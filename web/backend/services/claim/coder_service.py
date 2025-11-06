"""
services/claim/coder_service.py
Helper functions untuk halaman verifikasi ICD (Coder).
"""

from backend import models
from fastapi import Request
from backend.utils.flash import flash
from fastapi.responses import HTMLResponse

def render_coder_template(request: Request, claim, stages, csrf_token, user):
    """Helper untuk render edit_coder.html"""
    from backend.templates import templates
    return templates.TemplateResponse(
        "edit_coder.html",
        {
            "request": request,
            "claim": claim,
            "stages": stages,
            "csrf_token": csrf_token,
            "user": user,
            "current_user": user,
        },
    )


def map_diag_for_coder(d: models.ClaimDiagnosis, sim_by_diag_id: dict) -> dict:
    """Map diagnosis ke format template coder."""
    sim = sim_by_diag_id.get(d.id)
    icd_final = sim.verified_icd10 if sim else d.icd10_code
    verified_by = getattr(sim, "coder_verified_by", None)
    verified_at = getattr(sim, "coder_verified_at", None)

    return {
        "type": d.diagnosis_type or "-",
        "text": d.diagnosis_text or "-",
        "icd_doctor": d.icd10_code or "-",
        "icd_final": icd_final,
        "item_id": d.id,
        "field": "diagnosis",
        "verified_by": verified_by,
        "verified_at": verified_at,
    }


def map_proc_for_coder(p: models.ClaimProcedure, db) -> dict:
    """Map procedure ke format coder."""
    icd9_doctor = None
    proc_detail = db.query(models.ClaimProcedureDetail).filter(
        models.ClaimProcedureDetail.procedure_id == p.id,
        models.ClaimProcedureDetail.is_deleted == False
    ).first()

    if proc_detail and proc_detail.icd9_tindakan:
        icd9_doctor = proc_detail.icd9_tindakan
    elif p.icd9_final_by_coder:
        icd9_doctor = p.icd9_final_by_coder

    return {
        "type": p.procedure_source or "manual",
        "text": p.procedure_text or "-",
        "icd_doctor": icd9_doctor or "-",
        "icd_final": p.icd9_final_by_coder or None,
        "item_id": p.id,
        "procedure_id": p.id,
        "field": "procedure",
        "verified_by": p.verified_by,
        "verified_at": p.verified_at,
        "stage": p.stage or "admission",
    }


def empty_stages():
    """Struktur aman untuk template edit_coder.html"""
    return {
        "admission": {"diagnosis": [], "procedure": []},
        "daily-0": {"diagnosis": [], "procedure": []},
        "discharge": {"diagnosis": [], "procedure": []},
    }
