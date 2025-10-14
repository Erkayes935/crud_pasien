from fastapi import APIRouter, Request, Depends, Form, HTTPException, File, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from copy import deepcopy
import asyncio
from datetime import datetime

from backend import models, auth  # ⬅️ tambahkan ini
from backend.database import get_db
from backend.utils.templates import templates
from backend.utils.flash import flash
from backend.auth import require_roles_session, require_csrf_dep, issue_csrf_token
import backend.crud.user as user_crud
from backend.form_configs import form_configs

from backend.services.auth0_client import (
    create_auth0_user,
    send_password_invite,
    assign_auth0_roles,
)

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
    if current_user.has_role("superadmin"):
        users = user_crud.get_users_superadmin(db)
    elif current_user.has_role("admin_rs"):
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
    fields = deepcopy(form_configs["user"])

    for f in fields:
        if f["name"] == "role":
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
            allowed = (
                all_roles
                if current_user.has_role("superadmin")
                else [r for r in all_roles if r[0] not in ("superadmin", "admin_rs")]
            )
            f["type"] = "checkbox_group"
            f["options"] = allowed

        elif f["name"] == "hospital_id":
            if current_user.has_role("superadmin"):
                hospitals = db.query(models.Hospital).filter(
                    models.Hospital.is_deleted == False
                ).all()
                f["type"] = "select"
                f["options"] = [(h.id, h.nama) for h in hospitals]
            else:
                f["type"] = "readonly"
                f["value"] = (
                    current_user.hospital.nama if current_user.hospital else "-"
                )
                f["hidden_value"] = current_user.hospital_id

    return templates.TemplateResponse(
        "user_form.html",
        {
            "request": request,
            "mode": "add",
            "current_user": current_user,
            "user": current_user,
            "csrf_token": csrf_token,
            "fields": fields,
            "existing_medical_data": {},
        },
    )


@router.post("/users/add", name="add_user")
async def add_user(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    role: list[str] = Form(...),
    password: Optional[str] = Form(None),   # 🔹 password opsional
    hospital_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep),
):
    # =============================
    # Validasi awal
    # =============================
    if not email:
        raise HTTPException(status_code=400, detail="Email wajib diisi")

    if current_user.has_role("admin_rs"):
        for r in role:
            if r in ["superadmin", "admin_rs"]:
                raise HTTPException(
                    status_code=403,
                    detail="Role tersebut tidak boleh dibuat oleh Admin RS",
                )
        hospital_id = current_user.hospital_id

    # =============================
    # 1️⃣ Buat user di Auth0
    # =============================
    try:
        from backend.services.auth0_client import create_auth0_user
        auth0_data = await create_auth0_user(email=email, name=name, password=password)
        auth0_sub = auth0_data.get("user_id")
        print(f"✅ Auth0 user dibuat: {auth0_sub}")
    except Exception as e:
        err_text = str(e)
        if "PasswordStrengthError" in err_text or "password" in err_text.lower():
            flash(request, "❌ Password terlalu lemah. Gunakan minimal 8 karakter dengan huruf besar, kecil, angka, dan simbol.", "error")
            return RedirectResponse(url="/users/add", status_code=303)
        raise HTTPException(status_code=500, detail=f"Gagal membuat user Auth0: {e}")

    # =============================
    # 2️⃣ Simpan user ke DB lokal
    # =============================
    try:
        user_crud.create_user(
            db,
            {
                "email": email,
                "name": name,
                "role": ",".join(role),
                "hospital_id": hospital_id,
                "auth0_sub": auth0_sub,
            },
        )
        print(f"💾 User lokal tersimpan: {email}")
    except Exception as e:
        print(f"❌ Gagal simpan user ke DB: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan user ke DB: {e}")

    # =============================
    # 3️⃣ Jika password kosong → kirim link reset
    # =============================
    if not password:
        try:
            from backend.services.auth0_client import send_password_invite
            ticket_url = await send_password_invite(email=email)
            print(f"🔗 Link set password: {ticket_url}")
            flash(
                request,
                f"✅ User {email} berhasil dibuat. Link set password dikirim via email.",
                "success",
            )
        except Exception as e:
            print(f"⚠️ Gagal kirim email invite: {e}")
            flash(request, f"User dibuat tapi gagal kirim link set password.", "warning")
    else:
        flash(request, f"✅ User {email} berhasil dibuat dengan password langsung.", "success")

    # =============================
    # 4️⃣ Sinkronisasi role ke Auth0
    # =============================
    try:
        from backend.services.auth0_client import assign_auth0_roles
        await assign_auth0_roles(auth0_sub, role)
        print(f"✅ Role {role} berhasil disinkronkan ke Auth0 untuk {email}")
    except Exception as e:
        print(f"⚠️ Gagal sinkronisasi role Auth0: {e}")
        flash(
            request,
            f"User dibuat tapi gagal sinkronisasi role ke Auth0: {str(e)}",
            "warning",
        )

    # =============================
    # 5️⃣ Redirect
    # =============================
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
            if current_user.has_role("superadmin"):
                allowed = all_roles
            else:
                allowed = [r for r in all_roles if r[0] not in ("superadmin", "admin_rs")]

            f["type"] = "checkbox_group"
            f["options"] = allowed

        elif f["name"] == "hospital_id":
            if current_user.has_role("superadmin"):
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
            "user": current_user,
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


