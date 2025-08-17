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
from . import models


def get_patients(db: Session) -> List[models.Patient]:
    """Return all patient rows from the database.

    Args:
        db: SQLAlchemy Session

    Returns:
        List of Patient ORM objects.
    """

    return db.query(models.Patient).all()

def create_patient(db: Session, data: Dict[str, Any]) -> models.Patient:
    """Create and persist a new Patient.

    Args:
        db: SQLAlchemy Session
        data: dict mapping Patient field names to values

    Returns:
        The created Patient ORM object (with ID populated).
    """

    new_patient = models.Patient(**data)
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient

def update_patient(db: Session, patient_id: int, data: Dict[str, Any]) -> Optional[models.Patient]:
    """Update an existing patient with values from `data`.

    Args:
        db: SQLAlchemy Session
        patient_id: ID of the patient to update
        data: dict of fields to update

    Returns:
        The updated Patient, or None if the patient was not found.
    """

    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        return None

    for key, value in data.items():
        setattr(patient, key, value)
    db.commit()
    return patient

def delete_patient(db: Session, patient_id: int) -> bool:
    """Delete a patient by ID.

    Args:
        db: SQLAlchemy Session
        patient_id: ID of the patient to delete

    Returns:
        True if a patient was deleted, False if no patient with that ID exists.
    """

    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        return False
    db.delete(patient)
    db.commit()
    return True
