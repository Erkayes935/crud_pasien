from fastapi import APIRouter, Request, Depends, Form, HTTPException, File, UploadFile
from copy import deepcopy
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from backend import models
from backend.database import get_db
from backend.utils.templates import templates
from backend.utils.flash import flash
from backend import auth
from backend.auth import require_roles_session, require_csrf_dep, issue_csrf_token
import backend.crud.user as user_crud
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
    if current_user.has_role == "superadmin":
        users = user_crud.get_users_superadmin(db)
    elif current_user.has_role == "admin_rs":
        users = user_crud.get_users_admin_rs(db, current_user.hospital_id)
    else:
        users = []

    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "user_list.html",
        {
            "request": request,
            "users": users,
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
    fields = deepcopy(form_configs["user"])

    for f in fields:
        if f["name"] == "role":
            # Semua kemungkinan role
            all_roles = [
                ("superadmin", "Super Admin"),
                ("admin_rs", "Admin RS"),
                ("doctor", "Dokter"),
                ("coder", "Coder"),
                ("verifikator", "Verifikator"),
                ("costing", "Costing"),
                ("validator", "Validator"),
                ("manajemen", "Manajemen"),
            ]
            # Filter role sesuai role login
            if current_user.has_role == "superadmin":
                allowed = all_roles
            else:
                allowed = [r for r in all_roles if r[0] not in ("superadmin", "admin_rs")]

            f["type"] = "checkbox_group"
            f["options"] = allowed

        elif f["name"] == "hospital_id":
            if current_user.has_role == "superadmin":
                hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
                f["type"] = "select"
                f["options"] = [(h.id, h.nama) for h in hospitals]
            else:
                f["type"] = "readonly"
                f["value"] = current_user.hospital.nama if current_user.hospital else "-"
                f["hidden_value"] = current_user.hospital_id

    return templates.TemplateResponse(
        "user_form.html",
        {
            "request": request,
            "mode": "add",
            "current_user": current_user,
            "csrf_token": csrf_token,
            "fields": fields,
            "existing_medical_data": {},
        },
    )


@router.post("/users/add", name="add_user")
def add_user(
    request: Request,
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    role: list[str] = Form(...),
    hospital_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep),
):
    # Validasi role server-side
    if current_user.has_role == "admin_rs":
        for r in role:
            if r in ["superadmin", "admin_rs"]:
                raise HTTPException(status_code=403, detail="Role tersebut tidak boleh dibuat oleh Admin RS")

    role_str = ",".join(role)
    if current_user.has_role == "admin_rs":
        hospital_id = current_user.hospital_id

    user_crud.create_user(db, {
        "email": email,
        "name": name,
        "role": role_str,
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
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    csrf_token = issue_csrf_token(request)
    fields = deepcopy(form_configs["user"])

    for f in fields:
        if f["name"] == "role":
            if target_user.role:
                f["value"] = target_user.role

            all_roles = [
                ("superadmin", "Super Admin"),
                ("admin_rs", "Admin RS"),
                ("doctor", "Dokter"),
                ("coder", "Coder"),
                ("verifikator", "Verifikator"),
                ("costing", "Costing"),
                ("validator", "Validator"),
                ("manajemen", "Manajemen"),
            ]
            if current_user.has_role == "superadmin":
                allowed = all_roles
            else:
                allowed = [r for r in all_roles if r[0] not in ("superadmin", "admin_rs")]

            f["type"] = "checkbox_group"
            f["options"] = allowed

        elif f["name"] == "hospital_id":
            if current_user.has_role == "superadmin":
                hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
                f["type"] = "select"
                f["options"] = [(h.id, h.nama) for h in hospitals]
            else:
                f["type"] = "readonly"
                f["value"] = current_user.hospital.nama if current_user.hospital else "-"
                f["hidden_value"] = current_user.hospital_id

    return templates.TemplateResponse(
        "user_form.html",
        {
            "request": request,
            "mode": "edit",
            "record": target_user,
            "current_user": current_user,
            "csrf_token": csrf_token,
            "fields": fields,
            "existing_medical_data": {},
        },
    )


@router.post("/users/{user_id}/edit", name="edit_user")
def edit_user(
    request: Request,
    user_id: int,
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    role: list[str] = Form(...),
    hospital_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep),
):
    # Validasi role
    if current_user.has_role == "admin_rs":
        for r in role:
            if r in ["superadmin", "admin_rs"]:
                raise HTTPException(status_code=403, detail="Role tersebut tidak boleh dibuat oleh Admin RS")

    role_str = ",".join(role)
    updated = user_crud.update_user(db, user_id, {
        "name": name,
        "email": email,
        "role": role_str,
        "hospital_id": hospital_id if current_user.has_role == "superadmin" else current_user.hospital_id,
    })

    if not updated:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

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
    target = user_crud.get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    # 🚫 Self-delete protection
    if current_user.id == target.id:
        flash(request, "Anda tidak dapat menghapus akun Anda sendiri.", "error")
        return RedirectResponse(url="/users", status_code=303)

    ok = user_crud.delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Gagal menghapus user")

    flash(request, "User berhasil dihapus!", "success")
    return RedirectResponse(url="/users", status_code=303)

# ==================================================
# ADMIN RS - DASHBOARD & MANAGEMENT
# ==================================================

@router.get("/admin-rs/dashboard")
def admin_rs_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("admin_rs")),
):
    """
    Dashboard utama untuk Admin RS dengan tabs yang berfungsi.
    
    Menampilkan:
    - Overview statistik rules & reports  
    - Rules Management (PPK RS & RS Lokal)
    - Regional Reports Management
    - Analytics & Statistics
    """
    # Get user hospital info
    user_rs_id = None
    user_region_id = "jatim"  # Default region
    if hasattr(current_user, 'hospital') and current_user.hospital:
        user_rs_id = current_user.hospital.kode_hospital or f"rs_{current_user.hospital.id}"
    else:
        user_rs_id = "unknown"
    
    # Get rules yang dibuat oleh RS ini
    my_rules = db.query(models.RulesMaster).filter(
        models.RulesMaster.rs_id == user_rs_id,
        models.RulesMaster.layer.in_(["ppk", "rs"])  # PPK RS dan RS Lokal
    ).order_by(models.RulesMaster.created_at.desc()).all()
    
    # Group rules by status
    rules_by_status = {
        "unverified": [r for r in my_rules if r.status == "unverified"],
        "active": [r for r in my_rules if r.status == "active"], 
        "official": [r for r in my_rules if r.status == "official"],
        "rejected": [r for r in my_rules if r.status == "rejected"]
    }
    
    # Get regional reports yang dibuat oleh RS ini
    my_reports = db.query(models.RegionalReports).filter(
        models.RegionalReports.rs_id == user_rs_id
    ).order_by(models.RegionalReports.created_at.desc()).all()
    
    # Group reports by status
    reports_by_status = {
        "pending": [r for r in my_reports if r.status == "pending"],
        "reviewed": [r for r in my_reports if r.status == "reviewed"], 
        "converted": [r for r in my_reports if r.status == "converted"],
        "rejected": [r for r in my_reports if r.status == "rejected"]
    }
    
    # Statistics
    stats = {
        "total_rules": len(my_rules),
        "pending_rules": len(rules_by_status["unverified"]),
        "active_rules": len(rules_by_status["active"]) + len(rules_by_status["official"]),
        "rejected_rules": len(rules_by_status["rejected"]),
        "total_reports": len(my_reports),
        "pending_reports": len(reports_by_status["pending"]),
        "converted_reports": len(reports_by_status["converted"]),
        "rejected_reports": len(reports_by_status["rejected"])
    }
    
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "admin_rs_dashboard.html",
        {
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "my_rules": my_rules,
            "rules_by_status": rules_by_status,
            "my_reports": my_reports,
            "reports_by_status": reports_by_status,
            "stats": stats,
            "rs_id": user_rs_id,
            "csrf_token": csrf_token
        }
    )

