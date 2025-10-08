"""
Module: backend.crud.medical_record

CRUD helpers untuk MedicalRecord dan MedicalRecordLog.
Dipakai oleh router medical_record_router.py
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend import models


# =========================
# MEDICAL RECORDS
# =========================
def list_medical_records(
    db: Session,
    q: Optional[str] = None,
    status: Optional[str] = None,
    date_val: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> (List[models.MedicalRecord], int):
    """List medical records dengan filter + pagination."""
    query = db.query(models.MedicalRecord).join(models.Patient)

    if q:
        query = query.filter(models.Patient.nama.ilike(f"%{q}%"))

    if status == "final":
        query = query.filter(models.MedicalRecord.is_final.is_(True))
    elif status == "draft":
        query = query.filter(models.MedicalRecord.is_final.is_(False))

    if date_val:
        query = query.filter(models.MedicalRecord.notes_date == date_val)

    total = query.count()
    records = (
        query.order_by(models.MedicalRecord.id.desc())
        .filter(models.MedicalRecord.is_deleted == False)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return records, total


def get_record_by_id(db: Session, record_id: int) -> Optional[models.MedicalRecord]:
    return (
        db.query(models.MedicalRecord)
        .filter(models.MedicalRecord.id == record_id, models.MedicalRecord.is_deleted == False)
        .first()
    )


def update_record(db: Session, record_id: int, data: Dict[str, Any]) -> Optional[models.MedicalRecord]:
    record = db.query(models.MedicalRecord).filter(models.MedicalRecord.id == record_id).first()
    if not record:
        return None
    for k, v in data.items():
        setattr(record, k, v)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record_id: int) -> bool:
    record = db.query(models.MedicalRecord).filter(models.MedicalRecord.id == record_id).first()
    if not record:
        return False
    record.is_deleted = True
    db.commit()
    return True


# =========================
# MEDICAL RECORD LOGS
# =========================
def get_logs(db: Session, record_id: int) -> List[models.MedicalRecordLog]:
    return (
        db.query(models.MedicalRecordLog)
        .filter(
            models.MedicalRecordLog.medical_record_id == record_id,
            models.MedicalRecordLog.is_deleted == False,
        )
        .order_by(models.MedicalRecordLog.version.desc())
        .all()
    )


def add_log(db: Session, record_id: int, action: str, description: str, updated_by: int, snapshot: str):
    """Tambah log baru untuk rekam medis."""
    log = models.MedicalRecordLog(
        medical_record_id=record_id,
        action=action,
        description=description,
        updated_by=updated_by,
        data_snapshot=snapshot,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def delete_log(db: Session, log_id: int) -> bool:
    log = db.query(models.MedicalRecordLog).filter(models.MedicalRecordLog.id == log_id).first()
    if not log:
        return False
    log.is_deleted = True
    db.commit()
    return True