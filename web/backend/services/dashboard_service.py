"""
Module: backend.services.dashboard_service

Business logic untuk query data dashboard.
Digunakan oleh dashboard_router.py untuk render halaman dashboard.
"""

from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from backend import models


def get_dashboard_data(db: Session, current_user):
    data = {}

    # =========================
    # USERS
    # =========================
    if current_user.role == "superadmin":
        data["users_dashboard"] = (
            db.query(models.User)
            .filter(models.User.role == "admin_rs", models.User.is_deleted == False)
            .order_by(models.User.id.desc())
            .limit(10)
            .all()
        )
    elif current_user.role == "admin_rs":
        data["users_dashboard"] = (
            db.query(models.User)
            .filter(
                models.User.hospital_id == current_user.hospital_id,
                models.User.role.in_(
                    ["doctor", "coder", "verifikator", "costing", "validator", "manajemen"]
                ),
                models.User.is_deleted == False,
            )
            .order_by(models.User.id.desc())
            .limit(10)
            .all()
        )
    else:
        data["users_dashboard"] = []

    # =========================
    # PATIENTS
    # =========================
    data["total_pasien"] = db.query(models.Patient).count()
    data["pasien_hari_ini"] = (
        db.query(models.Claim)
        .filter(models.Claim.claim_date == datetime.today().date())
        .count()
    )

    # =========================
    # CLAIMS
    # =========================
    data["total_claims"] = (
        db.query(models.Claim).filter(models.Claim.is_deleted == False).count()
    )
    data["claims"] = (
        db.query(models.Claim)
        .options(joinedload(models.Claim.patient))
        .filter(models.Claim.is_deleted == False)
        .order_by(models.Claim.id.desc())
        .limit(10)
        .all()
    )

    data["draft_claims"] = (
        db.query(models.Claim)
        .filter(models.Claim.is_final == False, models.Claim.is_deleted == False)
        .count()
    )
    data["final_claims"] = (
        db.query(models.Claim)
        .filter(models.Claim.is_final == True, models.Claim.is_deleted == False)
        .count()
    )

    data["draft_claims_list"] = []
    if current_user.role == "verifikator":
        data["draft_claims_list"] = (
            db.query(models.Claim)
            .options(joinedload(models.Claim.patient))
            .filter(models.Claim.is_final == False, models.Claim.is_deleted == False)
            .order_by(models.Claim.id.desc())
            .all()
        )

    data["final_claims_list"] = (
        db.query(models.Claim)
        .options(joinedload(models.Claim.patient))
        .filter(models.Claim.is_final == True, models.Claim.is_deleted == False)
        .order_by(models.Claim.id.desc())
        .all()
    )

    # =========================
    # TOTAL USERS (opsional)
    # =========================
    if current_user.role in ["superadmin", "admin_rs"]:
        data["total_users"] = db.query(models.User).count()
    else:
        data["total_users"] = None

    # =========================
    # PASIEN LIST (opsional)
    # =========================
    if current_user.role in ["doctor", "coder", "verifikator"]:
        data["pasien_list"] = (
            db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
        )
    else:
        data["pasien_list"] = []

    return data