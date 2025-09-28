# backend/routers/patient_router.py
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from datetime import datetime, timedelta
from typing import Optional
import io, json
from openpyxl import Workbook

from backend import models
from backend.database import get_db
from backend.utils.templates import templates
from backend.utils.flash import flash
from backend.auth import require_roles_session, require_csrf_dep, issue_csrf_token
from backend.crud import patient as patient_crud
from backend.form_configs import form_configs

router = APIRouter()

# =========================
# LIST PATIENTS
# =========================
@router.get("/patients")
def list_patients(
    request: Request,
    flow: Optional[str] = None,
    search: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))
):
    query = db.query(models.Patient)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                func.lower(func.trim(models.Patient.nama)).like(pattern.lower()),
                func.lower(func.trim(models.Patient.no_ktp)).like(pattern.lower()),
                func.lower(func.trim(models.Patient.no_rm)).like(pattern.lower()),
                func.lower(func.trim(models.Patient.no_bpjs)).like(pattern.lower()),
            )
        )

    patients = (
        query.filter(models.Patient.is_deleted == False)
             .options(joinedload(models.Patient.hospital))
             .order_by(models.Patient.id.desc())
             .all()
    )
    csrf_token = issue_csrf_token(request)

    return templates.TemplateResponse("patient_list.html", {
        "request": request,
        "patients": patients,
        "user": user,
        "current_user": user,
        "search": search,
        "mode": mode,
        "flow": flow,
        "csrf_token": csrf_token,
    })

# =========================
# ADD PATIENT (FORM + SUBMIT)
# =========================
@router.get("/patients/add", name="add_patient", response_class=HTMLResponse)
def add_form(
    request: Request,
    user=Depends(require_roles_session("doctor")),
    db: Session = Depends(get_db),
):
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("patient_form.html", {
        "request": request,
        "mode": "add",
        "patient": None,
        "csrf_token": csrf_token,
        "user": user,
        "current_user": user,
        "fields": form_configs["patient"],
        "patients": None,
    })

