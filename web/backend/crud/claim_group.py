from sqlalchemy.orm import Session
from .. import models

def create_group(db: Session, patient_id: int, hospital_id: int, nama_group: str, created_by: str):
    new_group = models.ClaimGroup(
        kode_group=f"E{int(datetime.now().timestamp())}",
        nama_group=nama_group,
        patient_id=patient_id,
        hospital_id=hospital_id,
        created_by=created_by,
    )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group

def get_groups_by_patient(db: Session, patient_id: int):
    return db.query(models.ClaimGroup).filter(models.ClaimGroup.patient_id == patient_id).all()
