from fastapi import APIRouter, Request, Depends, HTTPException, Query, Body
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, datetime
import json

from backend import models, form_configs
from backend.database import get_db
from backend.utils.templates import templates
from backend.utils.flash import flash
from backend.auth import require_roles_session, require_csrf_dep, issue_csrf_token
from backend.crud import medical_record as mr_crud

router = APIRouter()


# =========================
# LIST MEDICAL RECORDS
# =========================
@router.get("/medical-records", name="list_medical_records")
def list_medical_records(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    q: str | None = Query(None),
    status: str | None = Query(None),
    date_str: str | None = Query(None, alias="date"),
    user=Depends(require_roles_session("doctor", "admin_rs")),
):
    date_val = None
    if date_str:
        try:
            date_val = date.fromisoformat(date_str)
        except ValueError:
            pass

    records, total = mr_crud.list_medical_records(db, q, status, date_val, page=page, page_size=10)
    total_pages = (total + 10 - 1) // 10

    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("medical_record_list.html", {
        "request": request,
        "medical_records": records,
        "page": page,
        "total_pages": total_pages,
        "q": q,
        "status": status,
        "date": date_str,
        "csrf_token": csrf_token,
        "user": user,
        "current_user": user,
    })


# =========================
# EDIT FORM
# =========================
@router.get("/medical-records/{record_id}/edit", name="edit_medical_record")
def edit_medical_record_form(
    request: Request,
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "admin_rs")),
):
    medical_record = mr_crud.get_record_by_id(db, record_id)
    if not medical_record:
        raise HTTPException(status_code=404, detail="Medical record not found")

    claims = db.query(models.Claim).filter(models.Claim.is_deleted == False).all()
    patients = db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
    csrf_token = issue_csrf_token(request)

    fields = form_configs["claim_medical_record"].copy()
    for f in fields:
        if f["name"] == "patient_id":
            f["options"] = [(p.id, p.nama) for p in patients]
            f["type"] = "select"

    return templates.TemplateResponse("claim_left.html", {
        "request": request,
        "mode": "edit",
        "record_id": record_id,
        "form_config": form_configs["claim_medical_record"],
        "user": current_user,
        "claims": claims,
        "patients": patients,
        "record": medical_record,
        "csrf_token": csrf_token,
        "current_user": current_user,
        "fields": fields,
    })


# =========================
# UPDATE RECORD
# =========================
@router.post("/medical-records/{record_id}/edit", name="update_medical_record")
def update_medical_record(
    request: Request,
    record_id: int,
    update_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "admin_rs")),
):
    record = mr_crud.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")

    # Ambil versi terakhir
    last_version = (
        db.query(models.MedicalRecordLog.version)
        .filter(models.MedicalRecordLog.medical_record_id == record.id)
        .order_by(models.MedicalRecordLog.version.desc())
        .first()
    )
    new_version = (last_version[0] + 1) if last_version else 1

    # Simpan log
    mr_crud.add_log(
        db,
        record_id=record.id,
        action="UPDATED",
        description="Rekam medis diperbarui",
        updated_by=current_user.id,
        snapshot=json.dumps(record.to_dict(), ensure_ascii=False),
    )

    # Update data baru
    updated = mr_crud.update_record(db, record_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Medical record not found")

    flash(request, "Rekam medis berhasil diperbarui!", "success")
    return templates.TemplateResponse("medical_record_detail.html", {
        "request": request,
        "record": updated,
        "logs": updated.logs,
    })


# =========================
# DELETE RECORD
# =========================
@router.post("/medical-records/{record_id}/delete", name="delete_medical_record")
def delete_medical_record(
    record_id: int,
    db: Session = Depends(get_db),
    request: Request = None,
    current_user=Depends(require_roles_session("doctor", "admin_rs")),
    _=Depends(require_csrf_dep),
):
    ok = mr_crud.delete_record(db, record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Medical record not found")

    flash(request, "Medical record berhasil dihapus !", "success")
    return RedirectResponse(url="/medical-records", status_code=303)


# =========================
# LOGS
# =========================
@router.get("/medical-records/{record_id}/logs", name="medical_record_logs")
def medical_record_logs(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor")),
):
    record = mr_crud.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")

    logs = mr_crud.get_logs(db, record_id)
    return templates.TemplateResponse("medical_record_detail.html", {
        "request": request,
        "record": record,
        "logs": logs,
        "user": current_user,
        "current_user": current_user,
    })