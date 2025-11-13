"""
Router untuk integrasi Data Hub dalam Web Application
"""
from fastapi import APIRouter, Request, Depends
from backend.auth import require_roles_session
from backend.utils.templates import templates
import os

router = APIRouter()

@router.get("/admin-rs/datahub")
def datahub_page(
    request: Request,
    current_user=Depends(require_roles_session("admin_rs", "superadmin"))
):
    """
    Data Hub page untuk Admin RS.
    Menampilkan Data Hub UI dalam iframe untuk standarisasi data RS.
    
    Access: admin_rs, superadmin
    """
    # Use localhost for browser access (not Docker internal network)
    datahub_url = "http://localhost:8000"
    
    return templates.TemplateResponse(
        "datahub_page.html",
        {
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "datahub_url": datahub_url
        }
    )
