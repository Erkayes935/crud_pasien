"""
Module: backend.crud.claim

Berisi operasi database untuk tabel Claim (klaim kesehatan).
Semua query/CRUD klaim dikumpulkan di sini supaya router tetap tipis
dan business logic berat bisa dipindahkan ke services/claim_service.py.
"""

import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from .. import models


# -----------------------
# GET / LIST
# -----------------------

def get_claims(
    db: Session,
    status: Optional[str] = None,
    tanggal_kunjungan: Optional[str] = None,
    patient_name: Optional[str] = None,
    jenis_kunjungan: Optional[str] = None,
    claim_id: Optional[int] = None,
    visit_id: Optional[int] = None
) -> List[models.Claim]:
    """Ambil daftar klaim dengan filter opsional."""
    query = db.query(models.Claim).join(models.Visit, models.Claim.visit_id == models.Visit.id)

    if status:
        query = query.filter(models.Claim.status.ilike(status))
    if jenis_kunjungan:
        query = query.filter(models.Visit.jenis_kunjungan.ilike(jenis_kunjungan))
    if tanggal_kunjungan:
        query = query.filter(models.Visit.tanggal_kunjungan == tanggal_kunjungan)
    if patient_name:
        query = query.join(models.Patient).filter(
            models.Patient.nama.ilike(f"%{patient_name}%")
        )
    if claim_id:
        query = query.filter(models.Claim.id == claim_id)
    if visit_id:
        query = query.filter(models.Claim.visit_id == visit_id)

    return (
        query.filter(models.Claim.is_deleted == False)
             .order_by(models.Claim.id.desc())
             .all()
    )


def get_claim(db: Session, claim_id: int) -> Optional[models.Claim]:
    """Ambil detail klaim berdasarkan ID."""
    return db.query(models.Claim).filter_by(id=claim_id, is_deleted=False).first()


# -----------------------
# CREATE (skip -> move to service)
# -----------------------

# -----------------------
# UPDATE
# -----------------------

def update_claim(db: Session, claim: models.Claim) -> models.Claim:
    """Update klaim (objek Claim sudah dimodifikasi di service/router)."""
    claim.updated_at = datetime.utcnow()
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


# -----------------------
# DELETE (SOFT)
# -----------------------

def delete_claim(db: Session, claim_id: int) -> bool:
    """Soft delete klaim (ubah is_deleted=True)."""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        return False
    claim.is_deleted = True
    claim.updated_at = datetime.utcnow()
    db.commit()
    return True


# -----------------------
# EXPORT
# -----------------------

def export_claims(
    db: Session,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[models.Claim]:
    """Ambil klaim untuk diexport (filter by status & rentang tanggal)."""
    query = db.query(models.Claim).join(models.Patient)
    if status:
        query = query.filter(models.Claim.status == status)
    if start_date:
        query = query.filter(models.Claim.tanggal_kunjungan >= start_date)
    if end_date:
        query = query.filter(models.Claim.tanggal_kunjungan <= end_date)
    return query.filter(models.Claim.is_deleted == False).all()
