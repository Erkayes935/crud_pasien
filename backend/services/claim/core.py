from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from ... import models
from .helper import parse_number, _update_or_create_procedure, _update_diag_fields, _update_medical_record_from_form
from .simulation import save_simulation_and_summary
import json

# ==================================================
# ADD CLAIM -> move from crud
# ==================================================
def add_claim_service(db: Session, user, form_data: dict):
    """Buat klaim baru + rekam medis baru (status draft by default)"""

    claim_date = form_data.get("claim_date") or datetime.utcnow()

    # 1. Buat rekam medis
    mr = models.MedicalRecord(
        record_type="claim",
        patient_id=form_data.get("patient_id"),
        visit_id=form_data.get("visit_id"),
        doctor_id=form_data.get("doctor_id"),
        doctor_name=form_data.get("doctor_name"),
        is_final=False,
        notes_date=datetime.utcnow(),
        created_at=datetime.utcnow() - timedelta(days=5),
        updated_at=datetime.utcnow(),
        is_deleted=bool(form_data.get("is_deleted")) if form_data.get("is_deleted") not in (None, "", "null") else False,
        is_dummy=bool(form_data.get("is_dummy")) if form_data.get("is_dummy") not in (None, "", "null") else False,
    )

    db.add(mr)
    db.flush()
    db.refresh(mr)

    # isi semua field medis dari form
    _update_medical_record_from_form(db, type("obj", (), {"medical_record": mr}), user, form_data, action="CREATED")

    # rekam medis log
    latest_version = db.query(func.max(models.MedicalRecordLog.version)) \
                       .filter(models.MedicalRecordLog.medical_record_id == mr.id) \
                       .scalar() or 0
    db.add(models.MedicalRecordLog(
        medical_record_id=mr.id,
        action="CREATED",
        description=f"Rekam medis {mr.id} dibuat oleh {user.name}",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        version=latest_version + 1,
        data_snapshot=json.dumps(mr.to_dict() if hasattr(mr, "to_dict") else {}, ensure_ascii=False),
        is_deleted=False,
        is_dummy=False
    ))

    # 2. Buat klaim baru
    claim = models.Claim(
        claim_date=claim_date,
        patient_id=form_data.get("patient_id"),
        visit_id=form_data.get("visit_id"),
        hospital_id=form_data.get("hospital_id"),
        doctor_id=form_data.get("doctor_id"),
        doctor_name=form_data.get("doctor_name"),
        medical_record_id=mr.id,
        is_final=False,
        status="draft",
        created_at=datetime.utcnow() - timedelta(days=5),
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=bool(form_data.get("is_dummy")) if form_data.get("is_dummy") not in (None, "", "null") else False,
    )
    db.add(claim)
    db.flush()
    db.refresh(claim)

    # klaim log
    db.add(models.ClaimLog(
        claim_id=claim.id,
        action="CREATED",
        description=f"Klaim {claim.id} dibuat oleh {user.name}",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=True
    ))
    db.commit()
    return claim
    
    
