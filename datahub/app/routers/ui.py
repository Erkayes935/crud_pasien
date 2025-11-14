from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_session
from ..models.core import DataHubSource, DataHubRecord, AuditLog, MedicalRecord, Patient, Visit
from sqlalchemy import func, desc

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_session)):
    """
    Dashboard endpoint that renders HTML with statistics.
    
    Counts:
    - Patients by source_type
    - Visits by source_type
    - Medical Records by source_type and status
    - Total = Patient + Visit + MedicalRecord
    """
    types = ["manual", "import_excel", "gateway"]
    summary = []

    for t in types:
        try:
            # 📹 Patients per sumber
            patient_count = db.query(func.count(Patient.id))\
                .filter(
                    Patient.source_type == t,
                    Patient.is_deleted == False
                ).scalar() or 0

            # 📹 Visits per sumber
            visit_count = db.query(func.count(Visit.id))\
                .filter(
                    Visit.source_type == t,
                    Visit.is_deleted == False
                ).scalar() or 0
            
            # 📹 Rekam Medis per sumber, dipecah by status
            valid_records = db.query(func.count(MedicalRecord.id))\
                .filter(
                    MedicalRecord.source_type == t,
                    MedicalRecord.status.in_(
                        ["ready_for_ai", "ai_processed", "ai_success"]
                    ),
                    MedicalRecord.is_deleted == False
                ).scalar() or 0

            error_records = db.query(func.count(MedicalRecord.id))\
                .filter(
                    MedicalRecord.source_type == t,
                    MedicalRecord.status == "error",
                    MedicalRecord.is_deleted == False
                ).scalar() or 0

            duplicate_records = db.query(func.count(MedicalRecord.id))\
                .filter(
                    MedicalRecord.source_type == t,
                    MedicalRecord.status == "duplicate",
                    MedicalRecord.is_deleted == False
                ).scalar() or 0

            medical_total = valid_records + error_records + duplicate_records

            # 📹 Total di header card
            total = patient_count + visit_count + medical_total

            # 📹 Last update per sumber (ambil yang paling baru dari Patient, Visit, MedicalRecord)
            last_patient = db.query(func.max(Patient.created_at))\
                .filter(
                    Patient.source_type == t,
                    Patient.is_deleted == False
                ).scalar()

            last_visit = db.query(func.max(Visit.created_at))\
                .filter(
                    Visit.source_type == t,
                    Visit.is_deleted == False
                ).scalar()

            last_medical = db.query(func.max(MedicalRecord.created_at))\
                .filter(
                    MedicalRecord.source_type == t,
                    MedicalRecord.is_deleted == False
                ).scalar()

            # Get the most recent timestamp from all three tables
            last_candidates = [d for d in [last_patient, last_visit, last_medical] if d]
            last_update = max(last_candidates) if last_candidates else None
            
            summary.append({
                "source": t,
                "total": total,
                "patients": patient_count,
                "visits": visit_count,
                "medical_records": medical_total,
                "valid": valid_records,
                "error": error_records,
                "duplicate": duplicate_records,
                "last_update": last_update.strftime("%Y-%m-%d %H:%M:%S") if last_update else None
            })
        
        except Exception as e:
            print(f"Error getting stats for {t}: {str(e)}")
            # Return minimal stats on error
            summary.append({
                "source": t,
                "total": 0,
                "patients": 0,
                "visits": 0,
                "medical_records": 0,
                "valid": 0,
                "error": 0,
                "duplicate": 0,
                "last_update": None
            })

    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "summary": summary}
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