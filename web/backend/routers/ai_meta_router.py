"""
Module: backend.routers.ai_meta_router

AI META Dashboard untuk superadmin:
- Bulk import rules untuk layer nasional/bridging/fraud/temporary
- Rule approval workflow (approve/reject rules dari RS)  
- Feedback review system
- Regional reports review
"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import json
import os

from .. import models
from ..database import get_db
from ..auth import require_roles_session, require_csrf_dep, require_csrf_json, issue_csrf_token
from ..utils.templates import templates

router = APIRouter(prefix="/ai-meta", tags=["AI META"])

# ==================================================
# MAIN DASHBOARD
# ==================================================

@router.get("/dashboard", response_class=HTMLResponse)
async def ai_meta_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin"))
):
    """
    AI META Dashboard utama untuk superadmin.
    Menampilkan overview dan akses ke semua fitur AI META.
    """
    
    # Statistik dashboard
    total_rules = db.query(models.RulesMaster).count()
    pending_rules = db.query(models.RulesMaster).filter(
        models.RulesMaster.status == "unverified"
    ).count()
    
    rules_with_feedback = db.query(models.RulesMaster).filter(
        models.RulesMaster.feedback.isnot(None)
    ).count()
    
    pending_regional_reports = db.query(models.RegionalReports).filter(
        models.RegionalReports.status == "pending"
    ).count()
    
    # Recent activities
    recent_rules = db.query(models.RulesMaster).filter(
        models.RulesMaster.status == "unverified"
    ).order_by(desc(models.RulesMaster.created_at)).limit(5).all()
    
    recent_feedback = db.query(models.RulesMaster).filter(
        models.RulesMaster.feedback.isnot(None)
    ).order_by(desc(models.RulesMaster.feedback_date)).limit(5).all()
    
    recent_reports = db.query(models.RegionalReports).filter(
        models.RegionalReports.status == "pending"  
    ).order_by(desc(models.RegionalReports.created_at)).limit(5).all()
    
    stats = {
        "total_rules": total_rules,
        "pending_rules": pending_rules,
        "rules_with_feedback": rules_with_feedback,
        "pending_regional_reports": pending_regional_reports
    }
    
    # Rules by Layer statistics (8 layers)
    all_layers = ["permenkes", "nasional", "ppk", "regional", "rs", "bridging", "fraud", "temporary"]
    rules_by_layer = {}
    
    for layer in all_layers:
        count = db.query(models.RulesMaster).filter(
            models.RulesMaster.layer == layer
        ).count()
        rules_by_layer[layer] = count
    
    # Reports by status statistics
    reports_by_status = {
        "pending": db.query(models.RegionalReports).filter(models.RegionalReports.status == "pending").count(),
        "converted": db.query(models.RegionalReports).filter(models.RegionalReports.status == "converted").count(),
        "rejected": db.query(models.RegionalReports).filter(models.RegionalReports.status == "rejected").count()
    }
    
    # Get AI META rules untuk Rules Management tab (dengan pagination)
    ai_meta_rules = db.query(models.RulesMaster).filter(
        models.RulesMaster.layer.in_(["permenkes", "nasional", "ppk", "regional", "rs", "bridging", "fraud", "temporary"])
    ).order_by(desc(models.RulesMaster.created_at)).limit(10).all()  # 10 rules per halaman
    
    # Get total rules count untuk pagination
    total_ai_meta_rules = db.query(models.RulesMaster).filter(
        models.RulesMaster.layer.in_(["permenkes", "nasional", "ppk", "regional", "rs", "bridging", "fraud", "temporary"])
    ).count()
    
    # Get semua regional reports untuk Regional Reports tab
    all_reports = db.query(models.RegionalReports).order_by(
        desc(models.RegionalReports.created_at)
    ).limit(10).all()
    
    total_reports = db.query(models.RegionalReports).count()
    
    # CRITICAL: Issue CSRF token for POST requests
    csrf_token = issue_csrf_token(request)
    
    # Calculate pagination for AI META rules
    rules_per_page = 10
    total_pages = (total_ai_meta_rules + rules_per_page - 1) // rules_per_page  # Ceiling division
    
    return templates.TemplateResponse("ai_meta_dashboard.html", {
        "request": request,
        "user": user,
        "current_user": user,
        "csrf_token": csrf_token,
        "stats": stats,
        "rules_by_layer": rules_by_layer,
        "reports_by_status": reports_by_status,
        "recent_rules": recent_rules,
        "recent_feedback": recent_feedback,
        "recent_reports": recent_reports,
        "ai_meta_rules": ai_meta_rules,
        "total_ai_meta_rules": total_ai_meta_rules,
        "total_pages": total_pages,
        "all_reports": all_reports,
        "total_reports": total_reports,
        "pending_count": reports_by_status["pending"],
        "converted_count": reports_by_status["converted"]
    })

# ==================================================
# RULES MANAGEMENT
# ==================================================

@router.get("/rules", response_class=HTMLResponse)
async def ai_meta_rules(
    request: Request,
    status: Optional[str] = None,
    layer: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin"))
):
    """
    Halaman manajemen rules untuk AI META.
    Filter berdasarkan status dan layer.
    """
    
    query = db.query(models.RulesMaster)
    
    if status:
        query = query.filter(models.RulesMaster.status == status)
    
    if layer:
        query = query.filter(models.RulesMaster.layer == layer)
        
    rules = query.order_by(desc(models.RulesMaster.created_at)).all()
    
    # Count per status untuk tabs
    status_counts = {
        "unverified": db.query(models.RulesMaster).filter(models.RulesMaster.status == "unverified").count(),
        "official": db.query(models.RulesMaster).filter(models.RulesMaster.status == "official").count(), 
        "active": db.query(models.RulesMaster).filter(models.RulesMaster.status == "active").count(),
        "rejected": db.query(models.RulesMaster).filter(models.RulesMaster.status == "rejected").count(),
    }
    
    return templates.TemplateResponse("ai_meta_rules.html", {
        "request": request,
        "user": user,
        "current_user": user,
        "rules": rules,
        "status_counts": status_counts,
        "current_status": status,
        "current_layer": layer
    })

@router.post("/rules/{rule_id}/approve")
async def approve_rule(
    rule_id: int,
    review_notes: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin"))
):
    """
    Approve rule yang disubmit oleh RS.
    """
    
    rule = db.query(models.RulesMaster).filter(models.RulesMaster.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule.status = "official"
    rule.approved_by = user.email
    rule.approved_date = datetime.now()
    rule.review_notes = review_notes
    
    db.commit()
    
    return {"status": "success", "message": "Rule berhasil di-approve"}

@router.post("/rules/{rule_id}/reject")
async def reject_rule(
    rule_id: int,
    review_notes: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin"))
):
    """
    Reject rule yang disubmit oleh RS.
    """
    
    rule = db.query(models.RulesMaster).filter(models.RulesMaster.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule.status = "rejected"
    rule.approved_by = user.email
    rule.approved_date = datetime.now()
    rule.review_notes = review_notes
    
    db.commit()
    
    return {"status": "success", "message": "Rule berhasil di-reject"}

# ==================================================
# BULK IMPORT SYSTEM
# ==================================================

@router.get("/bulk-import", response_class=HTMLResponse)
async def bulk_import_form(
    request: Request,
    user=Depends(require_roles_session("superadmin"))
):
    """
    Halaman bulk import rules untuk layer nasional/bridging/fraud/temporary.
    """
    
    return templates.TemplateResponse("ai_meta_bulk_import.html", {
        "request": request,
        "user": user,
        "current_user": user
    })

# ==================================================
# FEEDBACK REVIEW SYSTEM
# ==================================================

@router.get("/feedback", response_class=HTMLResponse)
async def feedback_review(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin"))
):
    """
    Halaman review feedback dari RS.
    """
    
    rules_with_feedback = db.query(models.RulesMaster).filter(
        models.RulesMaster.feedback.isnot(None)
    ).order_by(desc(models.RulesMaster.feedback_date)).all()
    
    return templates.TemplateResponse("ai_meta_feedback.html", {
        "request": request,
        "user": user,
        "current_user": user,
        "rules_with_feedback": rules_with_feedback
    })

# ==================================================
# REGIONAL REPORTS REVIEW
# ==================================================

@router.get("/regional-reports", response_class=HTMLResponse)
async def regional_reports_review(
    request: Request,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin"))
):
    """
    Halaman review regional reports dari RS.
    """
    
    query = db.query(models.RegionalReports)
    
    if status:
        query = query.filter(models.RegionalReports.status == status)
    
    reports = query.order_by(desc(models.RegionalReports.created_at)).all()
    
    return templates.TemplateResponse("ai_meta_regional_reports.html", {
        "request": request,
        "user": user,
        "current_user": user,
        "reports": reports,
        "current_status": status
    })

@router.post("/regional-reports/{report_id}/review")
async def review_regional_report(
    report_id: int,
    action: str = Form(...),  # "approve" or "reject"
    review_notes: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin"))
):
    """
    Review regional report (approve/reject).
    """
    
    report = db.query(models.RegionalReports).filter(models.RegionalReports.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if action == "approve":
        report.status = "reviewed"
    elif action == "reject":
        report.status = "rejected"  
    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    report.reviewed_by = user.email
    report.reviewed_date = datetime.now()
    report.review_notes = review_notes
    
    db.commit()
    
    return {"status": "success", "message": f"Report berhasil {action}"}

# ==================================================
# MISSING ENDPOINTS - FIXED
# ==================================================

@router.post("/bulk-import")
async def bulk_import_rules(
    request: Request,
    rules_file: UploadFile = File(...),
    target_layer: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin")),
    _=Depends(require_csrf_dep)
):
    """
    Bulk import rules dari file CSV/JSON ke layer tertentu.
    """
    print(f"🔧 Bulk import called by user: {user.email}, role: {user.role}")
    print(f"📁 File: {rules_file.filename}, Target layer: {target_layer}")
    
    try:
        # Validasi file type
        if not rules_file.filename.endswith(('.csv', '.json')):
            raise HTTPException(status_code=400, detail="File harus berformat CSV atau JSON")
        
        content = await rules_file.read()
        
        if rules_file.filename.endswith('.json'):
            parsed_json = json.loads(content)
            # Handle both single object and array of objects
            if isinstance(parsed_json, dict):
                rules_data = [parsed_json]  # Convert single object to array
            elif isinstance(parsed_json, list):
                rules_data = parsed_json
            else:
                raise HTTPException(status_code=400, detail="JSON harus berupa object atau array of objects")
        else:
            # Handle CSV format
            import csv
            import io
            csv_content = io.StringIO(content.decode('utf-8'))
            reader = csv.DictReader(csv_content)
            rules_data = list(reader)
        
        success_count = 0
        error_count = 0
        
        for rule_data in rules_data:
            try:
                # Ensure rule_data is a dictionary
                if isinstance(rule_data, str):
                    print(f"Skipping string data: {rule_data}")
                    error_count += 1
                    continue
                
                if not isinstance(rule_data, dict):
                    print(f"Invalid data type: {type(rule_data)}, data: {rule_data}")
                    error_count += 1
                    continue
                
                # Skip metadata fields
                if rule_data.get('_layer_explanation'):
                    continue
                
                # Create new rule
                new_rule = models.RulesMaster(
                    diagnosis=rule_data.get('diagnosis', ''),
                    field=rule_data.get('field', ''),
                    layer=target_layer,
                    isi=rule_data.get('isi', ''),
                    sumber=rule_data.get('sumber', ''),
                    rs_id=rule_data.get('rs_id'),
                    region_id=rule_data.get('region_id'),
                    status='official',
                    created_by=user.email,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                db.add(new_rule)
                success_count += 1
                print(f"✅ Imported rule: {rule_data.get('diagnosis', 'Unknown')} - {rule_data.get('field', 'Unknown')}")
                
            except Exception as e:
                print(f"❌ Error importing rule: {str(e)}")
                error_count += 1
                continue
        
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": f"Import berhasil: {success_count} rules, gagal: {error_count}",
            "success_count": success_count,
            "error_count": error_count
        })
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error bulk import: {str(e)}")

@router.post("/add-rule")
async def add_national_rule(
    request: Request,
    diagnosis: str = Form(...),
    field: str = Form(...),
    isi: str = Form(...),
    sumber: str = Form(...),
    layer: str = Form("nasional"),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin")),
    _=Depends(require_csrf_dep)
):
    """
    Tambah rule nasional baru.
    """
    try:
        new_rule = models.RulesMaster(
            diagnosis=diagnosis,
            field=field,
            layer=layer,
            isi=isi,
            sumber=sumber,
            status='official',  # Auto-approved untuk superadmin
            created_by=user.email,
            approved_by=user.email,  # Self-approved
            approved_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(new_rule)
        db.commit()
        
        return JSONResponse({
            "status": "success",
            "message": "Rule nasional berhasil ditambahkan",
            "rule_id": new_rule.id
        })
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error menambah rule: {str(e)}")

@router.put("/edit-rule/{rule_id}")
async def edit_rule(
    rule_id: int,
    request: Request,
    diagnosis: str = Form(...),
    field: str = Form(...),
    isi: str = Form(...),
    sumber: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin")),
    _=Depends(require_csrf_dep)
):
    """
    Edit rule yang sudah ada.
    """
    try:
        rule = db.query(models.RulesMaster).filter(models.RulesMaster.id == rule_id).first()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule tidak ditemukan")
        
        rule.diagnosis = diagnosis
        rule.field = field
        rule.isi = isi
        rule.sumber = sumber
        rule.updated_at = datetime.now()
        
        db.commit()
        
        return JSONResponse({
            "status": "success", 
            "message": "Rule berhasil diupdate"
        })
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error mengedit rule: {str(e)}")

@router.delete("/delete-rule/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin"))
):
    """
    Hapus rule dari database.
    """
    try:
        rule = db.query(models.RulesMaster).filter(models.RulesMaster.id == rule_id).first()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule tidak ditemukan")
        
        print(f"🗑️ Attempting to delete rule ID: {rule_id}, diagnosis: {rule.diagnosis}")
        
        db.delete(rule)
        db.commit()
        
        print(f"✅ Rule ID {rule_id} successfully deleted")
        
        return JSONResponse({
            "status": "success",
            "message": f"Rule ID {rule_id} berhasil dihapus"
        })
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error menghapus rule: {str(e)}")

@router.get("/rules/{rule_id}")
async def get_single_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin"))
):
    """
    Get single rule data untuk edit form.
    """
    try:
        rule = db.query(models.RulesMaster).filter(models.RulesMaster.id == rule_id).first()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule tidak ditemukan")
        
        return {
            "status": "success",
            "data": {
                "id": rule.id,
                "diagnosis": rule.diagnosis,
                "field": rule.field,
                "layer": rule.layer,
                "isi": rule.isi,
                "sumber": rule.sumber,
                "rs_id": rule.rs_id,
                "region_id": rule.region_id,
                "status": rule.status,
                "created_by": rule.created_by,
                "created_at": rule.created_at.isoformat() if rule.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error mengambil data rule: {str(e)}")

@router.post("/review-report")
async def review_regional_report(
    request: Request,
    report_id: str = Form(...),
    decision: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin")),
    _=Depends(require_csrf_dep)
):
    """
    AI META review regional reports dari RS.
    Fixed authentication to use consistent session-based auth.
    """
    try:
        # Get regional report (assuming you have RegionalReports model)
        report = db.query(models.RegionalReports).filter(
            models.RegionalReports.id == report_id
        ).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Regional report tidak ditemukan")

        # Update status based on decision
        if decision == "approve":
            report.status = "reviewed"
        elif decision == "reject":
            report.status = "rejected"  
        else:
            raise HTTPException(status_code=400, detail="Decision harus 'approve' atau 'reject'")
        
        report.reviewed_by = user.email
        report.reviewed_date = datetime.now()
        report.review_notes = notes
        
        db.commit()
        
        return JSONResponse({
            "status": "success", 
            "message": f"Report berhasil {decision}"
        })
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error review report: {str(e)}")

@router.post("/convert-to-rules")
async def convert_se_to_rules(
    request: Request,
    report_id: str = Form(...),
    target_layer: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin")),
    _=Depends(require_csrf_dep)
):
    """
    Convert SE report menjadi rules di layer tertentu.
    """
    print(f"🔧 Convert-to-rules called by user: {user.email}, report_id: {report_id}, target_layer: {target_layer}")
    try:
        # Validate target layer (semua 8 layer)
        allowed_layers = ["permenkes", "nasional", "ppk", "regional", "rs", "bridging", "fraud", "temporary"]
        if target_layer not in allowed_layers:
            raise HTTPException(status_code=400, detail=f"Layer '{target_layer}' tidak valid")
        
        # Get regional report (assuming you have RegionalReports model)
        report = db.query(models.RegionalReports).filter(
            models.RegionalReports.id == report_id
        ).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Regional report tidak ditemukan")

        # Extract content and convert to rule
        # This is a simplified conversion - you might want to parse the report content
        new_rule = models.RulesMaster(
            diagnosis=f"SE Report {report_id}",  # You might want to extract actual diagnosis
            field="justifikasi",  # Default field, might want to detect from content
            layer=target_layer,
            isi=f"Converted from SE Report: {report.content if hasattr(report, 'content') else 'SE content'}",
            sumber=f"SE Report {report_id} - Converted by AI META",
            rs_id=report.rs_id if hasattr(report, 'rs_id') else None,
            region_id=report.region_id if hasattr(report, 'region_id') else None,
            status="official",
            created_by=f"ai_meta_convert_{user.email}",
            approved_by=user.email,
            approved_date=datetime.now(),
            review_notes=f"Converted from SE Report {report_id} by {user.email}",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        db.add(new_rule)
        
        # Mark report as converted
        report.status = "converted"
        report.reviewed_by = user.email
        report.reviewed_date = datetime.now()
        
        db.commit()

        return JSONResponse({
            "status": "success",
            "message": f"SE Report berhasil dikonversi ke {target_layer} rules",
            "rule_id": new_rule.id
        })

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error convert SE: {str(e)}")

# DEBUG ENDPOINT - TEMPORARY
@router.get("/debug/auth")
async def debug_auth(
    user=Depends(require_roles_session("superadmin"))
):
    """Debug authentication"""
    return {
        "status": "success",
        "user": user.email,
        "role": user.role,
        "message": "Auth working!"
    }

@router.post("/debug/csrf")
async def debug_csrf(
    request: Request,
    user=Depends(require_roles_session("superadmin")),
    _=Depends(require_csrf_dep)
):
    """Debug CSRF protection with form data"""
    return {
        "status": "success",
        "user": user.email,
        "message": "CSRF form working!",
        "headers": dict(request.headers)
    }

@router.post("/debug/simple")
async def debug_simple_post(
    request: Request,
    user=Depends(require_roles_session("superadmin"))
):
    """Debug simple POST without CSRF"""
    print(f"🔧 DEBUG: Simple POST by {user.email}")
    return {
        "status": "success",
        "user": user.email,
        "message": "Simple POST working without CSRF!"
    }

@router.get("/debug/token")
async def debug_csrf_token(request: Request):
    """Check CSRF token generation"""
    csrf_token = issue_csrf_token(request)
    return {
        "csrf_token": csrf_token,
        "session_id": request.session.get("session_id", "NO_SESSION"),
        "cookies": dict(request.cookies),
        "message": "CSRF token info"
    }