from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_session
from ..models.core import DataHubSource, DataHubRecord, AuditLog
from sqlalchemy import func, desc

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_session)):
    types = ["manual", "import_excel", "gateway"]
    summary = []
    for t in types:
        q = (
            db.query(func.count(DataHubRecord.id).label("total"))
            .join(DataHubSource)
            .filter(DataHubSource.type == t)
        )
        total = q.scalar() or 0

        # contoh dummy statistik tambahan
        valid = total // 2
        error = total // 4
        duplicate = total // 8

        last_update = db.query(func.max(DataHubRecord.created_at))\
                        .join(DataHubSource)\
                        .filter(DataHubSource.type == t)\
                        .scalar()

        summary.append({
            "source": t,
            "total": total,
            "valid": valid,
            "error": error,
            "duplicate": duplicate,
            "last_update": last_update.strftime("%Y-%m-%d %H:%M") if last_update else None
        })

    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "summary": summary}
    )


@router.get("/api/logs")
def get_logs(limit: int = 10, db: Session = Depends(get_session)):
    """
    Get recent audit logs for dashboard
    """
    try:
        logs = (
            db.query(AuditLog)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .all()
        )
        
        return [
            {
                "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "-",
                "source": log.source or "unknown",
                "level": log.level or "info",
                "message": log.message or ""
            }
            for log in logs
        ]
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return []
