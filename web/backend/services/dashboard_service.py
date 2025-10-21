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
    # CLAIMS (role-based)
    # =========================
    roles = current_user.role_names or [current_user.role]
    query = db.query(models.Claim).options(joinedload(models.Claim.patient))
    query = query.filter(models.Claim.is_deleted == False)

    # === ROLE FILTERS ===
    if "doctor" in roles and not any(r in roles for r in ["coder", "verifikator"]):
        # Dokter hanya klaim miliknya yang masih draft / belum disubmit final
        query = query.filter(
            models.Claim.doctor_id == current_user.id,
            models.Claim.workflow_status.in_(["draft", "doctor_submitted"])
        )

    elif "coder" in roles and not any(r in roles for r in ["doctor", "verifikator"]):
        # Coder melihat klaim yang siap atau sedang direview
        query = query.filter(
            models.Claim.workflow_status.in_(
                ["doctor_submitted", "coder_review", "coder_verified"]
            )
        )

    elif "verifikator" in roles and not any(r in roles for r in ["doctor", "coder"]):
        # Verifikator hanya klaim yang sudah diverifikasi coder
        query = query.filter(
            models.Claim.workflow_status.in_(
                ["coder_verified", "verifikator_review"]
            )
        )

    elif any(r in roles for r in ["superadmin", "admin_rs"]):
        # Admin/Superadmin → semua klaim RS-nya
        if hasattr(current_user, "hospital") and current_user.hospital:
            query = query.filter(models.Claim.hospital_id == current_user.hospital.id)

    else:
        # Multi-role → semua klaim di RS
        if hasattr(current_user, "hospital") and current_user.hospital:
            query = query.filter(models.Claim.hospital_id == current_user.hospital.id)

    # === Ambil data klaim ===
    data["claims"] = query.order_by(models.Claim.created_at.desc()).limit(10).all()

    # === Statistik umum ===
    data["total_claims"] = db.query(models.Claim).filter(models.Claim.is_deleted == False).count()
    data["draft_claims"] = (
        db.query(models.Claim)
        .filter(
            models.Claim.is_final == False,
            models.Claim.is_deleted == False,
            models.Claim.workflow_status.in_(["draft", "doctor_submitted"])
        )
        .count()
    )
    data["final_claims"] = (
        db.query(models.Claim)
        .filter(
            models.Claim.is_final == True,
            models.Claim.is_deleted == False,
            (
                (models.Claim.workflow_status == None) |
                (models.Claim.workflow_status == "") |
                (models.Claim.workflow_status == "finalized") |
                (models.Claim.workflow_status == "approved")
            )
        )
        .count()
    )


    # === List final (tetap untuk tabel bawah) ===
    data["final_claims_list"] = (
        db.query(models.Claim)
        .options(joinedload(models.Claim.patient))
        .filter(
            models.Claim.is_final == True,
            models.Claim.is_deleted == False,
            (
                (models.Claim.workflow_status == None) |
                (models.Claim.workflow_status == "") |
                (models.Claim.workflow_status == "finalized") |
                (models.Claim.workflow_status == "approved")
            )
        )
        .order_by(models.Claim.id.desc())
        .limit(10)
        .all()
    )


    # =========================
    # TOTAL USERS & PASIEN LIST
    # =========================
    if current_user.role in ["superadmin", "admin_rs"]:
        data["total_users"] = db.query(models.User).count()
    else:
        data["total_users"] = None

    if any(r in roles for r in ["doctor", "coder", "verifikator"]):
        data["pasien_list"] = (
            db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
        )
    else:
        data["pasien_list"] = []

    return data
