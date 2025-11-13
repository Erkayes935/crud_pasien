"""
routers/claim/claim_regulation_feedback_router.py
💬 Modul router untuk sistem tooltip & feedback multilayer regulasi.

Router ini memanggil service global:
- `services/regulation_feedback_service.py`
yang berada di luar folder /claim karena digunakan lintas modul
(Claim, Admin RS, dan Dashboard AI META).
"""

from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.auth import require_roles_session, require_csrf_dep
from backend.services import regulation_feedback_service

router = APIRouter(tags=["Claim Regulation Feedback"])


# ======================================================
# 🎈 TOOLTIP SYSTEM ENDPOINT
# ======================================================
@router.get("/tooltip/rules/{field_path}")
async def get_field_tooltip(
    field_path: str,
    diagnosis: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """
    Tooltip system untuk menampilkan ringkasan aturan multilayer
    saat user hover di field tertentu.
    """
    try:
        result = regulation_feedback_service.get_tooltip_for_field(db, field_path, diagnosis)
        return {"status": "success", "data": result}
    except Exception as e:
        print(f"[TOOLTIP] ❌ Error: {e}")
        return {
            "status": "error",
            "message": f"Gagal memuat tooltip: {e}",
            "data": {}
        }


# ======================================================
# 💬 SUBMIT FEEDBACK ENDPOINT
# ======================================================
@router.post("/rules/{rule_id}/feedback")
async def submit_rule_feedback(
    rule_id: int,
    feedback: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs", "doctor", "verifikator")),
    _=Depends(require_csrf_dep),
):
    """
    Submit feedback untuk rule tertentu oleh doctor/verifikator/admin RS.
    """
    try:
        result = regulation_feedback_service.submit_feedback(db, rule_id, feedback, user)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        print(f"[FEEDBACK] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan feedback: {e}")


# ======================================================
# 📋 GET ALL FEEDBACK (ADMIN / AI META)
# ======================================================
@router.get("/rules/feedback/list")
async def get_rules_with_feedback(
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin", "ai_meta")),
):
    """
    Endpoint untuk AI META / admin pusat melihat semua rules
    yang sudah menerima feedback dari RS atau pengguna lain.
    """
    try:
        result = regulation_feedback_service.get_all_feedback(db)
        return {"status": "success", "total_feedback": len(result), "data": result}
    except Exception as e:
        print(f"[GET_FEEDBACK] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal memuat daftar feedback: {e}")
