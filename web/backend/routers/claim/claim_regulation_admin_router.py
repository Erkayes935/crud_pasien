"""
routers/claim/claim_regulation_admin_router.py
📘 Router untuk Admin RS & AI META:
CRUD Rules (PPK/RS), Upload SE Regional, dll.
"""

from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.auth import require_roles_session, require_csrf_dep
from backend.services import regulation_admin_service

router = APIRouter(tags=["Claim Regulation Admin"])


# ======================================================
# 🧩 CRUD RULES
# ======================================================
@router.get("/rules/my_rules")
async def get_my_rules(
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs")),
):
    try:
        data = regulation_admin_service.get_my_rs_rules(db, user)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal ambil rules: {e}")


@router.post("/rules/add")
async def add_rule(
    diagnosis: str = Form(...),
    field: str = Form(...),
    layer: str = Form(...),
    isi: str = Form(...),
    sumber: str = Form(...),
    pdf_file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs")),
    _=Depends(require_csrf_dep),
):
    try:
        new_rule = regulation_admin_service.add_rule(db, user, diagnosis, field, layer, isi, sumber, pdf_file)
        return {"status": "success", "rule_id": new_rule.id, "message": "Rule berhasil ditambahkan"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal tambah rule: {e}")


@router.put("/rules/{rule_id}/update")
async def update_rule(
    rule_id: int,
    diagnosis: str = Form(...),
    field: str = Form(...),
    isi: str = Form(...),
    sumber: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs")),
    _=Depends(require_csrf_dep),
):
    try:
        updated = regulation_admin_service.update_rule(db, user, rule_id, diagnosis, field, isi, sumber)
        return {"status": "success", "message": f"Rule {updated.id} berhasil diperbarui"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal update rule: {e}")


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs")),
    _=Depends(require_csrf_dep),
):
    try:
        deleted = regulation_admin_service.delete_rule(db, user, rule_id)
        return {"status": "success", "message": f"Rule {deleted.id} berhasil dihapus"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal hapus rule: {e}")


# ======================================================
# 📂 REGIONAL REPORTS
# ======================================================
@router.post("/regional-reports/add")
async def add_regional_report(
    title: str = Form(...),
    description: str = Form(""),
    se_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs")),
    _=Depends(require_csrf_dep),
):
    try:
        report = regulation_admin_service.add_regional_report(db, user, title, description, se_file)
        return {"status": "success", "message": "Laporan SE berhasil dikirim", "report_id": report.id}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal upload SE: {e}")
