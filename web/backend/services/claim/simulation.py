"""
Module: backend.services.claim.simulation

Berisi fungsi untuk menyimpan & mengambil data simulasi klaim
(utama/sekunder) serta opsional summary evaluasi hasil core_engine.
"""

from sqlalchemy.orm import Session, joinedload
from typing import Dict, Any
from datetime import datetime
import json
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
    
    # Load AI recommendations first to build simulasi structure
    ai_recs = db.query(models.ClaimAIRecommendation).options(
        joinedload(models.ClaimAIRecommendation.diagnosis)
    ).filter_by(claim_id=claim_id, is_deleted=False).all()
    
    # Build simulasi structure from AI recommendations
    for rec in ai_recs:
        stage = rec.stage or "admission"
        category = rec.category or "diagnosis"
        
        if stage not in sim:
            sim[stage] = {}
        if category not in sim[stage]:
            sim[stage][category] = []
            
        # Build item data from diagnosis relationship
        item_data = {
            "id": rec.id,
            "name": rec.diagnosis.diagnosis_text if rec.diagnosis else "",
            "kategori": rec.diagnosis.diagnosis_text if rec.diagnosis else "",
            "nama_kategori": rec.diagnosis.diagnosis_text if rec.diagnosis else "",
            "mapping": rec.diagnosis.diagnosis_type if rec.diagnosis else "",
            "icd10_code": rec.diagnosis.icd10_code if rec.diagnosis else "",
            "klinis": rec.diagnosis.justifikasi if rec.diagnosis else "",
            "confidence": rec.confidence_score or 0,
            "score": rec.confidence_score or 0,
            "child": rec.child or False
        }
        sim[stage][category].append(item_data)

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
        # 🧠 Diagnosis Evaluation
        summ["diagnosis"] = [
            {
                "id": d.id,
                "validitas": d.validitas,
                "validitas_detail": d.validitas_detail,
                "severity": d.severity,
                "kode_ina_cbg": d.kode_ina_cbg,
                "estimasi_tarif": float(d.estimasi_tarif) if d.estimasi_tarif else None,
                "syarat_klinis": d.syarat_klinis,
                "evaluasi_faskes": d.evaluasi_faskes,
                "rawat_inap": d.rawat_inap,
            }
            for d in db.query(models.ClaimDiagnosisEvaluation)
                      .filter_by(claim_id=claim_id)
                      .all()
        ]

        # 💉 Procedure Evaluation (tanpa procedure_id karena model memang tidak punya)
        summ["procedure"] = [
            {
                "id": p.id,
                "validitas": p.validitas,
                "validitas_detail": p.validitas_detail,
                "status_tindakan": p.status_tindakan,
                "tarif_impact": float(p.tarif_impact) if p.tarif_impact else None,
                "faskes": p.faskes,
                "rawat_inap": p.rawat_inap,
                "syarat_klinis": p.syarat_klinis,
            }
            for p in db.query(models.ClaimProcedureEvaluation)
                      .filter_by(claim_id=claim_id)
                      .all()
        ]

        # 🧩 Kombinasi / Alternatif
        summ["alternatif"] = [
            {
                "id": a.id,
                "kombinasi_nama": a.kombinasi_nama,
                "severity": a.severity,
                "kode_ina_cbg": a.kode_ina_cbg,
                "estimasi_tarif": float(a.estimasi_tarif) if a.estimasi_tarif else None,
                "syarat_klinis": a.syarat_klinis,
                "faskes": a.faskes,
                "rawat_inap": a.rawat_inap,
                "tindakan_wajib": a.tindakan_wajib,
            }
            for a in db.query(models.ClaimCombinationAlternative)
                      .filter_by(claim_id=claim_id)
                      .all()
        ]

    # Wrap simulasi in expected format
    return {"simulasi": sim}, summ


# ==================================================
# SAVE SIMULASI
# ==================================================

