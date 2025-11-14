"""
Hybrid Sync Router
==================
Menerima sinkronisasi UUID pasien dari RS Gateway.
Gateway hanya mengirim HASH dan UUID (tanpa PII!).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel, Field
from datetime import datetime
from backend.database import get_datahub_session
from backend.models.datahub.core import PatientUUIDMap
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sync", tags=["Hybrid Sync"])

class PatientUUIDSyncRequest(BaseModel):
    """Schema untuk sync request dari Gateway."""
    patient_uuid: str = Field(..., description="UUID pasien yang di-generate Gateway")
    hospital_id: str = Field(..., description="ID rumah sakit asal")
    name_hash: str | None = Field(None, description="Hash dari nama pasien")
    nik_hash: str | None = Field(None, description="Hash dari NIK pasien")

@router.post("/patient_uuid")
def sync_patient_uuid(
    data: PatientUUIDSyncRequest, 
    db: Session = Depends(get_datahub_session)
):
    """
    RS Gateway mengirim mapping untuk sync UUID.
    
    Request body:
    {
        "hospital_id": "RS001",
        "name_hash": "a3b4...",
        "nik_hash": "9a8c...",
        "patient_uuid": "uuid-xxxx"
    }
    """
    
    # Check apakah UUID sudah ada
    existing = db.query(PatientUUIDMap).filter(
        PatientUUIDMap.patient_uuid == data.patient_uuid
    ).first()

    if existing:
        # Update timestamp terakhir sync
        existing.last_synced = datetime.utcnow()
        db.commit()
        
        logger.info(f"[SYNC] ↻ Patient UUID already exists: {data.patient_uuid}")
        return {
            "status": "exists", 
            "message": "UUID already synced, updated timestamp",
            "patient_uuid": data.patient_uuid
        }

    # Check apakah ada UUID lain dengan hash yang sama (potential duplicate)
    if data.name_hash and data.nik_hash:
        duplicate = db.query(PatientUUIDMap).filter(
            and_(
                PatientUUIDMap.name_hash == data.name_hash,
                PatientUUIDMap.nik_hash == data.nik_hash,
                PatientUUIDMap.hospital_id == data.hospital_id,
                PatientUUIDMap.patient_uuid != data.patient_uuid
            )
        ).first()
        
        if duplicate:
            logger.warning(
                f"[SYNC] ⚠ Potential duplicate: "
                f"UUID {data.patient_uuid} has same hash as {duplicate.patient_uuid}"
            )
            # Tetap simpan tapi flag sebagai potential duplicate
            # TODO: Implement merge strategy

    # Simpan mapping baru
    mapping = PatientUUIDMap(
        patient_uuid=data.patient_uuid,
        source_type="gateway",
        hospital_id=data.hospital_id,
        name_hash=data.name_hash,
        nik_hash=data.nik_hash,
        created_at=datetime.utcnow(),
        last_synced=datetime.utcnow()
    )

    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    logger.info(f"[SYNC] ✓ New UUID synced from {data.hospital_id}: {data.patient_uuid}")
    return {
        "status": "ok", 
        "message": "UUID mapping stored successfully",
        "patient_uuid": data.patient_uuid,
        "created_at": mapping.created_at.isoformat()
    }


@router.get("/stats")
def sync_stats(db: Session = Depends(get_datahub_session)):
    """
    Statistik sinkronisasi hybrid.
    """
    total = db.query(PatientUUIDMap).count()
    
    by_source = dict(
        db.query(
            PatientUUIDMap.source_type, 
            func.count()
        ).group_by(PatientUUIDMap.source_type).all()
    )
    
    by_hospital = dict(
        db.query(
            PatientUUIDMap.hospital_id,
            func.count()
        ).group_by(PatientUUIDMap.hospital_id).all()
    )
    
    # Last sync time
    last_sync = db.query(PatientUUIDMap).order_by(
        PatientUUIDMap.last_synced.desc()
    ).first()
    
    return {
        "status": "ok",
        "total_uuids": total,
        "by_source": by_source,
        "by_hospital": by_hospital,
        "last_sync": last_sync.last_synced.isoformat() if last_sync else None
    }


@router.get("/patient/{patient_uuid}")
def get_patient_mapping(patient_uuid: str, db: Session = Depends(get_datahub_session)):
    """
    Cek mapping info untuk UUID tertentu (untuk debugging).
    Hanya mengembalikan metadata, bukan PII.
    """
    mapping = db.query(PatientUUIDMap).filter(
        PatientUUIDMap.patient_uuid == patient_uuid
    ).first()
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"UUID {patient_uuid} not found"
        )
    
    return {
        "patient_uuid": mapping.patient_uuid,
        "hospital_id": mapping.hospital_id,
        "source_type": mapping.source_type,
        "has_name_hash": bool(mapping.name_hash),
        "has_nik_hash": bool(mapping.nik_hash),
        "created_at": mapping.created_at.isoformat(),
        "last_synced": mapping.last_synced.isoformat()
    }
