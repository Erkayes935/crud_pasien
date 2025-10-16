"""
Module: backend.services.claim.core

Berisi service functions utama untuk manajemen klaim:
- tambah klaim baru
- update draft klaim
- finalisasi klaim

Semua fungsi di sini hanya fokus pada business logic klaim.
HTTP/Template handling dilakukan di claim_router.py.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from ... import models
from .simulation import save_simulasi
from .ai import store_ai_evaluations
from .. import claim_helper
import json


# ==================================================
# ADD CLAIM
# ==================================================
def add_claim_service(db: Session, visit_id: int, user, hospital_id: int | None = None):
    """
    Buat klaim baru (status draft) + log.
    """
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        return None

    claim = models.Claim(
        claim_date=datetime.utcnow(),
        visit_id=visit_id,
        patient_id=visit.patient_id,
        hospital_id=hospital_id,
        doctor_id=user.id,
        doctor_name=user.name,
        medical_record_id=None,
        is_final=False,
        status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=False,
    )
    db.add(claim)
    db.flush()
    db.refresh(claim)

    # Log klaim
    db.add(models.ClaimLog(
        claim_id=claim.id,
        action="CREATED",
        description=f"Klaim {claim.id} dibuat oleh {user.name}",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=False
    ))
    db.commit()
    return claim


# ==================================================
# UPDATE DRAFT
# ==================================================
def update_claim_draft_service(db: Session, claim_id: int, user, form_data: dict):
    """
    Update klaim dalam status draft:
    - update simulasi
    - update evaluasi (summary) dari core_engine
    - update rekam medis
    """
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        return None

    # Parsing simulasi & summary
    sim_data = form_data.get("simulasi")
    summ_data = form_data.get("summary")

    if isinstance(sim_data, str):
        try:
            sim_data = json.loads(sim_data)
        except Exception:
            sim_data = {}
    if isinstance(summ_data, str):
        try:
            summ_data = json.loads(summ_data)
        except Exception:
            summ_data = {}

    # Simpan simulasi
    if sim_data:
        save_simulasi(db, claim.id, sim_data, form_data)

    # Simpan evaluasi
    if summ_data:
        store_ai_evaluations(db, claim.id, summ_data)

    # Update rekam medis
    if claim.medical_record:
        claim_helper.update_medical_record_fields(claim.medical_record, form_data, user.id, db, "draft")

    # Update status klaim
    claim.is_final = False
    claim.status = "draft"
    claim.updated_at = datetime.utcnow()

    # Log klaim
    db.add(models.ClaimLog(
        claim_id=claim.id,
        action="UPDATED",
        description="Draft klaim diperbarui",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=False
    ))
    db.commit()
    db.refresh(claim)
    return claim


# ==================================================
# FINALIZE CLAIM
# ==================================================
def finalize_claim_service(db: Session, claim_id: int, user, form_data: dict):
    """
    Finalisasi klaim:
    - update simulasi
    - update evaluasi (summary)
    - update rekam medis
    - set status final
    """
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        return None

    sim_data = form_data.get("simulasi")
    summ_data = form_data.get("summary")

    if isinstance(sim_data, str):
        try:
            sim_data = json.loads(sim_data)
        except Exception:
            sim_data = {}
    if isinstance(summ_data, str):
        try:
            summ_data = json.loads(summ_data)
        except Exception:
            summ_data = {}

    if sim_data:
        save_simulasi(db, claim.id, sim_data)
    if summ_data:
        store_ai_evaluations(db, claim.id, summ_data)

    if claim.medical_record:
        claim_helper.update_medical_record_fields(claim.medical_record, form_data, user.id, db, "finalized")

    claim.is_final = True
    claim.status = "final"
    claim.updated_at = datetime.utcnow()

    db.add(models.ClaimLog(
        claim_id=claim.id,
        action="FINALIZED",
        description="Klaim difinalisasi",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=False
    ))
    db.commit()
    db.refresh(claim)
    return claim