def save_simulasi(db: Session, claim_id: int, sim_data: Dict[str, Any]) -> None:
    """
    Simpan ulang simulasi ke tabel ClaimSimulation dan juga simpan mapping individual items.

    Args:
        db (Session): DB session
        claim_id (int): ID klaim
        sim_data (dict): struktur dict { stage: { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] } }
    """
    print(f"[SAVE_SIMULASI] Saving simulasi for claim {claim_id}")
    print(f"[SAVE_SIMULASI] Data: {sim_data}")
    
    # Clear existing data
    db.query(models.ClaimSimulation).filter(models.ClaimSimulation.claim_id == claim_id).delete()
    
    # Clear existing AI recommendations to update with new mappings
    db.query(models.ClaimAIRecommendation).filter_by(claim_id=claim_id, is_deleted=False).update({"is_deleted": True})

    for stage, stage_data in (sim_data or {}).items():
        if not isinstance(stage_data, dict):
            continue
            
        print(f"[SAVE_SIMULASI] Processing stage: {stage}")

        # Save individual items with mappings
        for category in ["diagnosis", "komorbid", "komplikasi", "tindakan"]:
            items = stage_data.get(category, [])
            if not isinstance(items, list):
                continue
                
            print(f"[SAVE_SIMULASI] Processing {category}: {len(items)} items")
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                    
                mapping = item.get("mapping", "")
                print(f"[SAVE_SIMULASI] Item mapping: {mapping} for {item.get('name', 'unknown')}")
                
                # Store diagnosis with mapping information
                if category in ["diagnosis", "komorbid", "komplikasi"] and mapping:
                    # Store in ClaimDiagnosis with mapping as diagnosis_type
                    diag = models.ClaimDiagnosis(
                        claim_id=claim_id,
                        diagnosis_type=mapping,  # Use mapping as diagnosis_type (Primary, Secondary-Komorbid, etc.)
                        diagnosis_text=item.get("name") or item.get("kategori") or item.get("nama_kategori"),
                        icd10_code=item.get("icd10_code") or item.get("icd"),
                        justifikasi=item.get("klinis"),
                        is_deleted=False,
                        is_dummy=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(diag)
                    db.flush()  # Get ID
                    
                    # Create AI recommendation linked to diagnosis
                    rec = models.ClaimAIRecommendation(
                        claim_id=claim_id,
                        stage=stage,
                        category=category,
                        diagnosis_id=diag.id,
                        confidence_score=item.get("confidence") or item.get("score"),
                        child=item.get("child", False),
                        is_deleted=False,
                        is_dummy=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(rec)
                
                elif category == "tindakan" and mapping:
                    # For procedures, store mapping in a note or description field
                    # Since we don't have ClaimProcedure model with mapping, use existing structure
                    pass
                
                # Legacy ClaimSimulation records for backwards compatibility
                if mapping == "Primary" and category in ["diagnosis"]:
                    db.add(models.ClaimSimulation(
                        claim_id=claim_id,
                        stage=stage,
                        type="utama",
                        diagnosis_name=item.get("name") or item.get("kategori"),
                    ))
                elif mapping in ["Secondary-Komorbid", "Secondary-Komplikasi"] and category in ["diagnosis", "komorbid", "komplikasi"]:
                    db.add(models.ClaimSimulation(
                        claim_id=claim_id,
                        stage=stage,
                        type="sekunder", 
                        diagnosis_name=item.get("name") or item.get("kategori"),
                    ))

    db.commit()
    print(f"[SAVE_SIMULASI] Successfully saved simulasi for claim {claim_id}")


# ==================================================
# LOAD EXISTING MAPPINGS
# ==================================================

def load_existing_mappings(db: Session, claim_id: int) -> Dict[str, Any]:
    """
    Load existing AI recommendation mappings for a claim.
    
    Returns:
        dict: { stage: { category: [items_with_mappings] } }
    """
    # Get AI recommendations with related diagnoses
    recs = db.query(models.ClaimAIRecommendation).options(
        joinedload(models.ClaimAIRecommendation.diagnosis)
    ).filter_by(claim_id=claim_id, is_deleted=False).all()
    
    mappings = {}
    for rec in recs:
        stage = rec.stage or "admission"
        category = rec.category or "diagnosis"
        
        if stage not in mappings:
            mappings[stage] = {}
        if category not in mappings[stage]:
            mappings[stage][category] = []
            
        # Build item data from diagnosis relationship
        item_data = {
            "id": rec.id,
            "name": rec.diagnosis.diagnosis_text if rec.diagnosis else "",
            "kategori": rec.diagnosis.diagnosis_text if rec.diagnosis else "",
            "nama_kategori": rec.diagnosis.diagnosis_text if rec.diagnosis else "",
            "mapping": rec.diagnosis.diagnosis_type if rec.diagnosis else "",  # mapping stored as diagnosis_type
            "icd10_code": rec.diagnosis.icd10_code if rec.diagnosis else "",
            "klinis": rec.diagnosis.justifikasi if rec.diagnosis else "",
            "confidence": rec.confidence_score,
            "child": rec.child
        }
        mappings[stage][category].append(item_data)
    
    print(f"[LOAD_MAPPINGS] Loaded {len(recs)} mappings for claim {claim_id}")
    return mappings


def apply_mappings_to_simulasi(simulasi_data: Dict[str, Any], mappings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply saved mappings back to simulasi data structure.
    """
    print(f"[APPLY_MAPPINGS] Applying mappings to simulasi")
    
    for stage, stage_mappings in mappings.items():
        if stage not in simulasi_data:
            simulasi_data[stage] = {}
            
        for category, mapped_items in stage_mappings.items():
            if category not in simulasi_data[stage]:
                simulasi_data[stage][category] = []
                
            # Apply mappings to existing items
            for sim_item in simulasi_data[stage][category]:
                # Find matching mapped item by name/kategori
                item_name = sim_item.get("name") or sim_item.get("kategori") or sim_item.get("nama_kategori")
                for mapped_item in mapped_items:
                    mapped_name = mapped_item.get("name") or mapped_item.get("kategori") or mapped_item.get("nama_kategori")
                    if item_name and mapped_name and item_name == mapped_name:
                        sim_item["mapping"] = mapped_item.get("mapping", "")
                        print(f"[APPLY_MAPPINGS] Applied mapping '{mapped_item.get('mapping')}' to {item_name}")
                        break
    
    return simulasi_data


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
