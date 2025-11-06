"""
routers/claim/_utils.py
Kumpulan fungsi bantu (helper) untuk modul klaim:
- normalisasi parameter
- parsing integer
- membangun base query sesuai role user
- menerapkan filter lanjutan
- eagerload relasi ORM
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from backend import models


# ======================================================
# 🧩 NORMALISASI & PARSER
# ======================================================

def normalize_str(value: str | None) -> str | None:
    """Hilangkan spasi dan ubah string kosong jadi None"""
    if not value:
        return None
    value = value.strip()
    return value or None


def parse_int(value: str | None) -> int | None:
    """Ubah string ke int dengan aman"""
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


# ======================================================
# 🧱 QUERY BUILDER
# ======================================================

def build_base_query(db: Session, user):
    """
    Bangun query dasar untuk klaim sesuai role user.
    Mengembalikan (query, joined_flags)
    """
    q = db.query(models.Claim)
    roles = user.role_names or []
    if "verifikator" in roles and "coder" not in roles and "doctor" not in roles:
        q = q.filter(models.Claim.workflow_status.in_(
            ["coder_verified", "verifikator_review", "finalized"]
        ))
    elif "coder" in roles and "verifikator" not in roles and "doctor" not in roles:
        q = q.filter(models.Claim.workflow_status.in_(
            ["doctor_submitted", "coder_review", "coder_verified"]
        ))
    elif "doctor" in roles and "coder" not in roles and "verifikator" not in roles:
        q = q.filter(models.Claim.doctor_id == user.id)

    joined = dict(patient=False, visit=False, diagnosis=False, procedure=False, user=False)
    return q, joined


# ======================================================
# 🔍 FILTERING
# ======================================================

def apply_filters(q, f, joined):
    """
    Terapkan filter pencarian lanjutan ke query klaim.
    Bisa terima object atau dict (lebih fleksibel).
    """
    M = models

    # 🔹 Pastikan akses pakai get() universal
    def get_value(key):
        if isinstance(f, dict):
            return f.get(key)
        return getattr(f, key, None)

    patient_name = get_value("patient_name")
    tanggal_kunjungan = get_value("tanggal_kunjungan")
    claim_id = get_value("claim_id")
    visit_id = get_value("visit_id")
    diagnosis = get_value("diagnosis")
    tindakan = get_value("tindakan")
    doctor_name = get_value("doctor_name")
    status = get_value("status")
    workflow_status = get_value("workflow_status")

    # 🔹 Filter sesuai field (kode lama disesuaikan)
    if patient_name:
        if not joined["patient"]:
            q = q.join(M.Patient, M.Claim.patient_id == M.Patient.id)
            joined["patient"] = True
        q = q.filter(M.Patient.nama.ilike(f"%{patient_name}%"))

    if tanggal_kunjungan:
        if not joined["visit"]:
            q = q.join(M.Visit, M.Claim.visit_id == M.Visit.id)
            joined["visit"] = True
        q = q.filter(M.Visit.tanggal_kunjungan == tanggal_kunjungan)

    if claim_id:
        q = q.filter(M.Claim.id == claim_id)

    if visit_id:
        q = q.filter(M.Claim.visit_id == visit_id)

    if diagnosis:
        if not joined["diagnosis"]:
            q = q.join(M.ClaimDiagnosis, M.Claim.id == M.ClaimDiagnosis.claim_id)
            joined["diagnosis"] = True
        q = q.filter(
            or_(
                M.ClaimDiagnosis.diagnosis_text.ilike(f"%{diagnosis}%"),
                M.ClaimDiagnosis.icd10_code.ilike(f"%{diagnosis}%")
            ),
            M.ClaimDiagnosis.is_deleted == False
        )

    if tindakan:
        if not joined["procedure"]:
            q = q.join(M.ClaimProcedure, M.Claim.id == M.ClaimProcedure.claim_id)
            joined["procedure"] = True
        q = q.filter(
            or_(
                M.ClaimProcedure.procedure_text.ilike(f"%{tindakan}%"),
                M.ClaimProcedure.icd9_final_by_coder.ilike(f"%{tindakan}%")
            ),
            M.ClaimProcedure.is_deleted == False
        )

    if doctor_name:
        if not joined["user"]:
            q = q.outerjoin(M.User, M.Claim.doctor_id == M.User.id)
            joined["user"] = True
        q = q.filter(
            or_(
                M.Claim.doctor_name.ilike(f"%{doctor_name}%"),
                M.User.name.ilike(f"%{doctor_name}%")
            )
        )

    if status:
        q = q.filter(M.Claim.status == status)
    if workflow_status:
        q = q.filter(M.Claim.workflow_status == workflow_status)

    return q, joined



# ======================================================
# 🚀 EAGERLOAD
# ======================================================

def eagerload_relations(q, joined):
    """Tambahkan eagerload untuk relasi penting klaim"""
    M = models
    if not joined["patient"]:
        q = q.options(joinedload(M.Claim.patient))
    if not joined["visit"]:
        q = q.options(joinedload(M.Claim.visit))
    q = q.options(
        joinedload(M.Claim.hospital),
        joinedload(M.Claim.group),
        joinedload(M.Claim.diagnoses),
        joinedload(M.Claim.procedures),
        joinedload(M.Claim.tariffs),
        joinedload(M.Claim.ai_recommendations),
    )
    # if joined["diagnosis"] or joined["procedure"]:
    #     q = q.distinct()
    return q

# ======================================================
# 📊 ENHANCED CLAIM LIST HELPERS (FROM CLAIM_ROUTER.PY)
# ======================================================

def get_primary_diagnosis(claim):
    """Ambil diagnosis utama dari klaim."""
    if not claim.diagnoses:
        return "-"
    primary = next((d for d in claim.diagnoses if d.diagnosis_type == "utama" and not d.is_deleted), None)
    if primary:
        return f"{primary.diagnosis_text} ({primary.icd10_code or '-'})"
    if claim.medical_record and claim.medical_record.diagnosis_akhir:
        return claim.medical_record.diagnosis_akhir
    return "-"


def get_secondary_diagnoses(claim):
    """Hitung jumlah diagnosis sekunder dari klaim."""
    try:
        if not hasattr(claim, "diagnoses") or not claim.diagnoses:
            return 0
        return len([d for d in claim.diagnoses if d.diagnosis_type == "sekunder" and not d.is_deleted])
    except Exception as e:
        print(f"[SECONDARY_DIAGNOSES] Error for claim {getattr(claim, 'id', '-')}: {e}")
        return 0


def get_primary_procedure(claim):
    """Ambil tindakan utama dari klaim."""
    if not claim.procedures:
        return "-"
    primary = next((p for p in claim.procedures if p.procedure_source == "utama" and not p.is_deleted), None)
    if primary:
        icd9_code = primary.icd9_final_by_coder if primary.icd9_final_by_coder else "-"
        return f"{primary.procedure_text} ({icd9_code})"
    if claim.medical_record and claim.medical_record.tindakan:
        return claim.medical_record.tindakan
    return "-"


def get_tariffs_optimized(claim):
    """Ambil tarif INA-CBG dan RS secara efisien."""
    ina_cbg_amount = 0
    rs_amount = 0
    if not claim.tariffs:
        return ina_cbg_amount, rs_amount

    for t in claim.tariffs:
        if t.is_deleted:
            continue
        if ina_cbg_amount > 0 and rs_amount > 0:
            break
        if ina_cbg_amount == 0 and t.tariff_amount:
            cbg_code_lower = (t.cbg_code or "").lower()
            desc_lower = (t.description or "").lower()
            if "ina" in cbg_code_lower or "cbg" in cbg_code_lower or "ina" in desc_lower or "cbg" in desc_lower:
                ina_cbg_amount = t.tariff_amount
                continue
        if rs_amount == 0 and t.tariff_amount:
            desc_lower = (t.description or "").lower()
            if "rs" in desc_lower or "hospital" in desc_lower:
                rs_amount = t.tariff_amount
    return ina_cbg_amount, rs_amount


def calculate_length_of_stay(claim):
    """Hitung lama rawat inap (LOS)."""
    if not claim.visit or not claim.visit.tanggal_kunjungan:
        return 0
    if claim.created_at and claim.visit.tanggal_kunjungan:
        claim_date = claim.created_at.date()
        visit_date = claim.visit.tanggal_kunjungan
        if claim_date >= visit_date:
            delta = claim_date - visit_date
            return delta.days + 1
    return 1


def aggregate_ai_notifications(claim):
    """Kompilasi notifikasi AI untuk satu klaim."""
    if not claim.ai_recommendations:
        return {
            "total_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "success_count": 0,
            "max_severity": "info",
            "summary_text": "Belum ada analisis AI",
            "status_icon": "⚪",
        }

    notifications = {"error_count": 0, "warning_count": 0, "info_count": 0, "success_count": 0}
    for rec in claim.ai_recommendations:
        if rec.is_deleted:
            continue
        if rec.confidence_score is not None:
            if rec.confidence_score >= 90:
                notifications["success_count"] += 1
            elif rec.confidence_score >= 70:
                notifications["info_count"] += 1
            elif rec.confidence_score >= 50:
                notifications["warning_count"] += 1
            else:
                notifications["error_count"] += 1
        else:
            notifications["info_count"] += 1

    total = sum(notifications.values())
    if notifications["error_count"] > 0:
        max_severity = "error"
        status_icon = "❌"
    elif notifications["warning_count"] > 0:
        max_severity = "warning"
        status_icon = "⚠️"
    elif notifications["info_count"] > 0:
        max_severity = "info"
        status_icon = "ℹ️"
    elif notifications["success_count"] > 0:
        max_severity = "success"
        status_icon = "✅"
    else:
        max_severity = "info"
        status_icon = "⚪"

    if total == 0:
        summary_text = "Belum ada analisis"
    else:
        parts = []
        if notifications["error_count"] > 0:
            parts.append(f"{notifications['error_count']} Error")
        if notifications["warning_count"] > 0:
            parts.append(f"{notifications['warning_count']} Warning")
        if notifications["info_count"] > 0:
            parts.append(f"{notifications['info_count']} Info")
        if notifications["success_count"] > 0:
            parts.append(f"{notifications['success_count']} OK")
        summary_text = ", ".join(parts)

    return {
        "total_count": total,
        "max_severity": max_severity,
        "status_icon": status_icon,
        "summary_text": summary_text,
        **notifications,
    }


# ======================================================
# 📦 LIST-BASED HELPERS (BATCH OPERATIONS)
# ======================================================

def get_primary_diagnosis_from_list(diagnoses_list):
    """Ambil diagnosis utama dari list ClaimDiagnosis."""
    if not diagnoses_list:
        return "-"
    primary = next((d for d in diagnoses_list if d.diagnosis_type == "utama" and not d.is_deleted), None)
    if primary:
        return f"{primary.diagnosis_text} ({primary.icd10_code or '-'})"
    return "-"


def get_primary_procedure_from_list(procedures_list):
    """Ambil tindakan utama dari list ClaimProcedure."""
    if not procedures_list:
        return "-"
    primary = next((p for p in procedures_list if p.procedure_source == "utama" and not p.is_deleted), None)
    if primary:
        icd9_code = primary.icd9_final_by_coder if primary.icd9_final_by_coder else "-"
        return f"{primary.procedure_text} ({icd9_code})"
    return "-"


def get_tariffs_from_list(tariffs_list):
    """Ambil tarif INA-CBG dan RS dari list ClaimTariff."""
    ina_cbg_amount = 0
    rs_amount = 0
    if not tariffs_list:
        return ina_cbg_amount, rs_amount

    for t in tariffs_list:
        if t.is_deleted:
            continue
        if ina_cbg_amount > 0 and rs_amount > 0:
            break
        if ina_cbg_amount == 0 and t.tariff_amount:
            cbg_code_lower = (t.cbg_code or "").lower()
            desc_lower = (t.description or "").lower()
            if "ina" in cbg_code_lower or "cbg" in cbg_code_lower or "ina" in desc_lower or "cbg" in desc_lower:
                ina_cbg_amount = t.tariff_amount
                continue
        if rs_amount == 0 and t.tariff_amount:
            desc_lower = (t.description or "").lower()
            if "rs" in desc_lower or "hospital" in desc_lower:
                rs_amount = t.tariff_amount
    return ina_cbg_amount, rs_amount


def aggregate_ai_notifications_from_list(ai_recs_list):
    """Kompilasi notifikasi AI dari list ClaimAIRecommendation."""
    if not ai_recs_list:
        return {
            "total_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "success_count": 0,
            "max_severity": "info",
            "summary_text": "Belum ada analisis AI",
            "status_icon": "⚪",
        }

    notifications = {"error_count": 0, "warning_count": 0, "info_count": 0, "success_count": 0}
    for rec in ai_recs_list:
        if rec.is_deleted:
            continue
        if rec.confidence_score is not None:
            if rec.confidence_score >= 90:
                notifications["success_count"] += 1
            elif rec.confidence_score >= 70:
                notifications["info_count"] += 1
            elif rec.confidence_score >= 50:
                notifications["warning_count"] += 1
            else:
                notifications["error_count"] += 1
        else:
            notifications["info_count"] += 1

    total = sum(notifications.values())
    if notifications["error_count"] > 0:
        max_severity = "error"
        status_icon = "❌"
    elif notifications["warning_count"] > 0:
        max_severity = "warning"
        status_icon = "⚠️"
    elif notifications["info_count"] > 0:
        max_severity = "info"
        status_icon = "ℹ️"
    elif notifications["success_count"] > 0:
        max_severity = "success"
        status_icon = "✅"
    else:
        max_severity = "info"
        status_icon = "⚪"

    if total == 0:
        summary_text = "Belum ada analisis"
    else:
        parts = []
        if notifications["error_count"] > 0:
            parts.append(f"{notifications['error_count']} Error")
        if notifications["warning_count"] > 0:
            parts.append(f"{notifications['warning_count']} Warning")
        if notifications["info_count"] > 0:
            parts.append(f"{notifications['info_count']} Info")
        if notifications["success_count"] > 0:
            parts.append(f"{notifications['success_count']} OK")
        summary_text = ", ".join(parts)

    return {
        "total_count": total,
        "max_severity": max_severity,
        "status_icon": status_icon,
        "summary_text": summary_text,
        **notifications,
    }

def count_workflow_status(db, query):
    from sqlalchemy import func
    from backend import models
    result = db.query(
        models.Claim.workflow_status,
        func.count(models.Claim.id).label("count")
    ).filter(
        *query.whereclause.clauses if hasattr(query.whereclause, "clauses") else []
    ).group_by(models.Claim.workflow_status).all()

    counts = {
        "draft": 0,
        "doctor_submitted": 0,
        "coder_review": 0,
        "coder_verified": 0,
        "verifikator_review": 0,
        "finalized": 0,
    }
    for status, count in result:
        if status in counts:
            counts[status] = count
    return counts


def count_ai_alerts(db, user):
    from backend import models
    from sqlalchemy import func
    roles = user.role_names or []
    q = db.query(func.count(func.distinct(models.ClaimAIRecommendation.claim_id))).join(
        models.Claim, models.ClaimAIRecommendation.claim_id == models.Claim.id
    ).filter(models.ClaimAIRecommendation.is_deleted == False)
    if "doctor" in roles:
        q = q.filter(models.Claim.doctor_id == user.id)
    return q.scalar() or 0


def sum_total_tarif(db, user):
    from backend import models
    from sqlalchemy import func
    roles = user.role_names or []
    q = db.query(func.sum(models.ClaimTariff.tariff_amount)).join(
        models.Claim, models.ClaimTariff.claim_id == models.Claim.id
    ).filter(models.ClaimTariff.is_deleted == False)
    if "doctor" in roles:
        q = q.filter(models.Claim.doctor_id == user.id)
    return q.scalar() or 0


def enrich_claim_data(db, claims_raw, ai_status, tarif_cbg_min, tarif_cbg_max, los_min, los_max):
    from backend import models
    claims = []
    for c in claims_raw:
        c.patient_name = getattr(c.patient, "nama", "-")
        c.patient_rm = getattr(c.patient, "no_rm", "-")
        c.tanggal_kunjungan = getattr(c.visit, "tanggal_kunjungan", None)
        c.hospital_name = getattr(c.hospital, "nama", "-")

        c.diagnosis_utama = get_primary_diagnosis(c)
        c.diagnosis_sekunder = get_secondary_diagnoses(c)
        c.tindakan_utama = get_primary_procedure(c)
        c.tarif_ina_cbg, c.tarif_rs = get_tariffs_optimized(c)
        c.lama_rawat = calculate_length_of_stay(c)
        c.ai_status = aggregate_ai_notifications(c)

        include = True
        if ai_status:
            if ai_status == "not_analyzed" and c.ai_status["total_count"] > 0:
                include = False
            elif ai_status != "not_analyzed" and c.ai_status["max_severity"] != ai_status:
                include = False
        if tarif_cbg_min and c.tarif_ina_cbg < tarif_cbg_min:
            include = False
        if tarif_cbg_max and c.tarif_ina_cbg > tarif_cbg_max:
            include = False
        if los_min and c.lama_rawat < los_min:
            include = False
        if los_max and c.lama_rawat > los_max:
            include = False
        if include:
            claims.append(c)
    return claims
