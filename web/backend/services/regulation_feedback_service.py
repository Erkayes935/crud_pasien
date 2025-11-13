"""
services/regulation_feedback_service.py
💬 Modul service untuk sistem feedback & tooltip multilayer regulasi.

Lokasi ini DI LUAR folder /claim karena modul ini bersifat lintas sistem:
- Dipakai oleh: Claim Regulation Router, Admin RS, dan Dashboard AI META.
- Berhubungan dengan tabel RulesMaster (aturan multilayer nasional & RS).
"""

from sqlalchemy.orm import Session
from backend import models
from datetime import datetime


# ======================================================
# 🎈 TOOLTIP SYSTEM
# ======================================================
def get_tooltip_for_field(db: Session, field_path: str, diagnosis: str | None = None):
    """
    Ambil 1–3 rules teratas untuk tooltip hover di FE.
    Urut berdasarkan prioritas layer.
    """
    layer_priority = {
        "permenkes": 1, "nasional": 2, "ppk": 3, "regional": 4,
        "rs": 5, "bridging": 6, "fraud": 7, "temporary": 8
    }

    query = db.query(models.RulesMaster).filter(
        models.RulesMaster.field == field_path,
        models.RulesMaster.status.in_(["official", "active"])
    )

    if diagnosis:
        query = query.filter(models.RulesMaster.diagnosis.ilike(f"%{diagnosis}%"))

    rules = query.all()
    sorted_rules = sorted(rules, key=lambda r: layer_priority.get(r.layer, 99))

    tooltip_sections = []
    for rule in sorted_rules[:3]:  # limit 3 rule teratas
        isi = (rule.isi or "").strip()
        if len(isi) > 120:
            isi = isi[:120] + "..."
        tooltip_sections.append({
            "layer": rule.layer.upper(),
            "text": isi,
            "source": rule.sumber,
            "color_class": get_layer_color_class(rule.layer)
        })

    summary = f"Ditemukan {len(rules)} aturan untuk field ini"
    if diagnosis:
        summary += f" (diagnosis: {diagnosis})"
    if not rules:
        summary = "Tidak ada aturan khusus untuk field ini"

    return {
        "field": field_path,
        "diagnosis": diagnosis,
        "summary": summary,
        "total_rules": len(rules),
        "tooltip_sections": tooltip_sections,
        "has_rules": len(rules) > 0
    }


# ======================================================
# 💬 FEEDBACK SYSTEM
# ======================================================
def submit_feedback(db: Session, rule_id: int, feedback_text: str, user):
    """
    Simpan feedback dari user (doctor/verifikator/admin_rs).
    """
    rule = db.query(models.RulesMaster).filter(models.RulesMaster.id == rule_id).first()
    if not rule:
        raise ValueError("Rule tidak ditemukan")

    user_identifier = f"{getattr(user, 'role', 'unknown')}"
    if hasattr(user, "hospital") and user.hospital:
        user_identifier += f"_{user.hospital.kode_hospital or f'rs_{user.hospital.id}'}"

    rule.feedback = feedback_text.strip()
    rule.feedback_by = user_identifier
    rule.feedback_date = datetime.now()
    rule.updated_at = datetime.now()

    db.commit()

    return {
        "status": "success",
        "message": "Feedback berhasil disimpan",
        "rule_id": rule_id,
        "feedback_by": user_identifier
    }


# ======================================================
# 📋 LIST FEEDBACK UNTUK DASHBOARD
# ======================================================
def get_all_feedback(db: Session):
    """
    Ambil semua rules yang memiliki feedback.
    Digunakan oleh dashboard AI META atau admin pusat.
    """
    rules = db.query(models.RulesMaster).filter(
        models.RulesMaster.feedback.isnot(None)
    ).order_by(models.RulesMaster.feedback_date.desc()).all()

    result = []
    for r in rules:
        result.append({
            "id": r.id,
            "diagnosis": r.diagnosis,
            "field": r.field,
            "layer": r.layer,
            "isi": r.isi,
            "sumber": r.sumber,
            "rs_id": r.rs_id,
            "feedback": r.feedback,
            "feedback_by": r.feedback_by,
            "feedback_date": r.feedback_date.isoformat() if r.feedback_date else None,
            "status": r.status
        })
    return result


# ======================================================
# 🎨 UTIL - Layer Color
# ======================================================
def get_layer_color_class(layer: str) -> str:
    """Kembalikan warna teks sesuai layer."""
    layer_colors = {
        "permenkes": "text-red-600", "nasional": "text-orange-600",
        "ppk": "text-yellow-600", "regional": "text-green-600",
        "rs": "text-blue-600", "bridging": "text-indigo-600",
        "fraud": "text-purple-600", "temporary": "text-gray-600"
    }
    return layer_colors.get(layer, "text-gray-500")
