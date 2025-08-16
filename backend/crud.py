from sqlalchemy.orm import Session
from . import models

def get_patients(db: Session):
    return db.query(models.Patient).all()

def create_patient(db: Session, data):
    new_patient = models.Patient(**data)
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient

def update_patient(db: Session, patient_id, data):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    for key, value in data.items():
        setattr(patient, key, value)
    db.commit()
    return patient

def delete_patient(db: Session, patient_id):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    db.delete(patient)
    db.commit()
    return True
