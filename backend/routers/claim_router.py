"""
Module: backend.routers.claim_router

Semua route untuk manajemen klaim (list, add, edit, delete, AI, draft/finalize).
Route dibuat tipis → panggil crud.Claim + services.claim_service.
"""

from fastapi import APIRouter, Depends, Request, Form, Body, Query, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import Optional

from .. import models
from ..database import get_db
from ..utils.flash import flash
from ..utils.templates import templates
from ..utils.dummy_data import make_dummy
from ..auth import require_roles_session, require_csrf_dep, issue_csrf_token
from ..crud import claim_note as claim_crud
from ..services import claim as claim_service
from ..form_configs import form_configs
from ..utils.form_utils import get_form_as_dict

import io, json
from openpyxl import Workbook

router = APIRouter(prefix="/claims", tags=["Claims"])

# ==========================
# WIZARD KLAIM BARU
# ==========================

@router.get("/add/start")
def add_claim_start(
    request: Request,
    user=Depends(require_roles_session("doctor"))
):
    """Step 1: redirect dari dashboard → daftar pasien (mode klaim)."""
    flash(request, "Pilih pasien untuk memulai klaim baru...", "info")
    return RedirectResponse("/patients?mode=claim")


@router.get("/add/form/{visit_id}", response_class=HTMLResponse, name="form_add_claim")
def claim_form(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor"))  # hanya dokter yg boleh
):
    """Step 2: tampilkan form klaim berdasarkan visit terpilih."""
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit tidak ditemukan")
    patient = visit.patient

    csrf_token = issue_csrf_token(request)

    # field netral dari config
    fields = form_configs["claim_medical_record"].copy()

    # Inject hospital (auto dari akun dokter)
    if user.hospital:
        fields.insert(0, {"name": "hospital_id", "type": "hidden", "value": user.hospital.id})
        fields.insert(1, {
            "name": "hospital_name", "label": "Rumah Sakit",
            "type": "readonly", "value": user.hospital.nama
        })

    # Inject patient & visit (selalu hidden karena datang dari wizard)
    fields.insert(0, {"name": "patient_id", "type": "hidden", "value": patient.id})
    fields.insert(1, {"name": "visit_id", "type": "hidden", "value": visit.id})

    # Inject dokter (auto dari akun login)
    if user.role == "doctor":
        fields.insert(2, {
            "name": "doctor_name",
            "label": "Dokter",
            "type": "readonly",
            "value": user.name
        })
        fields.insert(3, {
            "name": "doctor_id",
            "type": "hidden",
            "value": user.id
        })
    else:
        doctors = db.query(models.User).filter(
            models.User.role == "doctor",
            models.User.is_deleted == False
        ).all()
        fields.insert(2, {
            "name": "doctor_id",
            "label": "Dokter",
            "type": "select",
            "options": [{"value": d.id, "label": d.name} for d in doctors]
        })

    return templates.TemplateResponse(
        "claim_left.html",
        {
            "request": request,
            "visit": visit,
            "patient": patient,
            "mode": "add",
            "current_user": user,
            "user": user,
            "role": user.role if isinstance(user.role, str) else user.role[0],
            "isDoctor": user.role == "doctor" or ("doctor" in user.role),
            "isVerifikator": user.role == "verifikator" or ("verifikator" in user.role),
            "csrf_token": csrf_token,
            "claim_medical_record_fields": fields,
        },
    )


# ==================================================
# LIST & DETAIL
# ==================================================

@router.get("")
def list_claims(
    request: Request,
    status: str | None = Query(None),
    tanggal_kunjungan: str | None = Query(None),
    patient_name: str | None = Query(None),
    jenis_kunjungan: str | None = Query(None),
    claim_id: int | None = Query(None),
    visit_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))
):
    claims = claim_crud.get_claims(
        db,
        status=status,
        tanggal_kunjungan=tanggal_kunjungan,
        patient_name=patient_name,
        jenis_kunjungan=jenis_kunjungan,
        claim_id=claim_id,
        visit_id=visit_id,
    )
    return templates.TemplateResponse(
        "claim_list.html",
        {
            "request": request,
            "claims": claims,
            "user": user,
            "current_user": user,
            "csrf_token": issue_csrf_token(request),
            "status": status,
            "tanggal_kunjungan": tanggal_kunjungan,
            "patient_name": patient_name,
            "jenis_kunjungan": jenis_kunjungan,
            "claim_id": claim_id,
            "visit_id": visit_id,
        }
    )