# ==================================================
# Claim Draft Service Functions
# ==================================================
def update_claim_draft_service(db: Session, claim_id: int, user, form_data: dict):
    """Update klaim dalam status draft + update rekam medis"""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Parsing simulasi & summary dari form
    sim_data, summ_data = {}, {}
    simulasi = form_data.get("simulasi")
    summary = form_data.get("summary")

    if simulasi:
        try:
            sim_data = json.loads(simulasi)
        except Exception as e:
            print("❌ Gagal parse simulasi:", e)
    if summary:
        try:
            summ_data = json.loads(summary)
        except Exception as e:
            print("❌ Gagal parse summary:", e)

    # Update ClaimDiagnosis & ClaimProcedure
    try:
        for stage, stage_data in sim_data.items():
            # === Diagnosis Utama ===
            if "utama" in stage_data and stage_data["utama"]:
                diag = db.query(models.ClaimDiagnosis).filter_by(
                    claim_id=claim.id, diagnosis_text=stage_data["utama"]["name"]
                ).first()
                if not diag:
                    diag = models.ClaimDiagnosis(
                        claim_id=claim.id,
                        diagnosis_type="utama",
                        diagnosis_text=stage_data["utama"]["name"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True,
                    )
                    db.add(diag)
                    db.flush()
                _update_diag_fields(diag, stage_data["utama"])

            # === Diagnosis Sekunder ===
            for sec in stage_data.get("sekunder", []):
                diag = db.query(models.ClaimDiagnosis).filter_by(
                    claim_id=claim.id, diagnosis_text=sec["name"]
                ).first()
                if not diag:
                    diag = models.ClaimDiagnosis(
                        claim_id=claim.id,
                        diagnosis_type="sekunder",
                        diagnosis_text=sec["name"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True,
                    )
                    db.add(diag)
                    db.flush()
                _update_diag_fields(diag, sec)

            # === Tindakan Utama ===
            if "tindakanUtama" in stage_data and stage_data["tindakanUtama"]:
                _update_or_create_procedure(
                    db, claim, stage_data["tindakanUtama"], "utama"
                )

            # === Tindakan Sekunder ===
            for td in stage_data.get("tindakanSekunder", []):
                _update_or_create_procedure(db, claim, td, "sekunder")

        db.flush()
    except Exception as e:
        print("❌ Gagal update ClaimDiagnosis/ClaimProcedure:", e)

    # Save simulasi & summary
    save_simulation_and_summary(db, claim.id, sim_data, summ_data)

    # Update draft status
    claim.is_final = False
    claim.status = "draft"
    claim.updated_at = datetime.utcnow()

    # Update rekam medis
    _update_medical_record_from_form(db, claim, user, form_data, action="UPDATED")

    # Klaim log
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
# Finalize Claim
# ==================================================
def finalize_claim_service(db: Session, claim_id: int, user, form_data: dict):
    """Finalize klaim + update rekam medis"""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Parsing simulasi & summary
    sim_data, summ_data = {}, {}
    simulasi = form_data.get("simulasi")
    summary = form_data.get("summary")

    if simulasi:
        try:
            sim_data = json.loads(simulasi)
        except Exception as e:
            print("❌ Gagal parse simulasi:", e)
    if summary:
        try:
            summ_data = json.loads(summary)
        except Exception as e:
            print("❌ Gagal parse summary:", e)

    # Update Diagnosis & Procedure sama seperti draft
    try:
        for stage, stage_data in sim_data.items():
            if "utama" in stage_data and stage_data["utama"]:
                diag = db.query(models.ClaimDiagnosis).filter_by(
                    claim_id=claim.id, diagnosis_text=stage_data["utama"]["name"]
                ).first()
                if not diag:
                    diag = models.ClaimDiagnosis(
                        claim_id=claim.id,
                        diagnosis_type="utama",
                        diagnosis_text=stage_data["utama"]["name"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True,
                    )
                    db.add(diag)
                    db.flush()
                _update_diag_fields(diag, stage_data["utama"])

            for sec in stage_data.get("sekunder", []):
                diag = db.query(models.ClaimDiagnosis).filter_by(
                    claim_id=claim.id, diagnosis_text=sec["name"]
                ).first()
                if not diag:
                    diag = models.ClaimDiagnosis(
                        claim_id=claim.id,
                        diagnosis_type="sekunder",
                        diagnosis_text=sec["name"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True,
                    )
                    db.add(diag)
                    db.flush()
                _update_diag_fields(diag, sec)

            if "tindakanUtama" in stage_data and stage_data["tindakanUtama"]:
                _update_or_create_procedure(
                    db, claim, stage_data["tindakanUtama"], "utama"
                )
            for td in stage_data.get("tindakanSekunder", []):
                _update_or_create_procedure(db, claim, td, "sekunder")
        db.flush()
    except Exception as e:
        print("❌ Gagal update ClaimDiagnosis/ClaimProcedure:", e)

    if not summ_data or (
        "kombinasi_diagnosis" not in summ_data and
        "procedure" not in summ_data and
        "alternatif" not in summ_data
    ):
        old_diag = db.query(models.ClaimDiagnosisEvaluation).filter_by(claim_id=claim.id).first()
        print("🔎 Data ClaimDiagnosisEvaluation lama:", old_diag)
        old_proc = db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=claim.id).all()
        old_alt = db.query(models.ClaimCombinationAlternative).filter_by(claim_id=claim.id).all()
        print("🔎 Data ClaimCombinationAlternative lama:", old_alt)

        summ_data = {
            "kombinasi_diagnosis": {
                "validitas": old_diag.validitas if old_diag else None,
                "severity": old_diag.severity if old_diag else None,
                "validitas_detail": old_diag.validitas_detail if old_diag else None,
                "kode_ina_cbg": old_diag.kode_ina_cbg if old_diag else None,
                "estimasi_tarif": old_diag.estimasi_tarif if old_diag else None,
                "syarat_klinis": old_diag.syarat_klinis if old_diag else None,
                "evaluasi_faskes": old_diag.evaluasi_faskes if old_diag else None,
                "rawat_inap": old_diag.rawat_inap if old_diag else None,
            } if old_diag else {},
            "procedure": [
                {
                    "procedure_id": p.procedure_id,
                    "validitas": p.validitas,
                    "validitas_detail": p.validitas_detail,
                    "status_tindakan": p.status_tindakan,
                    "tarif_impact": p.tarif_impact,
                    "faskes": p.faskes,
                    "rawat_inap": p.rawat_inap,
                    "syarat_klinis": p.syarat_klinis,
                }
                for p in old_proc
            ],
            "alternatif": [
                {
                    "kombinasi": a.kombinasi_nama,   # pakai key 'kombinasi'
                    "severity": a.severity,
                    "kode_ina_cbg": a.kode_ina_cbg,
                    "tarif": a.estimasi_tarif,       # pakai key 'tarif'
                    "syarat_klinis": a.syarat_klinis,
                    "faskes": a.faskes,
                    "rawat_inap": a.rawat_inap,
                    "tindakan_wajib": a.tindakan_wajib,
                }
                for a in old_alt
            ],
        }

    print("📌 finalize_claim_service.summ_data.kombinasi_diagnosis:", summ_data.get("kombinasi_diagnosis"))
    print("📌 finalize_claim_service.summ_data.procedure:", summ_data.get("procedure"))
    print("📌 finalize_claim_service.summ_data.alternatif:", summ_data.get("alternatif"))

    # Save simulasi & summary
    save_simulation_and_summary(db, claim.id, sim_data, summ_data)

    # Update klaim
    claim.is_final = True
    claim.status = "final"
    claim.updated_at = datetime.utcnow()

    # Update rekam medis
    _update_medical_record_from_form(db, claim, user, form_data, action="FINALIZED")

    # Klaim log
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