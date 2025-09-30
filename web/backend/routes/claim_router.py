"""
Module: backend.routers.claim_router

Manajemen klaim: list, detail, add/edit, draft/finalize, delete,
simulasi, evaluasi, AI proxy (core_engine), dan export.
"""

from fastapi import APIRouter, Depends, Request, Form, Body, Query, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import date
import io, json
from openpyxl import Workbook

from .. import models, form_configs
from ..database import get_db
from ..auth import require_roles_session, require_csrf_dep, issue_csrf_token
from ..utils.templates import templates
from ..utils.flash import flash
from ..crud import claim as claim_crud
from ..services.claim import core, simulation, ai
from ..services import claim_ai, claim_helper

router = APIRouter(prefix="/claims", tags=["Claims"])


# ==================================================
# LIST & DETAIL
# ==================================================

@router.get("")
def list_claims(
    request: Request,
    status: str | None = Query(None),
    tanggal_kunjungan: str | None = Query(None),
    patient_name: str | None = Query(None),
    claim_id: int | None = Query(None),
    visit_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator")),
):
    claims = claim_crud.get_claims(
        db,
        status=status,
        tanggal_kunjungan=tanggal_kunjungan,
        patient_name=patient_name,
        claim_id=claim_id,
        visit_id=visit_id,
    )
    return templates.TemplateResponse("claim_list.html", {
        "request": request,
        "claims": claims,
        "user": user,
        "current_user": user,
        "csrf_token": issue_csrf_token(request),
        "status": status,
        "tanggal_kunjungan": tanggal_kunjungan,
        "patient_name": patient_name,
        "claim_id": claim_id,
        "visit_id": visit_id,
    })


@router.get("/{claim_id}")
def claim_detail(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))
):
    claim = claim_crud.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return templates.TemplateResponse("claim_detail.html", {
        "request": request,
        "claim": claim,
        "user": user,
        "csrf_token": issue_csrf_token(request),
        "current_user": user,
    })


# ==================================================
# EXPORT
# ==================================================

@router.get("/export", name="export_claims")
def export_claims(
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","coder","verifikator","admin_rs","superadmin")),
):
    claims = claim_crud.export_claims(db, status, start_date, end_date)

    wb = Workbook()
    ws = wb.active
    ws.title = "Claims"
    ws.append(["Tanggal Klaim", "Nama Pasien", "Status", "Nama Dokter", "Created At"])
    for c in claims:
        ws.append([
            c.claim_date,
            c.patient.nama if c.patient else "N/A",
            c.status,
            c.doctor_name,
            c.created_at,
        ])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"claims_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================================================
# ADD / EDIT / UPDATE / FINALIZE
# ==================================================

@router.post("/add", name="add_claim")
def add_claim(
    request: Request,
    visit_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    claim = core.add_claim_service(
        db, user=current_user,
        form_data={"visit_id": visit_id, "hospital_id": current_user.hospital.id if current_user.hospital else None}
    )
    flash(request, "Claim berhasil ditambahkan!", "success")
    return RedirectResponse(url=f"/claims/{claim.id}", status_code=303)


@router.get("/{id}/edit")
def edit_claim_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator","coder","doctor"))
):
    claim = db.query(models.Claim).get(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    csrf_token = issue_csrf_token(request)
    is_doctor = (isinstance(user.role, str) and user.role == "doctor") or \
                (isinstance(user.role, (list, tuple)) and "doctor" in user.role)

    sim, summ = claim_helper.load_sim_and_summary(db, id, include_summary=not is_doctor)
    template_name = "claim_left.html" if is_doctor else "claim_right.html"

    return templates.TemplateResponse(template_name, {
        "request": request,
        "mode": "edit",
        "record": claim,
        "csrf_token": csrf_token,
        "current_user": user,
        "user": user,
        "isDoctor": is_doctor,
        "isVerifikator": ("verifikator" in user.role) if isinstance(user.role, (list, tuple)) else (user.role == "verifikator"),
        "sim": sim,
        "summ": summ,
        "claim_medical_record_fields": form_configs["claim_medical_record"],
    })


@router.post("/{claim_id}/update-draft", name="save_draft")
def update_claim_draft(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
    **form_data
):
    core.update_claim_draft_service(db, claim_id, user, form_data)
    flash(request, "Draft klaim berhasil diperbarui", "success")
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/{claim_id}/finalize", name="finalize_claim")
def finalize_claim(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator")),
    _=Depends(require_csrf_dep),
    **form_data
):
    core.finalize_claim_service(db, claim_id, user, form_data)
    flash(request, "Klaim difinalisasi", "success")
    return RedirectResponse("/dashboard", status_code=303)


# ==================================================
# DELETE
# ==================================================

@router.post("/{claim_id}/delete", name="delete_claim")
def delete_claim(
    claim_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","verifikator")),
    _=Depends(require_csrf_dep),
):
    claim_crud.delete_claim(db, claim_id)
    flash(request, "Klaim berhasil dihapus!", "success")
    return RedirectResponse("/claims", status_code=303)


# ==================================================
# SIMULASI & EVALUASI
# ==================================================

@router.get("/{claim_id}/simulations")
def get_simulations(claim_id: int, db: Session = Depends(get_db)):
    return simulation.get_simulations_service(db, claim_id)


# ==================================================
# AI PROXY (CORE ENGINE)
# ==================================================

@router.post("/{claim_id}/predict_ddx")
async def predict_ddx(claim_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    cid = payload.get("claim_id") or claim_id
    if not cid:
        raise HTTPException(status_code=422, detail="claim_id required")
    stage = (payload.get("stage") or "admission").strip()
    global_record = claim_helper.build_global_record(db, cid)
    forward = {"claim_id": cid, "stage": stage, "global_record": global_record}
    return await claim_ai.proxy_core_engine("/predict_ddx", forward)


@router.post("/{claim_id}/analyze_diagnosis")
async def analyze_diagnosis(claim_id: int, payload: dict = Body(...)):
    return await claim_ai.proxy_core_engine("/analyze_diagnosis", payload)


@router.post("/{claim_id}/analyze_procedure")
async def analyze_procedure(claim_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    cid = payload.get("claim_id") or claim_id
    procedure_name = payload.get("procedure_name")
    stage = (payload.get("stage") or "admission").strip()
    if not cid or not procedure_name:
        raise HTTPException(status_code=422, detail="claim_id and procedure_name required")
    context = claim_helper.build_procedure_context(db, cid, stage)
    core_payload = {"claim_id": cid, "procedure_name": procedure_name, "stage": stage}
    if context:
        core_payload["context"] = context
    return await claim_ai.proxy_core_engine("/analyze_procedure", core_payload)


@router.post("/{claim_id}/generate_claim_combos")
async def generate_claim_combos(claim_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    cid = payload.get("claim_id") or claim_id
    if not cid:
        raise HTTPException(status_code=422, detail="claim_id required")
    result = await claim_ai.proxy_core_engine("/generate_claim_combos", payload)
    ai.clear_ai_results(db, cid)
    ai.bulk_store_ai_results_from_core(db, cid, result)
    stage = payload.get("stage", "admission")
    return {"claim_id": cid, "stage": stage, "result": result}


@router.post("/{claim_id}/resume_medis")
async def resume_medis(claim_id: int, payload: dict = Body(...)):
    return await claim_ai.proxy_core_engine("/resume_medis", payload)


@router.post("/{claim_id}/regulation_detail")
async def regulation_detail(claim_id: int, payload: dict = Body(...)):
    return await claim_ai.proxy_core_engine("/regulation_detail", payload)
