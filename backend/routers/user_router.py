from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from backend import models
from backend.database import get_db
from backend.utils.templates import templates
from backend.utils.flash import flash
from backend.auth import require_roles_session, require_csrf_dep, issue_csrf_token
from backend.crud import user as user_crud
from backend.form_configs import form_configs

router = APIRouter()


# =========================
# LIST USERS
# =========================
@router.get("/users")
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
):
    if current_user.role == "superadmin":
        users = user_crud.get_users_superadmin(db)
    elif current_user.role == "admin_rs":
        users = user_crud.get_users_admin_rs(db, current_user.hospital_id)
    else:
        users = []

    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "user_list.html",
        {
            "request": request,
            "users": users,
            "user": current_user,
            "current_user": current_user,
            "csrf_token": csrf_token,
        },
    )


# =========================
# ADD USER
# =========================
@router.get("/users/add")
def add_user_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
):
    csrf_token = issue_csrf_token(request)
    fields = form_configs["user"].copy()

    for f in fields:
        # Role
        if f["name"] == "role":
            if current_user.role == "superadmin":
                f["type"] = "hidden"
                f["value"] = "admin_rs"
                f["display"] = "Admin RS"
            elif current_user.role == "admin_rs":
                f["type"] = "select"
                f["options"] = [
                    ("doctor", "Dokter"),
                    ("coder", "Coder"),
                    ("verifikator", "Verifikator"),
                    ("costing", "Costing"),
                    ("validator", "Validator"),
                    ("manajemen", "Manajemen"),
                ]

        # Hospital
        if f["name"] == "hospital_id":
            if current_user.role == "superadmin":
                hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
                f["type"] = "select"
                f["options"] = [(h.id, h.nama) for h in hospitals]

            elif current_user.role == "admin_rs":
                f["type"] = "readonly"
                f["value"] = current_user.hospital.nama if current_user.hospital else "-"
                f["hidden_value"] = current_user.hospital_id if current_user.hospital_id else None

    return templates.TemplateResponse(
        "user_form.html",
        {
            "request": request,
            "mode": "add",
            "user": current_user,
            "current_user": current_user,
            "csrf_token": csrf_token,
            "fields": fields,
        },
    )


@router.post("/users/add", name="add_user")
def add_user(
    request: Request,
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    hospital_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep),
):
    if role not in ["admin_rs", "doctor", "coder", "verifikator", "costing", "validator", "manajemen"]:
        raise HTTPException(status_code=400, detail="Role tidak valid")

    if current_user.role == "admin_rs":
        hospital_id = current_user.hospital_id

    user = user_crud.create_user(db, {
        "email": email,
        "name": name,
        "role": role,
        "hospital_id": hospital_id,
    })

    flash(request, "User berhasil ditambahkan!", "success")
    return RedirectResponse(url="/users", status_code=303)


# =========================
# EDIT USER
# =========================
@router.get("/users/{user_id}/edit", name="edit_user")
def edit_user_form(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
):
    target_user = user_crud.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    csrf_token = issue_csrf_token(request)
    fields = form_configs["user"].copy()

    for f in fields:
        if f["name"] == "role":
            if current_user.role == "superadmin":
                f["options"] = [("admin_rs", "Admin RS")]
                f["type"] = "select"
            elif current_user.role == "admin_rs":
                f["options"] = [
                    ("doctor", "Dokter"),
                    ("coder", "Coder"),
                    ("verifikator", "Verifikator"),
                    ("costing", "Costing"),
                    ("validator", "Validator"),
                    ("manajemen", "Manajemen"),
                ]
                f["type"] = "select"

        if f["name"] == "hospital_id":
            if current_user.role == "superadmin":
                hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
                f["type"] = "select"
                f["options"] = [(h.id, h.nama) for h in hospitals]
            elif current_user.role == "admin_rs":
                f["type"] = "readonly"
                f["value"] = current_user.hospital.nama if current_user.hospital else "-"
                f["hidden_value"] = current_user.hospital_id if current_user.hospital_id else None

    return templates.TemplateResponse(
        "user_form.html",
        {
            "request": request,
            "mode": "edit",
            "record": target_user,
            "csrf_token": csrf_token,
            "current_user": current_user,
            "fields": fields,
        },
    )


@router.post("/users/{user_id}/edit", name="edit_user")
def edit_user(
    request: Request,
    user_id: int,
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    hospital_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep),
):
    if role not in ["admin_rs", "doctor", "coder", "verifikator", "costing", "validator", "manajemen"]:
        raise HTTPException(status_code=400, detail="Role tidak valid")

    updated = user_crud.update_user(db, user_id, {
        "name": name,
        "email": email,
        "role": role,
        "hospital_id": hospital_id if current_user.role == "superadmin" else current_user.hospital_id,
    })

    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    flash(request, "User berhasil diperbarui!", "success")
    return RedirectResponse(url="/users", status_code=303)


# =========================
# DELETE USER (SOFT)
# =========================
@router.post("/users/{user_id}/delete", name="delete_user")
def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep),
):
    ok = user_crud.delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")

    flash(request, "User berhasil dihapus!", "success")
    return RedirectResponse(url="/users", status_code=303)
