"""
services/regulation_admin_service.py
⚙️ Service untuk manajemen regulasi oleh Admin RS & AI META.

Berisi logika CRUD rules (layer PPK & RS Lokal) dan upload laporan regional (SE).
"""

import os, uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend import models


# ======================================================
# 🧩 CRUD RULES (PPK & RS LOKAL)
# ======================================================
def get_my_rs_rules(db: Session, user):
    """Ambil seluruh rules milik RS user login (layer ppk & rs)."""
    user_rs_id = None
    if hasattr(user, "hospital") and user.hospital:
        user_rs_id = user.hospital.kode_hospital or f"rs_{user.hospital.id}"

    rules = (
        db.query(models.RulesMaster)
        .filter(
            and_(
                models.RulesMaster.rs_id == user_rs_id,
                models.RulesMaster.layer.in_(["ppk", "rs"]),
            )
        )
        .order_by(models.RulesMaster.created_at.desc())
        .all()
    )

    grouped = {"ppk": {}, "rs": {}}
    for rule in rules:
        grouped.setdefault(rule.layer, {}).setdefault(rule.status, []).append({
            "id": rule.id,
            "diagnosis": rule.diagnosis,
            "field": rule.field,
            "isi": rule.isi,
            "sumber": rule.sumber,
            "created_at": rule.created_at.isoformat(),
            "updated_at": rule.updated_at.isoformat(),
            "status": rule.status,
        })
    return grouped


def add_rule(db: Session, user, diagnosis: str, field: str, layer: str, isi: str, sumber: str, pdf_file):
    """Tambah rule baru untuk RS."""
    if layer not in ["ppk", "rs"]:
        raise ValueError("Layer tidak diizinkan untuk Admin RS")

    # ambil RS info
    user_rs_id = None
    if hasattr(user, "hospital") and user.hospital:
        user_rs_id = user.hospital.kode_hospital or f"rs_{user.hospital.id}"

    pdf_filename = None
    if pdf_file and pdf_file.filename:
        upload_dir = "web/uploads/rules_pdf"
        os.makedirs(upload_dir, exist_ok=True)
        if pdf_file.content_type != "application/pdf":
            raise ValueError("File harus PDF")

        file_extension = pdf_file.filename.split(".")[-1]
        pdf_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(upload_dir, pdf_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(pdf_file.file.read())

    new_rule = models.RulesMaster(
        diagnosis=diagnosis.strip(),
        field=field.strip(),
        layer=layer,
        isi=isi.strip(),
        sumber=sumber.strip(),
        pdf_file=pdf_filename,
        rs_id=user_rs_id,
        region_id="jatim",  # default sementara
        status="unverified",
        created_by=f"admin_rs_{user_rs_id}",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule


def update_rule(db: Session, user, rule_id: int, diagnosis: str, field: str, isi: str, sumber: str):
    """Edit rule yang masih unverified."""
    user_rs_id = None
    if hasattr(user, "hospital") and user.hospital:
        user_rs_id = user.hospital.kode_hospital or f"rs_{user.hospital.id}"

    rule = (
        db.query(models.RulesMaster)
        .filter(
            and_(
                models.RulesMaster.id == rule_id,
                models.RulesMaster.rs_id == user_rs_id,
                models.RulesMaster.layer.in_(["ppk", "rs"]),
            )
        )
        .first()
    )
    if not rule:
        raise ValueError("Rule tidak ditemukan atau bukan milik RS ini")
    if rule.status != "unverified":
        raise ValueError(f"Rule status '{rule.status}' tidak bisa diedit")

    rule.diagnosis, rule.field, rule.isi, rule.sumber = (
        diagnosis.strip(),
        field.strip(),
        isi.strip(),
        sumber.strip(),
    )
    rule.updated_at = datetime.now()
    db.commit()
    return rule


def delete_rule(db: Session, user, rule_id: int):
    """Soft delete rule unverified."""
    user_rs_id = None
    if hasattr(user, "hospital") and user.hospital:
        user_rs_id = user.hospital.kode_hospital or f"rs_{user.hospital.id}"

    rule = (
        db.query(models.RulesMaster)
        .filter(
            and_(
                models.RulesMaster.id == rule_id,
                models.RulesMaster.rs_id == user_rs_id,
                models.RulesMaster.status == "unverified",
            )
        )
        .first()
    )
    if not rule:
        raise ValueError("Rule tidak ditemukan atau tidak bisa dihapus")

    rule.status = "deleted"
    rule.updated_at = datetime.now()
    db.commit()
    return rule


# ======================================================
# 📂 REGIONAL REPORT (UPLOAD SE)
# ======================================================
def add_regional_report(db: Session, user, title: str, description: str, se_file):
    """Upload file SE regional (PDF) untuk dikirim ke AI META."""
    if not se_file.filename.endswith(".pdf"):
        raise ValueError("File harus PDF")
    if hasattr(se_file, "size") and se_file.size > 10 * 1024 * 1024:
        raise ValueError("Ukuran maksimal 10MB")

    user_rs_id = None
    if hasattr(user, "hospital") and user.hospital:
        user_rs_id = user.hospital.kode_hospital or f"rs_{user.hospital.id}"

    upload_dir = "web/uploads/regional_se"
    os.makedirs(upload_dir, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(upload_dir, unique_filename)
    with open(file_path, "wb") as buffer:
        buffer.write(se_file.file.read())

    report = models.RegionalReports(
        title=title.strip(),
        description=description.strip(),
        se_file=unique_filename,
        region_id="jatim",
        rs_id=user_rs_id,
        status="pending",
        reported_by=f"admin_rs_{user_rs_id}",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
