from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend import models

def get_hospitals(db: Session) -> List[models.Hospital]:
    return (
        db.query(models.Hospital)
        .filter(models.Hospital.is_deleted == False)
        .order_by(models.Hospital.id.desc())
        .all()
    )

def get_hospital_by_id(db: Session, hospital_id: int) -> Optional[models.Hospital]:
    return db.query(models.Hospital).filter(models.Hospital.id == hospital_id, models.Hospital.is_deleted == False).first()

def create_hospital(db: Session, data: Dict[str, Any]) -> models.Hospital:
    if "is_deleted" not in data:
        data["is_deleted"] = False
    if "is_dummy" not in data:
        data["is_dummy"] = True
    hospital = models.Hospital(**data)
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital

def update_hospital(db: Session, hospital_id: int, data: Dict[str, Any]) -> Optional[models.Hospital]:
    hospital = db.query(models.Hospital).filter(models.Hospital.id == hospital_id, models.Hospital.is_deleted == False).first()
    if not hospital:
        return None
    for k, v in data.items():
        setattr(hospital, k, v)
    db.commit()
    db.refresh(hospital)
    return hospital

def delete_hospital(db: Session, hospital_id: int) -> bool:
    hospital = db.query(models.Hospital).filter(models.Hospital.id == hospital_id).first()
    if not hospital:
        return False
    hospital.is_deleted = True
    db.commit()
    return True