# ==================================================
# ADMIN RS - RULES MANAGEMENT
# ==================================================

@router.get("/admin-rs/rules")
def admin_rs_rules_management(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("admin_rs")),
):
    """
    Halaman Rules Management khusus untuk Admin RS.
    
    Admin RS bisa:
    - Lihat semua rules PPK RS & RS Lokal yang sudah dibuat
    - Tambah rule baru (PPK RS atau RS Lokal)
    - Edit rule yang belum di-approve
    - Hapus rule (soft delete)
    """
    # Get rules yang dibuat oleh RS ini (harus sama dengan logic di claim_router.py)
    user_rs_id = None
    if hasattr(current_user, 'hospital') and current_user.hospital:
        user_rs_id = current_user.hospital.kode_hospital or f"rs_{current_user.hospital.id}"
    else:
        user_rs_id = "unknown"
    
    # Import RulesMaster model
    from .. import models
    
    my_rules = db.query(models.RulesMaster).filter(
        models.RulesMaster.rs_id == user_rs_id,
        models.RulesMaster.layer.in_(["ppk", "rs"])  # PPK RS dan RS Lokal
    ).order_by(models.RulesMaster.created_at.desc()).all()
    
    # Group rules by status for better display
    rules_by_status = {
        "unverified": [r for r in my_rules if r.status == "unverified"],
        "active": [r for r in my_rules if r.status == "active"], 
        "official": [r for r in my_rules if r.status == "official"],
        "rejected": [r for r in my_rules if r.status == "rejected"]
    }
    
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "admin_rs_rules.html",
        {
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "my_rules": my_rules,
            "rules_by_status": rules_by_status,
            "total_rules": len(my_rules),
            "rs_id": user_rs_id,
            "csrf_token": csrf_token
        }
    )