@router.post("/patients/add", name="add_patient")
def add_patient(
    request: Request,
    flow: Optional[str] = None,
    no_ktp: Optional[str] = Form(...),
    no_bpjs: Optional[str] = Form(...),
    no_rm: Optional[str] = Form(...),
    nama: str = Form(...),
    tanggal_lahir: Optional[str] = Form(None),
    jenis_kelamin: Optional[str] = Form(None),
    alamat: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    no_hp: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    try:
        patient_crud.create_patient(db, {
            "no_ktp": no_ktp or None,
            "no_bpjs": no_bpjs or None,
            "no_rm": no_rm or None,
            "hospital_id": user.hospital_id,
            "nama": nama,
            "tanggal_lahir": tanggal_lahir or None,
            "jenis_kelamin": jenis_kelamin or None,
            "alamat": alamat or None,
            "email": email or None,
            "no_hp": no_hp or None,
            "created_at": datetime.now() - timedelta(days=7),
            "updated_at": datetime.now(),
            "is_deleted": False,
            "is_dummy": True,
        })
        flash(request, "Pasien berhasil ditambahkan!", "success")
        return RedirectResponse(url="/patients", status_code=303)
    except Exception as e:
        error_msg = f"Gagal menambahkan pasien: {str(e)}"
        flash(request, error_msg, "danger")
        return templates.TemplateResponse("patient_form.html", {
            "request": request,
            "fields": form_configs["patient"],
            "mode": "add",
            "patient": {
                "nama": nama,
                "tanggal_lahir": tanggal_lahir,
                "jenis_kelamin": jenis_kelamin,
                "alamat": alamat,
                "email": email,
                "hospital_id": user.hospital_id,
                "no_hp": no_hp,
                "no_ktp": no_ktp,
                "no_bpjs": no_bpjs,
                "no_rm": no_rm,
                "created_at": datetime.now() - timedelta(days=7),
                "updated_at": datetime.now(),
                "is_deleted": False,
                "is_dummy": True,
            },
            "user": user,
            "current_user": user,
            "error_msg": error_msg,
        })

# =========================
# EDIT PATIENT (FORM + SUBMIT)
# =========================
@router.get("/patients/edit/{patient_id}", name="edit_patient")
def edit_form(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
):
    patient = (
        db.query(models.Patient)
          .filter(models.Patient.id == patient_id, models.Patient.is_deleted == False)
          .first()
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")

    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("patient_form.html", {
        "request": request,
        "fields": form_configs["patient"],
        "mode": "edit",
        "record": patient,
        "csrf_token": csrf_token,
        "user": user,
        "current_user": user,
    })

@router.post("/patients/edit/{patient_id}", name="update_patient")
def update_patient(
    patient_id: int,
    request: Request,
    flow: Optional[str] = None,
    no_ktp: Optional[str] = Form(...),
    no_bpjs: Optional[str] = Form(...),
    no_rm: Optional[str] = Form(...),
    nama: str = Form(...),
    tanggal_lahir: Optional[str] = Form(None),
    jenis_kelamin: Optional[str] = Form(None),
    alamat: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    no_hp: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    patient = (
        db.query(models.Patient)
          .filter(models.Patient.id == patient_id, models.Patient.is_deleted == False)
          .first()
    )
    if not patient:
        error_msg = "Pasien tidak ditemukan"
        return templates.TemplateResponse("patient_form.html", {
            "request": request,
            "fields": form_configs["patient"],
            "mode": "edit",
            "patient": None,
            "user": user,
            "current_user": user,
            "error_msg": error_msg,
        })

    try:
        updated = patient_crud.update_patient(db, patient_id, {
            "no_ktp": no_ktp or None,
            "no_bpjs": no_bpjs or None,
            "no_rm": no_rm or None,
            "hospital_id": user.hospital_id,
            "nama": nama,
            "tanggal_lahir": tanggal_lahir or None,
            "alamat": alamat or None,
            "jenis_kelamin": jenis_kelamin or None,
            "email": email or None,
            "no_hp": no_hp or None,
            "updated_at": datetime.now(),
        })
        if not updated:
            raise HTTPException(status_code=404, detail="Pasien tidak ditemukan (update)")
        flash(request, "Pasien berhasil diperbarui!", "success")
        return RedirectResponse(url="/patients", status_code=303)
    except Exception as e:
        error_msg = f"Gagal memperbarui pasien: {str(e)}"
        flash(request, error_msg, "danger")
        return templates.TemplateResponse("patient_form.html", {
            "request": request,
            "fields": form_configs["patient"],
            "mode": "edit",
            "patient": {
                "id": patient_id,
                "no_ktp": no_ktp,
                "no_bpjs": no_bpjs,
                "no_rm": no_rm,
                "hospital_id": user.hospital_id,
                "nama": nama,
                "tanggal_lahir": tanggal_lahir,
                "jenis_kelamin": jenis_kelamin,
                "alamat": alamat,
                "email": email,
                "no_hp": no_hp,
                "updated_at": datetime.now(),
            },
            "user": user,
            "current_user": user,
            "error_msg": error_msg,
        })

# =========================
# DELETE (SOFT)
# =========================
@router.post("/patients/delete/{patient_id}")
def delete_patient(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    ok = patient_crud.delete_patient(db, patient_id)  # soft delete (versi revisi)
    if not ok:
        raise HTTPException(status_code=404, detail="Patient not found")
    flash(request, "Pasien berhasil dihapus!", "success")
    return RedirectResponse("/patients", status_code=303)

# =========================
# EXPORT/IMPORT
# =========================
@router.get("/export")
def export_patients(
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))
):
    patients = (
        db.query(models.Patient)
          .filter(models.Patient.is_deleted == False)
          .all()
    )
    wb = Workbook()
    ws = wb.active
    ws.title = "Patients"
    ws.append(["Nama", "Tanggal Lahir", "Nomor HP", "Alamat", "Email", "No KTP", "No BPJS", "No Rekam Medis"])
    for p in patients:
        ws.append([p.nama, p.tanggal_lahir, p.no_hp, p.alamat, p.email, p.no_ktp, p.no_bpjs, p.no_rm])
    buffer = io.BytesIO()
    wb.save(buffer); buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=patients.xlsx"},
    )

@router.post("/import")
def import_patients(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator")),
    _=Depends(require_csrf_dep),
):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are allowed")
    try:
        raw = file.file.read()
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Invalid JSON structure (expect list)")

    created = 0
    for item in data:
        patient_crud.create_patient(db, {
            "nama": item.get("nama"),
            "tanggal_lahir": item.get("tanggal_lahir"),
            "alamat": item.get("alamat"),
            "email": item.get("email"),
            "no_hp": item.get("no_hp"),
            "no_ktp": item.get("no_ktp"),
            "no_bpjs": item.get("no_bpjs"),
            "no_rm": item.get("no_rm"),
            "hospital_id": getattr(user, "hospital_id", None),
            "created_at": datetime.now() - timedelta(days=7),
            "updated_at": datetime.now(),
            "is_deleted": False,
            "is_dummy": True,
        })
        created += 1

    csrf_token = issue_csrf_token(request)
    return {"status": "success", "count": created, "csrf_token": csrf_token}
