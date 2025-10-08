"""
Module: backend.crud.user

CRUD helpers untuk User.
Operasi dasar: create, read, update, soft-delete.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend import models


# =========================
# GET
# =========================
def get_users_superadmin(db: Session) -> List[models.User]:
    """Superadmin hanya boleh lihat user dengan role admin_rs."""
    return (
        db.query(models.User)
        .filter(models.User.role == "admin_rs", models.User.is_deleted == False)
        .order_by(models.User.id.desc())
        .all()
    )

def get_users_admin_rs(db: Session, hospital_id: int) -> List[models.User]:
    """Admin RS hanya boleh lihat user RS yang sama (selain dirinya)."""
    return (
        db.query(models.User)
        .filter(
            models.User.hospital_id == hospital_id,
            models.User.role.in_(["doctor", "coder", "verifikator", "costing", "validator", "manajemen"]),
            models.User.is_deleted == False,
        )
        .order_by(models.User.id.desc())
        .all()
    )

def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    """Ambil user berdasarkan ID."""
    return db.query(models.User).filter(models.User.id == user_id, models.User.is_deleted == False).first()


# =========================
# CREATE
# =========================
def create_user(db: Session, data: Dict[str, Any]) -> models.User:
    """Buat user baru."""
    if "is_deleted" not in data:
        data["is_deleted"] = False
    if "is_dummy" not in data:
        data["is_dummy"] = True
    new_user = models.User(**data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# =========================
# UPDATE
# =========================
def update_user(db: Session, user_id: int, data: Dict[str, Any]) -> Optional[models.User]:
    """Update user berdasarkan ID."""
    user = db.query(models.User).filter(models.User.id == user_id, models.User.is_deleted == False).first()
    if not user:
        return None

    for key, value in data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


# =========================
# DELETE (Soft)
# =========================
def delete_user(db: Session, user_id: int) -> bool:
    """Soft-delete user (is_deleted=True)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return False
    user.is_deleted = True
    db.commit()
    return True