@router.get("/admin-rs/regional-reports")
def admin_rs_regional_reports(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("admin_rs")),
):
    """
    Halaman Regional Reports untuk Admin RS.
    
    Admin RS bisa:
    - Laporkan edaran regional (SE) dengan upload PDF
    - Lihat status laporan yang sudah dikirim
    - Track progress review dari AI META
    """
    # Get user's hospital info
    user_rs_id = None
    user_region_id = "jatim"  # Default region
    if hasattr(current_user, 'hospital') and current_user.hospital:
        user_rs_id = current_user.hospital.kode_hospital or f"rs_{current_user.hospital.id}"
    
    # Get regional reports yang dibuat oleh RS ini
    my_reports = db.query(models.RegionalReports).filter(
        models.RegionalReports.rs_id == user_rs_id
    ).order_by(models.RegionalReports.created_at.desc()).all()
    
    # Group reports by status
    reports_by_status = {
        "pending": [r for r in my_reports if r.status == "pending"],
        "reviewed": [r for r in my_reports if r.status == "reviewed"], 
        "converted": [r for r in my_reports if r.status == "converted"],
        "rejected": [r for r in my_reports if r.status == "rejected"]
    }
    
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "admin_rs_regional_reports.html",
        {
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "my_reports": my_reports,
            "reports_by_status": reports_by_status,
            "total_reports": len(my_reports),
            "rs_id": user_rs_id,
            "region_id": user_region_id,
            "csrf_token": csrf_token
        }
    )

# ==================================================
# ADMIN RS - CRUD ENDPOINTS
# ==================================================

