from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.utils.templates import templates
from backend.utils.flash import flash
from backend.auth import require_roles_session, issue_csrf_token
from backend.services import dashboard_service

router = APIRouter()

# =========================
# DASHBOARD PAGE
# =========================
@router.get("/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles_session("doctor", "admin_rs", "superadmin", "coder", "verifikator")
    ),
):
    data = dashboard_service.get_dashboard_data(db, current_user)
    csrf_token = issue_csrf_token(request)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "csrf_token": csrf_token,
            **data,
        },
    )


# =========================
# ROOT → redirect ke dashboard
# =========================
@router.get("/")
def root_redirect(
    request: Request,
    user=Depends(
        require_roles_session("doctor", "admin_rs", "superadmin", "coder", "verifikator")
    ),
):
    flash(request, "Redirecting to dashboard...", "info")
    return RedirectResponse(url="/dashboard", status_code=303)
