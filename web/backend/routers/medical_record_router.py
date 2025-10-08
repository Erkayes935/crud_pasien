from fastapi import APIRouter, Request, Depends, HTTPException, Query, Body
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, datetime
import json
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
import io
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


# =========================================================
# 📤 EXPORT MEDICAL RECORDS (Excel)
# =========================================================
@router.get("/medical-records/export", name="export_medical_records")
def export_medical_records(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Cari pasien berdasarkan nama"),
    status: str | None = Query(None, description="Filter status rekam medis (final/draft)"),
    date: str | None = Query(None, description="Tanggal rekam medis (YYYY-MM-DD)"),
    start_date: str | None = Query(None, description="Tanggal awal rentang"),
    end_date: str | None = Query(None, description="Tanggal akhir rentang"),
    user=Depends(require_roles_session("doctor", "admin_rs", "superadmin")),
):
    """
    Ekspor data rekam medis ke Excel — mengikuti filter tampilan daftar.
    Jika user sudah melakukan filter (q, status, date), maka hasil ekspor menyesuaikan.
    """
    # Base query
    query = db.query(models.MedicalRecord).join(models.Patient)

    # 🔹 Filter: Nama Pasien
    if q:
        query = query.filter(models.Patient.nama.ilike(f"%{q}%"))

    # 🔹 Filter: Status
    if status:
        if status == "final":
            query = query.filter(models.MedicalRecord.is_final == True)
        elif status == "draft":
            query = query.filter(models.MedicalRecord.is_final == False)

    # 🔹 Filter: Tanggal tunggal
    from datetime import date as date_cls
    if date:
        try:
            parsed_date = date_cls.fromisoformat(date)
            query = query.filter(models.MedicalRecord.notes_date == parsed_date)
        except ValueError:
            pass  # abaikan jika kosong / tidak valid

    # 🔹 Filter: Rentang tanggal (opsional)
    if start_date:
        try:
            start_date_val = date_cls.fromisoformat(start_date)
            query = query.filter(models.MedicalRecord.notes_date >= start_date_val)
        except ValueError:
            pass
    if end_date:
        try:
            end_date_val = date_cls.fromisoformat(end_date)
            query = query.filter(models.MedicalRecord.notes_date <= end_date_val)
        except ValueError:
            pass

    # Ambil data
    records = query.order_by(models.MedicalRecord.notes_date.desc()).all()
    if not records:
        raise HTTPException(status_code=404, detail="Tidak ada data rekam medis untuk diekspor.")

    # =========================================================
    # 📘 Membuat file Excel
    # =========================================================
    wb = Workbook()
    ws = wb.active
    ws.title = "Rekam Medis"

    headers = [
        "ID Rekam Medis", "Tanggal Catatan", "Jenis Rekam",
        "Nama Pasien", "No. RM", "Jenis Kelamin", "Tanggal Lahir",
        "Dokter", "Rumah Sakit", "Keluhan", "Diagnosis Awal",
        "Diagnosis Akhir", "Tindakan", "Obat",
        "Catatan Dokter", "Validasi Fornas", "Status Final"
    ]
    ws.append(headers)

    for rec in records:
        patient = rec.patient
        hospital = rec.visit.hospital if rec.visit else None

        ws.append([
            rec.id,
            rec.notes_date.strftime("%Y-%m-%d") if rec.notes_date else "-",
            rec.record_type or "-",
            patient.nama if patient else "-",
            patient.no_rm if patient else "-",
            patient.jenis_kelamin if patient else "-",
            patient.tanggal_lahir.strftime("%Y-%m-%d") if (patient and patient.tanggal_lahir) else "-",
            rec.doctor_name or "-",
            hospital.nama if hospital else "-",
            rec.keluhan or "-",
            rec.diagnosis_awal or "-",
            rec.diagnosis_akhir or "-",
            rec.tindakan or "-",
            rec.obat or "-",
            rec.notes_doctor or "-",
            rec.validasi_fornas or "-",
            "Final" if rec.is_final else "Draft",
        ])

    # Atur lebar kolom otomatis
    for col in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max(12, min(max_length + 2, 60))

    # Simpan ke buffer memory
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"rekam_medis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

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