@router.get("/{claim_id}")
def claim_detail(request: Request, claim_id: int, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))):
    claim = claim_crud.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return templates.TemplateResponse(
        "claim_detail.html",
        {"request": request, "claim": claim, "user": user, "current_user": user, "csrf_token": issue_csrf_token(request)}
    )


# ==================================================
# EXPORT
# ==================================================

@router.get("/export", name="export_claims")
def export_claims(
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","coder","verifikator","admin_rs","superadmin"))
):
    claims = claim_crud.export_claims(db, status=status, start_date=start_date, end_date=end_date)

    wb = Workbook()
    ws = wb.active
    ws.title = "Claims"
    ws.append([
        "Tanggal Klaim", "Nama Pasien", "Status", "Nama Dokter",
        "Simulasi Draft", "Ringkasan Draft",
        "Final", "Simulasi Final", "Ringkasan Final", "Created At",
    ])
    for c in claims:
        ws.append([
            c.claim_date,
            c.patient.nama if c.patient else "N/A",
            c.status,
            c.doctor_name,
            json.dumps(c.simulasi_draft) if not c.is_final else "N/A",
            json.dumps(c.summary_draft) if not c.is_final else "N/A",
            "Ya" if c.is_final else "Tidak",
            json.dumps(c.simulasi_draft) if c.is_final else "N/A",
            json.dumps(c.summary_draft) if c.is_final else "N/A",
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
# ADD CLAIM
# ==================================================

@router.post("/add", name="add_claim")
def add_claim(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
    form_data: dict = Depends(get_form_as_dict)  # helper untuk ambil semua field form ke dict
):
    claim = claim_service.add_claim_service(db, user, form_data)
    flash(request, "✅ ID Klaim berhasil didapatkan!", "success")
    return RedirectResponse(url=f"/claims/{claim.id}/edit", status_code=303)


# ==================================================
# EDIT CLAIM
# ==================================================

@router.get("/{id}/edit")
def edit_claim_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator", "coder", "doctor"))
):
    claim = db.query(models.Claim).get(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    patients = db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
    visits = db.query(models.Visit).filter(models.Visit.is_deleted == False).all()
    hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
    csrf_token = issue_csrf_token(request)

    is_doctor = (isinstance(user.role, str) and user.role == "doctor") or \
                (isinstance(user.role, (list, tuple)) and "doctor" in user.role)

    include_summary = not is_doctor
    sim, summ = claim_service.load_sim_and_summary_service(db, id, include_summary=include_summary)

    template_name = "claim_left.html" if is_doctor else "claim_right.html"

    fields = form_configs["claim_medical_record"].copy()
    for f in fields:
        if f["name"] == "patient_id":
            f["options"] = [(p.id, p.nama) for p in patients]
            if claim.patient_id:
                f["value"] = claim.patient_id
        if f["name"] == "visit_id":
            f["options"] = [(v.id, f"{v.id} - {v.tanggal_kunjungan}") for v in visits]
            if claim.visit_id:
                f["value"] = claim.visit_id
        if f["name"] == "hospital_id":
            f["options"] = [(h.id, h.nama) for h in hospitals]
            if claim.hospital_id:
                f["value"] = claim.hospital_id
        if claim.medical_record and f["name"] in claim.medical_record.__dict__:
            f["value"] = getattr(claim.medical_record, f["name"])

    return templates.TemplateResponse(template_name, {
        "request": request,
        "mode": "edit",
        "record": claim,
        "csrf_token": csrf_token,
        "current_user": user,
        "user": user,
        "role": user.role if isinstance(user.role, str) else user.role[0],
        "isDoctor": is_doctor,
        "isVerifikator": (user.role == "verifikator") if isinstance(user.role, str) else ("verifikator" in user.role),
        "fields": fields,
        "sim": sim,
        "summ": summ,
        "claim_medical_record_fields": fields,
    })

# ==================================================
# AI RECOMMENDATION + SUMMARY / EVALUASI + SIMULASI
# ==================================================

@router.post("/ai/recommendation")
def ai_recommendation(payload: dict = Body(...), db: Session = Depends(get_db)):
    print(f"[ROUTER] /ai/recommendation hit with payload={payload}")  # 🔥
    claim_id = int(payload["claim_id"])
    data = claim_service.ai_recommendation(db, claim_id)
    return {"status": "ok", "data": data}


@router.post("/ai/summary/{claim_id}")
def ai_summary(claim_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    result = claim_service.ai_summary_service(db, claim_id, payload)
    return result

@router.get("/{claim_id}/simulations")
def get_simulations(claim_id: int, db: Session = Depends(get_db)):
    return claim_service.get_simulations_service(db, claim_id)

# ==================================================
# UPDATE DRAFT / FINALIZE
# ==================================================

@router.post("/{claim_id}/update-draft", name="save_draft")
def update_claim_draft(request: Request, claim_id: int, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor")), _=Depends(require_csrf_dep), form_data: dict = Depends(get_form_as_dict)):
    claim_service.update_claim_draft_service(db, claim_id, user, form_data)
    flash(request, "Draft klaim berhasil diperbarui", "success")
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/{claim_id}/finalize", name="finalize_claim")
def finalize_claim(request: Request, claim_id: int, db: Session = Depends(get_db), user=Depends(require_roles_session("verifikator")), _=Depends(require_csrf_dep), form_data: dict = Depends(get_form_as_dict)):
    claim_service.finalize_claim_service(db, claim_id, user, form_data)
    flash(request, "Klaim difinalisasi", "success")
    return RedirectResponse(url="/dashboard", status_code=303)

# ==================================================
# DELETE
# ==================================================

@router.post("/delete/{id}", name="delete_claim")
def delete_claim(id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor", "verifikator")), _=Depends(require_csrf_dep)):
    claim_crud.delete_claim(db, id)
    flash(request, "Klaim berhasil dihapus !", "success")
    return RedirectResponse("/claims", status_code=303)

# ==================================================
# AI DETAIL & REGULATIONS 
# ==================================================
@router.get("/ai/recommendation/detail")
def ai_recommendation_detail_get(claim_id: int, rec_type: str, item_id: int, db: Session = Depends(get_db)):
    return claim_service.ai_recommendation_detail(db, claim_id, rec_type, item_id)

@router.get("/{claim_id}/regulations")
def get_regulations(
    claim_id: int,
    diagnosis_id: int | None = None,
    procedure_id: int | None = None,
    diagnosis_evaluation_id: int | None = None,
    procedure_evaluation_id: int | None = None,
    idrg_diagnosis_id: int | None = None,
    idrg_summary_id: int | None = None,
    db: Session = Depends(get_db)
):
    return claim_service.get_regulations_payload(
        db, claim_id,
        diagnosis_id=diagnosis_id,
        procedure_id=procedure_id,
        diagnosis_evaluation_id=diagnosis_evaluation_id,
        procedure_evaluation_id=procedure_evaluation_id,
        idrg_diagnosis_id=idrg_diagnosis_id,
        idrg_summary_id=idrg_summary_id
    )

# ==================================================
# SEARCH AUTOCOMPLETE
# ==================================================

from ..utils.dummy_data import dummy_diagnosis_list, dummy_diagnosis_detail

@router.get("/search/diagnosis")
def search_diagnosis(query: str):
    dummy = dummy_diagnosis_list()
    results = [d for d in dummy if query.lower() in d["name"].lower()]
    return {"status": "ok", "data": results}

@router.get("/search/diagnosis/detail/{code}")
def search_diagnosis_detail(code: str):
    return {"status": "ok", "data": dummy_diagnosis_detail(code)}


@router.get("/{claim_id}/notes")
def get_notes(claim_id: int, db: Session = Depends(get_db)):
    notes = db.query(models.ClaimNote).filter(models.ClaimNote.claim_id == claim_id).all()
    return {"data": [
        {
            "id": n.id,
            "item_id": n.item_id,
            "role": n.role,
            "user_id": n.user_id,
            "note_text": n.note_text,
            "timestamp": n.timestamp.isoformat()
        } for n in notes
    ]}
