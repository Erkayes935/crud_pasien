from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from backend.form_configs import form_configs
from backend.database import get_db
from backend.utils.templates import templates
from backend.utils.flash import flash
from backend.auth import require_roles_session, require_csrf_dep, issue_csrf_token
import backend.crud.hospital as hospital_crud

router = APIRouter()


# =========================
# LIST HOSPITALS
# =========================
@router.get("/hospitals")
def list_hospitals(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin", "admin_rs")),
):
    hospitals = hospital_crud.get_hospitals(db)
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "hospital_list.html",
        {
            "request": request,
            "hospitals": hospitals,
            "user": user,
            "csrf_token": csrf_token,
            "current_user": user,
        },
    )


# =========================
# ADD HOSPITAL
# =========================
@router.get("/hospitals/add")
def add_hospital_form(
    request: Request,
    user=Depends(require_roles_session("superadmin", "admin_rs")),
):
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "hospital_form.html",
        {
            "request": request,
            "mode": "add",
            "user": user,
            "csrf_token": csrf_token,
            "current_user": user,
            "fields": form_configs["hospital"],
        },
    )


@router.post("/hospitals/add", name="add_hospital")
def add_hospital(
    request: Request,
    nama: Optional[str] = Form(None),
    kode_hospital: Optional[str] = Form(None),
    tipe_hospital: Optional[str] = Form(None),
    jenis_hospital: Optional[str] = Form(None),
    alamat: Optional[str] = Form(None),
    telepon: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    status_akreditasi: Optional[str] = Form(None),
    status_bridging: Optional[str] = Form(None),
    jumlah_tempat_tidur: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep),
):
    hospital_crud.create_hospital(db, {
        "nama": nama,
        "kode_hospital": kode_hospital,
        "tipe_hospital": tipe_hospital,
        "jenis_hospital": jenis_hospital,
        "alamat": alamat,
        "telepon": telepon,
        "email": email,
        "status_akreditasi": status_akreditasi,
        "status_bridging": status_bridging,
        "jumlah_tempat_tidur": jumlah_tempat_tidur,
        "admin_id": current_user.id,
    })
    flash(request, "Hospital berhasil ditambahkan!", "success")
    return RedirectResponse(url="/hospitals", status_code=303)


# =========================
# EDIT HOSPITAL
# =========================
@router.get("/hospitals/{hospital_id}/edit", name="edit_hospital")
def edit_hospital_form(
    request: Request,
    hospital_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
):
    hospital = hospital_crud.get_hospital_by_id(db, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "hospital_form.html",
        {
            "request": request,
            "mode": "edit",
            "record": hospital,
            "csrf_token": csrf_token,
            "current_user": current_user,
            "user": current_user,
            "fields": form_configs["hospital"],
        },
    )


@router.post("/hospitals/{hospital_id}/edit", name="edit_hospital")
def edit_hospital(
    request: Request,
    hospital_id: int,
    nama: Optional[str] = Form(None),
    kode_hospital: Optional[str] = Form(None),
    tipe_hospital: Optional[str] = Form(None),
    jenis_hospital: Optional[str] = Form(None),
    alamat: Optional[str] = Form(None),
    telepon: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    status_akreditasi: Optional[str] = Form(None),
    status_bridging: Optional[str] = Form(None),
    jumlah_tempat_tidur: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep),
):
    updated = hospital_crud.update_hospital(db, hospital_id, {
        "nama": nama,
        "kode_hospital": kode_hospital,
        "tipe_hospital": tipe_hospital,
        "jenis_hospital": jenis_hospital,
        "alamat": alamat,
        "telepon": telepon,
        "email": email,
        "status_akreditasi": status_akreditasi,
        "status_bridging": status_bridging,
        "jumlah_tempat_tidur": jumlah_tempat_tidur,
    })

    if not updated:
        raise HTTPException(status_code=404, detail="Hospital not found")

    flash(request, "Hospital berhasil diperbarui!", "success")
    return RedirectResponse(url="/hospitals", status_code=303)


# =========================
# DELETE HOSPITAL (SOFT)
# =========================
@router.post("/hospitals/{hospital_id}/delete")
def delete_hospital(
    request: Request,
    hospital_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs", "superadmin")),
    _=Depends(require_csrf_dep),
):
    ok = hospital_crud.delete_hospital(db, hospital_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Hospital not found")

    flash(request, "Rumah sakit berhasil dihapus !", "success")
    return RedirectResponse("/hospitals", status_code=303)