@router.get("/ai-meta/dashboard")
def ai_meta_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin")),  # Hanya superadmin sebagai AI META
):
    """
    Dashboard AI META untuk review regional reports dan rules management.
    
    AI META bisa:
    - Review regional reports dari seluruh RS
    - Approve/reject/convert SE menjadi regional rules
    - Manage rules nasional, bridging, fraud, temporary
    """
    
    # Get semua regional reports yang perlu direview
    all_reports = db.query(models.RegionalReports).order_by(
        models.RegionalReports.created_at.desc()
    ).all()
    
    # Group reports by status for dashboard overview
    reports_by_status = {
        "pending": [r for r in all_reports if r.status == "pending"],
        "reviewed": [r for r in all_reports if r.status == "reviewed"], 
        "converted": [r for r in all_reports if r.status == "converted"],
        "rejected": [r for r in all_reports if r.status == "rejected"]
    }
    
    # Get statistics
    total_reports = len(all_reports)
    pending_count = len(reports_by_status["pending"])
    converted_count = len(reports_by_status["converted"])
    
    # Get rules yang dibuat AI META (layer non-PPK/RS)
    ai_meta_rules = db.query(models.RulesMaster).filter(
        models.RulesMaster.layer.in_(["permenkes", "nasional", "regional", "bridging", "fraud", "temporary"])
    ).order_by(models.RulesMaster.created_at.desc()).limit(20).all()
    
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "ai_meta_dashboard.html",
        {
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "all_reports": all_reports,
            "reports_by_status": reports_by_status,
            "total_reports": total_reports,
            "pending_count": pending_count,
            "converted_count": converted_count,
            "ai_meta_rules": ai_meta_rules,
            "csrf_token": csrf_token
        }
    )


@router.post("/ai-meta/review-report")
async def ai_meta_review_report(
    request: Request,
    report_id: str = Form(...),
    decision: str = Form(...),
    notes: str = Form(""),
    current_user: models.User = Depends(auth.get_current_user_secure),
    db: Session = Depends(get_db),
    _=Depends(require_csrf_dep),
):
    """AI META review regional reports dari RS"""
    
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Only AI META (superadmin) can review reports")

    # Get regional report
    regional_report = db.query(models.RegionalReports).filter(
        models.RegionalReports.id == report_id
    ).first()
    
    if not regional_report:
        raise HTTPException(status_code=404, detail="Regional report not found")

    # Update status based on decision
    if decision == "approve":
        regional_report.status = "reviewed"
        regional_report.reviewed_by = current_user.id
        regional_report.review_notes = notes
        regional_report.reviewed_at = datetime.utcnow()
        message = "SE Report approved dan siap untuk dikonversi ke rules"
    elif decision == "reject":
        regional_report.status = "rejected"
        regional_report.reviewed_by = current_user.id
        regional_report.review_notes = notes
        regional_report.reviewed_at = datetime.utcnow()
        message = "SE Report ditolak"
    else:
        raise HTTPException(status_code=400, detail="Invalid decision")

    db.commit()

    return {"success": True, "message": message}


@router.post("/ai-meta/convert-to-rules")
async def ai_meta_convert_to_rules(
    request: Request,
    report_id: str = Form(...),
    target_layer: str = Form("regional"),
    current_user: models.User = Depends(auth.get_current_user_secure),
    db: Session = Depends(get_db),
    _=Depends(require_csrf_dep),
):
    """Convert approved regional report ke multilayer rules"""
    
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Only AI META can convert reports")

    # Get regional report
    regional_report = db.query(models.RegionalReports).filter(
        models.RegionalReports.id == report_id,
        models.RegionalReports.status == "reviewed"
    ).first()
    
    if not regional_report:
        raise HTTPException(status_code=404, detail="Regional report not found or not reviewed")

    try:
        # Create new rule from regional report
        new_rule = models.RulesMaster(
            diagnosis="CONVERTED-FROM-SE",
            field="regional_conversion", 
            operator="equals",
            value="converted",
            isi=f"Converted from SE: {regional_report.title}",
            layer=target_layer,
            region_id=regional_report.region_id,
            rs_id=regional_report.rs_id,
            status="active",
            created_by=current_user.id,
        )
        
        db.add(new_rule)
        
        # Update regional report status
        regional_report.status = "converted"
        regional_report.converted_to_rules_at = datetime.utcnow()
        
        db.commit()

        return {"success": True, "message": f"SE successfully converted to {target_layer} rules"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@router.post("/ai-meta/bulk-import")
async def ai_meta_bulk_import(
    request: Request,
    rules_file: UploadFile = File(...),
    target_layer: str = Form("nasional"),
    current_user: models.User = Depends(auth.get_current_user_secure),
    db: Session = Depends(get_db),
    _=Depends(require_csrf_dep),
):
    """Bulk import rules dari CSV/Excel file"""
    
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Only AI META can bulk import")

    # Validate file type
    if not rules_file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only CSV/Excel files supported")

    try:
        import pandas as pd
        from io import BytesIO
        
        # Read file
        content = await rules_file.read()
        if rules_file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        else:
            df = pd.read_excel(BytesIO(content))

        # Expected columns: diagnosis, field, operator, value, isi
        required_cols = ['diagnosis', 'field', 'operator', 'value', 'isi']
        if not all(col in df.columns for col in required_cols):
            raise HTTPException(status_code=400, detail=f"CSV must have columns: {required_cols}")

        imported_count = 0
        for _, row in df.iterrows():
            new_rule = models.RulesMaster(
                diagnosis=row['diagnosis'],
                field=row['field'],
                operator=row['operator'],
                value=row['value'],
                isi=row['isi'],
                layer=target_layer,
                status="active",
                created_by=current_user.id,
            )
            db.add(new_rule)
            imported_count += 1

        db.commit()
        return {"success": True, "message": f"Successfully imported {imported_count} rules"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    flash(request, f"User {target.name or target.email} berhasil dihapus.", "success")
    return RedirectResponse(url="/users", status_code=303)
