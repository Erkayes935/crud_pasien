from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional

from backend import models
from backend.database import get_db
from backend.utils.templates import templates
from backend.utils.flash import flash
from backend.auth import require_roles_session, require_csrf_dep, issue_csrf_token
from backend.crud import visit as visit_crud
from backend.form_configs import form_configs

router = APIRouter()


# =========================
# LIST VISITS
# =========================
@router.get("/visits")
def list_visits(
    request: Request,
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "admin_rs")),
):
    visits = visit_crud.get_visits(db, search)
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("visit_list.html", {
        "request": request,
        "visits": visits,
        "user": user,
        "csrf_token": csrf_token,
        "current_user": user,
        "flow": None,
        "patient": None,
    })

# =========================
# ADD VISIT
# =========================
@router.get("/visits/add")
def add_visit_form(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "admin_rs")),
):
    patient_id = request.query_params.get("patient_id")
    patient = db.query(models.Patient).get(patient_id) if patient_id else None
    patients = db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
    hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
    csrf_token = issue_csrf_token(request)

    fields = form_configs["visit"].copy()
    for f in fields:
        if f["name"] == "hospital_name" and user.hospital:
            f["type"] = "readonly"
            f["value"] = user.hospital.nama
            f["hidden_name"] = "hospital_id"
            f["hidden_value"] = user.hospital_id

        if f["name"] == "doctor_name":
            f["type"] = "readonly"
            f["value"] = user.name
            f["hidden_name"] = "doctor_id"
            f["hidden_value"] = user.id

        if f["name"] == "patient_id":
            f["options"] = [(p.id, p.nama) for p in patients]

    return templates.TemplateResponse("visit_form.html", {
        "request": request,
        "mode": "add",
        "user": user,
        "visit": None,
        "flow": None,
        "hospitals": hospitals,
        "patient": patient,
        "patient_id": patient_id,
        "patients": patients,
        "csrf_token": csrf_token,
        "current_user": user,
        "fields": fields,
    })


@router.post("/visits/add", name="add_visit")
def add_visit(
    request: Request,
    patient_id: Optional[int] = Form(None),
    hospital_id: Optional[int] = Form(None),
    eksternal_id: Optional[str] = Form(None),
    sumber: Optional[str] = Form(None),
    poli: Optional[str] = Form(None),
    doctor_id: Optional[int] = Form(None),
    doctor_name: Optional[str] = Form(None),
    tanggal_kunjungan: Optional[date] = Form(None),
    jenis_kunjungan: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "admin_rs")),
    _=Depends(require_csrf_dep),
):
    visit_crud.create_visit(db, {
        "patient_id": patient_id,
        "hospital_id": current_user.hospital_id,
        "eksternal_id": eksternal_id,
        "sumber": sumber,
        "poli": poli,
        "doctor_id": current_user.id,
        "doctor_name": current_user.name,
        "tanggal_kunjungan": tanggal_kunjungan,
        "jenis_kunjungan": jenis_kunjungan,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_deleted": False,
        "is_dummy": True,
    })
    flash(request, "Kunjungan berhasil ditambahkan!", "success")
    return RedirectResponse(url="/visits", status_code=303)


# =========================
# EDIT VISIT
# =========================
@router.get("/visits/edit/{visit_id}", name="edit_visit")
def edit_visit_form(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "admin_rs")),
):
    visit = visit_crud.get_visit_by_id(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    patients = db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
    hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
    csrf_token = issue_csrf_token(request)

    fields = form_configs["visit"].copy()
    for f in fields:
        if f["name"] == "patient_id":
            f["options"] = [(p.id, p.nama) for p in patients]
        if f["name"] == "hospital_id":
            f["options"] = [(h.id, h.nama) for h in hospitals]

    return templates.TemplateResponse("visit_form.html", {
        "request": request,
        "mode": "edit",
        "record": visit,
        "csrf_token": csrf_token,
        "current_user": user,
        "user": user,
        "flow": None,
        "hospitals": hospitals,
        "patients": patients,
        "fields": fields,
    })


@router.post("/visits/edit/{visit_id}", name="edit_visit")
def edit_visit(
    request: Request,
    visit_id: int,
    patient_id: Optional[int] = Form(None),
    hospital_id: Optional[int] = Form(None),
    eksternal_id: Optional[str] = Form(None),
    sumber: Optional[str] = Form(None),
    poli: Optional[str] = Form(None),
    doctor_id: Optional[int] = Form(None),
    doctor_name: Optional[str] = Form(None),
    tanggal_kunjungan: Optional[date] = Form(None),
    jenis_kunjungan: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "admin_rs")),
    _=Depends(require_csrf_dep),
):
    updated = visit_crud.update_visit(db, visit_id, {
        "patient_id": patient_id,
        "hospital_id": current_user.hospital_id,
        "eksternal_id": eksternal_id,
        "sumber": sumber,
        "poli": poli,
        "doctor_id": current_user.id,
        "doctor_name": current_user.name,
        "tanggal_kunjungan": tanggal_kunjungan,
        "jenis_kunjungan": jenis_kunjungan,
        "updated_at": datetime.utcnow(),
        "is_deleted": False,
        "is_dummy": True,
    })
    if not updated:
        raise HTTPException(status_code=404, detail="Visit not found")

    flash(request, "Kunjungan berhasil diperbarui!", "success")
    return RedirectResponse(url="/visits", status_code=303)


# =========================
# DELETE VISIT
# =========================
@router.post("/visits/delete/{visit_id}")
def delete_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    request: Request = None,
    _=Depends(require_csrf_dep),
):
    ok = visit_crud.delete_visit(db, visit_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Visit not found")

    flash(request, "Visit berhasil dihapus !", "success")
    return RedirectResponse("/visits", status_code=303)
