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
from ..auth import require_roles_session
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
    
    return templates.TemplateResponse("ai_meta_dashboard.html", {
        "request": request,
        "user": user,
        "current_user": user,
        "stats": stats,
        "recent_rules": recent_rules,
        "recent_feedback": recent_feedback,
        "recent_reports": recent_reports
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

@router.post("/bulk-import")
async def bulk_import_rules(
    layer: str = Form(...),
    rules_json: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin"))
):
    """
    Bulk import rules dari JSON format.
    Khusus untuk layer: nasional, bridging, fraud, temporary
    """
    
    allowed_layers = ["nasional", "bridging", "fraud", "temporary"]
    if layer not in allowed_layers:
        raise HTTPException(status_code=400, detail=f"Layer {layer} tidak diizinkan untuk bulk import")
    
    try:
        rules_data = json.loads(rules_json)
        if not isinstance(rules_data, list):
            raise ValueError("JSON harus berupa array")
            
        imported_count = 0
        
        for rule_data in rules_data:
            # Validasi required fields
            required_fields = ["diagnosis", "field", "isi", "sumber"]
            for field in required_fields:
                if field not in rule_data:
                    raise ValueError(f"Field '{field}' wajib ada di setiap rule")
            
            # Create rule
            rule = models.RulesMaster(
                layer=layer,
                diagnosis=rule_data["diagnosis"],
                field=rule_data["field"],
                isi=rule_data["isi"],
                sumber=rule_data["sumber"],
                rs_id=rule_data.get("rs_id"),
                region_id=rule_data.get("region_id"),
                status="official",  # AI META import langsung official
                created_by=f"ai_meta_{user.email}",
                approved_by=user.email,
                approved_date=datetime.now(),
                review_notes=f"Bulk imported by AI META admin: {user.email}"
            )
            
            db.add(rule)
            imported_count += 1
        
        db.commit()
        
        return {
            "status": "success", 
            "message": f"Berhasil import {imported_count} rules untuk layer {layer}",
            "imported_count": imported_count
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Format JSON tidak valid")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error import: {str(e)}")

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