@router.post("/admin-rs/add-rule")
def admin_rs_add_rule(
    request: Request,
    layer: str = Form(...),
    diagnosis: str = Form(...),
    field: str = Form(...),
    isi: str = Form(...),
    sumber: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("admin_rs")),
    _=Depends(require_csrf_dep),
):
    """
    Tambah rule baru dari Admin RS.
    """
    # Get user hospital info
    user_rs_id = None
    if hasattr(current_user, 'hospital') and current_user.hospital:
        user_rs_id = current_user.hospital.kode_hospital or f"rs_{current_user.hospital.id}"
    else:
        user_rs_id = "unknown"
    
    # Validate layer (hanya boleh ppk dan rs untuk admin RS)
    if layer not in ['ppk', 'rs']:
        raise HTTPException(status_code=400, detail="Layer tidak valid untuk Admin RS")
    
    try:
        new_rule = models.RulesMaster(
            diagnosis=diagnosis,
            field=field,
            isi=isi,
            sumber=sumber,
            layer=layer,
            status="unverified",  # Perlu review dari superadmin
            rs_id=user_rs_id,
            created_by=current_user.email or "admin_rs"
        )
        
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        
        return {"status": "success", "message": "Rule berhasil ditambahkan", "rule_id": new_rule.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error menambahkan rule: {str(e)}")

@router.post("/admin-rs/add-report")
def admin_rs_add_report(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    pdf_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("admin_rs")),
    _=Depends(require_csrf_dep),
):
    """
    Tambah regional report baru dari Admin RS.
    """
    # Get user hospital info
    user_rs_id = None
    user_region_id = "jatim"  # Default region
    if hasattr(current_user, 'hospital') and current_user.hospital:
        user_rs_id = current_user.hospital.kode_hospital or f"rs_{current_user.hospital.id}"
    else:
        user_rs_id = "unknown"
    
    # Validate PDF file
    if pdf_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File harus berformat PDF")
    
    # Save uploaded file
    try:
        from pathlib import Path
        upload_dir = Path("web/uploads/regional_reports")
        upload_dir.mkdir(exist_ok=True, parents=True)
        
        file_path = upload_dir / f"{user_rs_id}_{int(datetime.now().timestamp())}_{pdf_file.filename}"
        
        with open(file_path, "wb") as f:
            content = pdf_file.file.read()
            f.write(content)
        
        new_report = models.RegionalReports(
            title=title,
            description=description,
            pdf_path=str(file_path),
            status="pending",  # Menunggu review dari AI META
            rs_id=user_rs_id,
            region_id=user_region_id,
            created_by=current_user.email or "admin_rs"
        )
        
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        
        return {"status": "success", "message": "Regional report berhasil dilaporkan", "report_id": new_report.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error menambahkan report: {str(e)}")

@router.delete("/admin-rs/rules/{rule_id}/delete")
def admin_rs_delete_rule(
    rule_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("admin_rs")),
):
    """
    Hapus rule (soft delete) dari Admin RS.
    """
    # Get user hospital info
    user_rs_id = None
    if hasattr(current_user, 'hospital') and current_user.hospital:
        user_rs_id = current_user.hospital.kode_hospital or f"rs_{current_user.hospital.id}"
    else:
        user_rs_id = "unknown"
    
    # Find rule dan pastikan milik RS ini
    rule = db.query(models.RulesMaster).filter(
        models.RulesMaster.id == rule_id,
        models.RulesMaster.rs_id == user_rs_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule tidak ditemukan")
    
    # Hanya bisa hapus rule yang belum di-approve
    if rule.status != "unverified":
        raise HTTPException(status_code=400, detail="Hanya bisa hapus rule yang belum di-approve")
    
    try:
        # Soft delete
        db.delete(rule)
        db.commit()
        
        return {"status": "success", "message": "Rule berhasil dihapus"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error menghapus rule: {str(e)}")


# AI META Dashboard endpoint moved to ai_meta_router.py for better organization and consistent authentication
    flash(request, f"User {target.name or target.email} berhasil dihapus.", "success")
    return RedirectResponse(url="/users", status_code=303)
