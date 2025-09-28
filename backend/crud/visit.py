"""
Module: backend.crud.visit

CRUD helpers untuk Visit.
Dipakai oleh visit_router.py
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend import models


# =========================
# GET
# =========================
def get_visits(db: Session, search: Optional[str] = None) -> List[models.Visit]:
    query = db.query(models.Visit)
    if search:
        query = query.filter(
            models.Visit.doctor_name.ilike(f"%{search}%")
            | models.Visit.poli.ilike(f"%{search}%")
        )
    return (
        query.order_by(models.Visit.id.desc())
        .filter(models.Visit.is_deleted == False)
        .all()
    )


def get_visits_by_patient(db: Session, patient_id: int, search: Optional[str] = None) -> List[models.Visit]:
    query = db.query(models.Visit).filter(models.Visit.patient_id == patient_id)
    if search:
        query = query.filter(
            models.Visit.doctor_name.ilike(f"%{search}%")
            | models.Visit.poli.ilike(f"%{search}%")
        )
    return (
        query.order_by(models.Visit.id.desc())
        .filter(models.Visit.is_deleted == False)
        .all()
    )


def get_visit_by_id(db: Session, visit_id: int) -> Optional[models.Visit]:
    return (
        db.query(models.Visit)
        .filter(models.Visit.id == visit_id, models.Visit.is_deleted == False)
        .first()
    )


# =========================
# CREATE
# =========================
def create_visit(db: Session, data: Dict[str, Any]) -> models.Visit:
    visit = models.Visit(**data)
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


# =========================
# UPDATE
# =========================
def update_visit(db: Session, visit_id: int, data: Dict[str, Any]) -> Optional[models.Visit]:
    visit = db.query(models.Visit).filter(models.Visit.id == visit_id).first()
    if not visit:
        return None
    for k, v in data.items():
        setattr(visit, k, v)
    db.commit()
    db.refresh(visit)
    return visit


# =========================
# DELETE (Soft)
# =========================
def delete_visit(db: Session, visit_id: int) -> bool:
    visit = db.query(models.Visit).filter(models.Visit.id == visit_id).first()
    if not visit:
        return False
    visit.is_deleted = True
    db.commit()
    return True
