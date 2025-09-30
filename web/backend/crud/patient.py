"""
Module: backend.crud

Small database helper functions that operate with a SQLAlchemy `Session`.
Functions here perform simple CRUD operations and are intentionally minimal
so route handlers in `main.py` remain straightforward. These helpers expect
the caller to pass correctly shaped data (dictionary keys matching model
attributes) and provide minimal defensive checks (returning None/False when
the target resource does not exist) to make callers easier to implement.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend import models

def get_patients(db: Session) -> List[models.Patient]:
    """Return all active patients (not soft-deleted)."""
    return db.query(models.Patient).filter(models.Patient.is_deleted == False).all()

def create_patient(db: Session, data: Dict[str, Any]) -> models.Patient:
    """Create and persist a new Patient."""
    if "is_deleted" not in data:
        data["is_deleted"] = False
    if "is_dummy" not in data:
        data["is_dummy"] = True
    new_patient = models.Patient(**data)
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient

def update_patient(db: Session, patient_id: int, data: Dict[str, Any]) -> Optional[models.Patient]:
    """Update an existing patient with values from `data`."""
    patient = db.query(models.Patient).filter(
        models.Patient.id == patient_id,
        models.Patient.is_deleted == False
    ).first()
    if not patient:
        return None
    for key, value in data.items():
        setattr(patient, key, value)
    db.commit()
    db.refresh(patient)
    return patient

def delete_patient(db: Session, patient_id: int) -> bool:
    """Soft-delete a patient by setting is_deleted=True."""
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        return False
    patient.is_deleted = True
    db.commit()
    return True