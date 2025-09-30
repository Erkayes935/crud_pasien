"""
Module: backend.services.claim.simulation

Berisi fungsi untuk menyimpan & mengambil data simulasi klaim
(utama/sekunder) serta opsional summary evaluasi hasil core_engine.
"""

from sqlalchemy.orm import Session, joinedload
from typing import Dict, Any
from ... import models

# ==================================================
# LOAD SIMULASI + SUMMARY
# ==================================================

def load_sim_and_summary(db: Session, claim_id: int, include_summary: bool = True):
    """
    Ambil ulang simulasi + evaluasi dari tabel pecahan.

    Args:
        db (Session): DB session
        claim_id (int): ID klaim
        include_summary (bool): sertakan evaluasi (diagnosis, procedure, alternatif)
    """
    sim: dict = {}
    summ: dict = {}

    # === ClaimSimulation ===
    sims = db.query(models.ClaimSimulation).filter_by(claim_id=claim_id).all()
    for s in sims:
        if s.stage not in sim:
            sim[s.stage] = {
                "utama_diagnosis": None,
                "utama_tindakan": None,
                "sekunder_diagnosis": [],
                "sekunder_tindakan": []
            }
        if s.diagnosis_utama_id:
            sim[s.stage]["utama_diagnosis"] = {"id": s.diagnosis_utama_id, "type": "diagnosis"}
        if s.tindakan_utama_id:
            sim[s.stage]["utama_tindakan"] = {"id": s.tindakan_utama_id, "type": "tindakan"}
        if s.diagnosis_sekunder_id:
            sim[s.stage]["sekunder_diagnosis"].append({"id": s.diagnosis_sekunder_id, "type": "diagnosis"})
        if s.tindakan_sekunder_id:
            sim[s.stage]["sekunder_tindakan"].append({"id": s.tindakan_sekunder_id, "type": "tindakan"})

    # === Evaluasi (opsional, untuk verifikator/coder) ===
    if include_summary:
        summ["diagnosis"] = [
            {
                "validitas": d.validitas,
                "severity": d.severity,
                "kode_ina_cbg": d.kode_ina_cbg,
                "estimasi_tarif": float(d.estimasi_tarif) if d.estimasi_tarif else None,
                "syarat_klinis": d.syarat_klinis,
                "evaluasi_faskes": d.evaluasi_faskes,
                "rawat_inap": d.rawat_inap,
            }
            for d in db.query(models.ClaimDiagnosisEvaluation).filter_by(claim_id=claim_id).all()
        ]
        summ["procedure"] = [
            {
                "procedure_id": p.procedure_id,
                "validitas": p.validitas,
                "status_tindakan": p.status_tindakan,
                "tarif_impact": float(p.tarif_impact) if p.tarif_impact else None,
                "faskes": p.faskes,
                "rawat_inap": p.rawat_inap,
                "syarat_klinis": p.syarat_klinis,
            }
            for p in db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=claim_id).all()
        ]
        summ["alternatif"] = [
            {
                "kombinasi_nama": a.kombinasi_nama,
                "severity": a.severity,
                "kode_ina_cbg": a.kode_ina_cbg,
                "estimasi_tarif": float(a.estimasi_tarif) if a.estimasi_tarif else None,
                "syarat_klinis": a.syarat_klinis,
                "faskes": a.faskes,
                "rawat_inap": a.rawat_inap,
                "tindakan_wajib": a.tindakan_wajib,
                "notes": a.notes,
            }
            for a in db.query(models.ClaimCombinationAlternative).filter_by(claim_id=claim_id).all()
        ]

    return sim, summ


# ==================================================
# SAVE SIMULASI
# ==================================================

def save_simulasi(db: Session, claim_id: int, sim_data: Dict[str, Any]) -> None:
    """
    Simpan ulang simulasi ke tabel ClaimSimulation.

    Args:
        db (Session): DB session
        claim_id (int): ID klaim
        sim_data (dict): struktur dict { stage: { utama, sekunder } }
    """
    db.query(models.ClaimSimulation).filter(models.ClaimSimulation.claim_id == claim_id).delete()

    for stage, arr in (sim_data or {}).items():
        if not isinstance(arr, dict):
            continue

        if arr.get("utama"):
            utama_item = arr["utama"] if isinstance(arr["utama"], dict) else None
            if utama_item:
                db.add(models.ClaimSimulation(
                    claim_id=claim_id,
                    stage=stage,
                    type="utama",
                    diagnosis_id=utama_item.get("diagnosis_id"),
                    procedure_id=utama_item.get("procedure_id"),
                ))

        for sekunder_item in arr.get("sekunder", []):
            db.add(models.ClaimSimulation(
                claim_id=claim_id,
                stage=stage,
                type="sekunder",
                diagnosis_id=sekunder_item.get("diagnosis_id"),
                procedure_id=sekunder_item.get("procedure_id"),
            ))

    db.commit()


# ==================================================
# GET SIMULASI (SERVICE)
# ==================================================

def get_simulations_service(db: Session, claim_id: int):
    """
    Ambil simulasi beserta relasi diagnosis/procedure untuk klaim tertentu.

    Args:
        db (Session): DB session
        claim_id (int): ID klaim
    """
    sims = (
        db.query(models.ClaimSimulation)
        .options(
            joinedload(models.ClaimSimulation.diagnosis_utama),
            joinedload(models.ClaimSimulation.diagnosis_sekunder),
            joinedload(models.ClaimSimulation.tindakan_utama),
            joinedload(models.ClaimSimulation.tindakan_sekunder),
        )
        .filter_by(claim_id=claim_id)
        .all()
    )

    return {
        "status": "ok",
        "data": [
            {
                "stage": s.stage,
                "diagnosis_utama_id": s.diagnosis_utama_id,
                "diagnosis_utama_name": s.diagnosis_utama.diagnosis_text if s.diagnosis_utama else None,
                "diagnosis_sekunder_id": s.diagnosis_sekunder_id,
                "diagnosis_sekunder_name": s.diagnosis_sekunder.diagnosis_text if s.diagnosis_sekunder else None,
                "tindakan_utama_id": s.tindakan_utama_id,
                "tindakan_utama_name": s.tindakan_utama.procedure_text if s.tindakan_utama else None,
                "tindakan_sekunder_id": s.tindakan_sekunder_id,
                "tindakan_sekunder_name": s.tindakan_sekunder.procedure_text if s.tindakan_sekunder else None,
            }
            for s in sims
        ],
    }
