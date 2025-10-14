"""
Module: backend.crud.user

CRUD helpers untuk User.
Sekarang mendukung sistem multi-role (User–Role–UserRole) 
namun tetap kompatibel dengan kolom role tunggal lama.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session, joinedload
from backend import models


# =====================================================
# HELPER
# =====================================================

def _matches_any_role(user: models.User, allowed_roles: List[str]) -> bool:
    """
    Helper untuk memeriksa apakah user memiliki salah satu dari allowed_roles.
    Kompatibel untuk user lama (kolom role) maupun user baru (relasi roles).
    """
    if not user:
        return False

    # Ambil daftar role dari helper di models.py
    roles = user.role_names if hasattr(user, "role_names") else []
    return any(r in allowed_roles for r in roles)


# =====================================================
# GET
# =====================================================

def get_users_superadmin(db: Session) -> List[models.User]:
    """Superadmin hanya boleh lihat user dengan role admin_rs."""
    users = (
        db.query(models.User)
        .options(joinedload(models.User.roles))
        .filter(models.User.is_deleted == False)
        .order_by(models.User.id.desc())
        .all()
    )
    return [u for u in users if _matches_any_role(u, ["admin_rs"])]


def get_users_admin_rs(db: Session, hospital_id: int) -> List[models.User]:
    """Admin RS hanya boleh lihat user RS yang sama (selain dirinya)."""
    users = (
        db.query(models.User)
        .options(joinedload(models.User.roles))
        .filter(
            models.User.hospital_id == hospital_id,
            models.User.is_deleted == False,
        )
        .order_by(models.User.id.desc())
        .all()
    )
    allowed_roles = ["doctor", "coder", "verifikator", "costing", "validator", "manajemen"]
    return [u for u in users if _matches_any_role(u, allowed_roles)]


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    """Ambil user berdasarkan ID."""
    return (
        db.query(models.User)
        .options(joinedload(models.User.roles))
        .filter(models.User.id == user_id, models.User.is_deleted == False)
        .first()
    )


# =====================================================
# CREATE
# =====================================================

def create_user(db: Session, data: Dict[str, Any]) -> models.User:
    """
    Buat user baru.
    Bisa dipanggil baik dari sistem lama (pakai kolom role)
    maupun sistem baru (langsung isi roles list).
    """
    if "is_deleted" not in data:
        data["is_deleted"] = False
    if "is_dummy" not in data:
        data["is_dummy"] = True

    # Jika data mengandung "roles" (list of role names)
    roles_data = data.pop("roles", None)

    new_user = models.User(**data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Assign role relasi jika ada
    if roles_data:
        role_objs = db.query(models.Role).filter(models.Role.name.in_(roles_data)).all()
        new_user.roles = role_objs
        db.commit()
        db.refresh(new_user)

    return new_user


# =====================================================
# UPDATE
# =====================================================

def update_user(db: Session, user_id: int, data: Dict[str, Any]) -> Optional[models.User]:
    """Update user berdasarkan ID."""
    user = (
        db.query(models.User)
        .options(joinedload(models.User.roles))
        .filter(models.User.id == user_id, models.User.is_deleted == False)
        .first()
    )
    if not user:
        return None

    roles_data = data.pop("roles", None)

    # Update field biasa
    for key, value in data.items():
        setattr(user, key, value)

    # Update role relasi jika dikirim
    if roles_data is not None:
        role_objs = db.query(models.Role).filter(models.Role.name.in_(roles_data)).all()
        user.roles = role_objs

    db.commit()
    db.refresh(user)
    return user


# =====================================================
# DELETE (Soft)
# =====================================================

def delete_user(db: Session, user_id: int) -> bool:
    """Soft-delete user (is_deleted=True)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return False
    user.is_deleted = True
    db.commit()
    return True


# =====================================================
# EXTRA HELPERS
# =====================================================

def get_user_roles(db: Session, user_id: int) -> List[str]:
    """Ambil semua role user (gabungan kolom lama dan relasi baru)."""
    user = db.query(models.User).options(joinedload(models.User.roles)).filter(models.User.id == user_id).first()
    return user.role_names if user else []
