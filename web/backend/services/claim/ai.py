"""
Module: backend.services.claim.ai

Berisi fungsi untuk menyimpan hasil AI & evaluasi klaim
dari core_engine ke database. Tidak ada dummy di sini,
semua data berasal dari core_engine.
"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any
from ... import models
from .helper import parse_number

# ==================================================
# AI RECOMMENDATIONS (hasil predict_ddx / analyze_diagnosis / analyze_procedure / regulation)
# ==================================================

def store_ai_recommendations(
    db: Session,
    claim_id: int,
    ai_data: Dict[str, Any],
    mode: str,
    stage: str = "admission"
) -> None:
    """
    Enhanced storage function for AI recommendations with validation and logging.
    
    Args:
        db: Database session
        claim_id: ID of the claim
        ai_data: AI response data to store
        mode: Type of AI result ("predict", "diagnosis", "procedure", "combos", "regulation")
        stage: Current stage ("admission", "daily", "discharge")
    """
    try:
        print(f"[AI STORAGE] Starting storage for claim {claim_id}, mode: {mode}, stage: {stage}")
        print(f"[AI STORAGE] Data received: {ai_data}")
        
        # Validate inputs
        if not claim_id:
            raise ValueError("claim_id is required")
        if not isinstance(ai_data, dict):
            raise ValueError("ai_data must be a dictionary")
        if mode not in ["predict", "diagnosis", "procedure", "combos", "regulation", "resume"]:
            raise ValueError(f"Invalid mode: {mode}")
            
        # Validate claim exists
        claim = db.query(models.Claim).filter_by(id=claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")

        if mode == "predict":
            # pastikan ClaimSimulation ada
            sim = db.query(models.ClaimSimulation).filter_by(
                claim_id=claim_id, stage=stage, is_deleted=False
            ).first()
            if not sim:
                sim = models.ClaimSimulation(
                    claim_id=claim_id,
                    stage=stage,
                    is_deleted=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(sim)
                db.flush()

            for category in ["diagnosis", "komorbid", "komplikasi"]:
                for item in ai_data.get(category, []):
                    # Store parent item
                    diag = models.ClaimDiagnosis(
                        claim_id=claim_id,
                        diagnosis_type=category,
                        diagnosis_text=item.get("kategori"),
                        confidence_score=item.get("score"),
                        is_deleted=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(diag)
                    db.flush()

                    rec = models.ClaimAIRecommendation(
                        claim_id=claim_id,
                        stage=stage,
                        category=category,
                        diagnosis_id=diag.id,
                        child=False,
                        confidence_score=item.get("score"),
                        is_deleted=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(rec)
                    
                    # Store children items
                    for child in item.get("children", []):
                        child_diag = models.ClaimDiagnosis(
                            claim_id=claim_id,
                            diagnosis_type=category,
                            diagnosis_text=child.get("kategori"),
                            confidence_score=child.get("score"),
                            is_deleted=False,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        db.add(child_diag)
                        db.flush()

                        child_rec = models.ClaimAIRecommendation(
                            claim_id=claim_id,
                            stage=stage,
                            category=category,
                            diagnosis_id=child_diag.id,
                            child=True,
                            confidence_score=child.get("score"),
                            is_deleted=False,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        db.add(child_rec)

        elif mode == "diagnosis":
            diag = models.ClaimDiagnosis(
                claim_id=claim_id,
                diagnosis_type="analysis",
                diagnosis_text=ai_data.get("diagnosis_text"),
                icd10_code=ai_data.get("icd10_code"),
                klinis=ai_data.get("justifikasi"),
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(diag)
            db.flush()

            rec = models.ClaimAIRecommendation(
                claim_id=claim_id,
                stage=stage,
                category="diagnosis",
                diagnosis_id=diag.id,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(rec)

        elif mode == "procedure":
            proc = models.ClaimProcedure(
                claim_id=claim_id,
                procedure_text=ai_data.get("procedure_text"),
                icd9_code=ai_data.get("icd9_code"),
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(proc)
            db.flush()

            rec = models.ClaimAIRecommendation(
                claim_id=claim_id,
                stage=stage,
                category="procedure",
                procedure_id=proc.id,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(rec)

        elif mode == "combos":
            # biasanya combos disimpan via store_ai_evaluations / bulk_store_ai_results_from_core
            for ev in ai_data.get("evaluasi_diagnosis", []):
                db.add(models.ClaimDiagnosisEvaluation(
                    claim_id=claim_id,
                    validitas=ev.get("valid"),
                    validitas_detail=ev.get("catatan"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                ))

            for ev in ai_data.get("evaluasi_procedure", []):
                db.add(models.ClaimProcedureEvaluation(
                    claim_id=claim_id,
                    validitas=ev.get("valid"),
                    validitas_detail=ev.get("catatan"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                ))

            for alt in ai_data.get("alternatif", []):
                db.add(models.ClaimCombinationAlternative(
                    claim_id=claim_id,
                    kombinasi_nama="; ".join(alt.get("kombinasi", [])),
                    notes=alt.get("catatan"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                ))

        elif mode == "regulation":
            # Extract data from regulation service response format
            regulation_data = ai_data
            if "data" in ai_data and isinstance(ai_data["data"], list) and len(ai_data["data"]) > 0:
                regulation_data = ai_data["data"][0]  # Get first regulation item
            
            # Convert isi list to JSON string if needed
            isi = regulation_data.get("isi", [])
            if isinstance(isi, list):
                isi = "\n".join(isi) if isi else ""
            
            reg = models.ClaimRegulationDetail(
                claim_id=claim_id,
                dasar_hukum=regulation_data.get("dasar_hukum", ""),
                judul_regulasi=regulation_data.get("judul_regulasi", ""),
                bab_pasal=regulation_data.get("bab_pasal", ""),
                isi=isi,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(reg)

        elif mode == "resume":
            # Store resume medis as a note in ClaimNote
            resume_text = ai_data.get("resume", "")
            if isinstance(ai_data, dict) and "data" in ai_data:
                resume_text = ai_data["data"].get("resume", "") if isinstance(ai_data["data"], dict) else str(ai_data["data"])
            
            # Clear existing resume notes
            db.query(models.ClaimNote).filter_by(
                claim_id=claim_id, 
                field_name="ai_medical_resume"
            ).delete()
            
            # Add new resume note
            note = models.ClaimNote(
                claim_id=claim_id,
                field_name="ai_medical_resume",
                note_text=resume_text,
                stage=stage,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(note)

        db.commit()
        print(f"[AI STORAGE] Successfully stored recommendations for {mode}")
    except Exception as e:
        print(f"[AI STORAGE] Error storing recommendations: {str(e)}")
        db.rollback()
        raise
    
# ==================================================
# AI EVALUATIONS (hasil generate_claim_combos / summary)
# ==================================================

def store_ai_evaluations(db: Session, claim_id: int, evaluasi: dict):
    """
    Simpan hasil evaluasi kombinasi ke tabel pecahan:
      - ClaimDiagnosisEvaluation
      - ClaimProcedureEvaluation
      - ClaimCombinationAlternative

    Args:
        db (Session): DB session
        claim_id (int): ID klaim
        evaluasi (dict): payload evaluasi dari core_engine
    """
    # 🔹 Hapus data lama biar tidak numpuk
    db.query(models.ClaimDiagnosisEvaluation).filter_by(claim_id=claim_id).delete()
    db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=claim_id).delete()
    db.query(models.ClaimCombinationAlternative).filter_by(claim_id=claim_id).delete()
    db.commit()

    def parse_validitas(raw: str):
        if not raw:
            return None
        raw_lower = raw.lower()
        if "invalid" in raw_lower:
            return "invalid"
        if "warning" in raw_lower or "medium" in raw_lower:
            return "warning"
        if "valid" in raw_lower:
            return "valid"
        return None

    # === Kombinasi Diagnosis ===
    diag = evaluasi.get("kombinasi_diagnosis", {})
    if diag:
        diag_eval = models.ClaimDiagnosisEvaluation(
            claim_id=claim_id,
            validitas=parse_validitas(diag.get("validitas")),
            validitas_detail=diag.get("validitas_detail"),
            severity=diag.get("severity"),
            kode_ina_cbg=diag.get("kode_ina_cbg"),
            estimasi_tarif=parse_number(diag.get("estimasi_tarif")),
            syarat_klinis=diag.get("syarat_klinis"),
            evaluasi_faskes=diag.get("evaluasi_faskes"),
            rawat_inap=diag.get("rawat_inap"),
            is_dummy=False,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(diag_eval)

    # === Kombinasi Tindakan ===
    for td in evaluasi.get("kombinasi_tindakan", []):
        proc_eval = models.ClaimProcedureEvaluation(
            claim_id=claim_id,
            validitas=parse_validitas(td.get("validitas")),
            validitas_detail=td.get("validitas_detail"),
            status_tindakan=td.get("status_tindakan"),
            tarif_impact=parse_number(td.get("tarif_impact")),
            faskes=td.get("faskes"),
            rawat_inap=td.get("rawat_inap"),
            syarat_klinis=td.get("syarat_klinis"),
            is_dummy=False,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(proc_eval)

    # === Alternatif Kombinasi ===
    for alt in evaluasi.get("alternatif", []):
        comb = models.ClaimCombinationAlternative(
            claim_id=claim_id,
            kombinasi_nama=alt.get("kombinasi_nama"),
            severity=alt.get("severity"),
            kode_ina_cbg=alt.get("kode_ina_cbg"),
            estimasi_tarif=parse_number(alt.get("estimasi_tarif")),
            syarat_klinis=alt.get("syarat_klinis"),
            faskes=alt.get("faskes"),
            rawat_inap=alt.get("rawat_inap"),
            tindakan_wajib=alt.get("tindakan_wajib"),
            notes=alt.get("notes"),
            is_dummy=False,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(comb)

    db.commit()

# ==================================================
# UTILITIES
# ==================================================

def clear_ai_results(db: Session, claim_id: int) -> None:
    """
    Clear all AI results for a specific claim before generating new ones.
    Includes validation and logging.
    """
    print(f"[AI STORAGE] Clearing AI results for claim {claim_id}")
    
    try:
        # Validate claim exists
        claim = db.query(models.Claim).filter_by(id=claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
            
        # Clear all related AI data
        print(f"[AI STORAGE] Removing AI recommendations and evaluations")
        db.query(models.ClaimCombinationAlternative).filter_by(claim_id=claim_id).delete()
        db.query(models.ClaimDiagnosisEvaluation).filter_by(claim_id=claim_id).delete()
        db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=claim_id).delete()
        db.commit()
        
    except Exception as e:
        print(f"[AI STORAGE] Error clearing AI results: {str(e)}")
        db.rollback()
        raise

def bulk_store_ai_results_from_core(db: Session, claim_id: int, result: dict) -> None:
    """
    Store results directly from core_engine with enhanced validation and logging.
    
    Args:
        db: Database session
        claim_id: ID of the claim 
        result: Core engine response containing alternatives, evaluations etc.
    """
    stored_items = {
        "alternatives": 0,
        "diagnosis_evaluations": 0,
        "procedure_evaluations": 0
    }
    
    try:
        print(f"[AI STORAGE] Starting bulk storage for claim {claim_id}")
        print(f"[AI STORAGE] Core engine result: {result}")
        
        if not isinstance(result, dict):
            raise ValueError("Result must be a dictionary")
            
        # Validate claim exists
        claim = db.query(models.Claim).filter_by(id=claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
            
        # Store alternatives
        for alt in result.get("alternatives", []):
            try:
                db.add(models.ClaimCombinationAlternative(
                    claim_id=claim_id,
                    kombinasi_nama=alt.get("kombinasi_nama"),
                    severity=alt.get("severity"),
                    kode_ina_cbg=alt.get("kode_ina_cbg"),
                    estimasi_tarif=parse_number(alt.get("estimasi_tarif")),
                    syarat_klinis=alt.get("syarat_klinis"),
                    faskes=alt.get("faskes"),
                    rawat_inap=alt.get("rawat_inap"),
                    tindakan_wajib=alt.get("tindakan_wajib"),
                    notes=alt.get("notes"),
                ))
                stored_items["alternatives"] += 1
            except Exception as e:
                print(f"[AI STORAGE] Error storing alternative: {str(e)}")

        # Store diagnosis evaluations
        for diag in result.get("diagnosis_evaluations", []):
            try:
                db.add(models.ClaimDiagnosisEvaluation(
                    claim_id=claim_id,
                    diagnosis_id=diag.get("diagnosis_id"),
                    validitas=diag.get("validitas"),
                    severity=diag.get("severity"),
                    kode_ina_cbg=diag.get("kode_ina_cbg"),
                    estimasi_tarif=parse_number(diag.get("estimasi_tarif")),
                    syarat_klinis=diag.get("syarat_klinis"),
                    evaluasi_faskes=diag.get("evaluasi_faskes"),
                    rawat_inap=diag.get("rawat_inap"),
                ))
                stored_items["diagnosis_evaluations"] += 1
            except Exception as e:
                print(f"[AI STORAGE] Error storing diagnosis evaluation: {str(e)}")

        # Store procedure evaluations
        for proc in result.get("procedure_evaluations", []):
            try:
                db.add(models.ClaimProcedureEvaluation(
                    claim_id=claim_id,
                    procedure_id=proc.get("procedure_id"),
                    validitas=proc.get("validitas"),
                    status_tindakan=proc.get("status_tindakan"),
                    tarif_impact=parse_number(proc.get("tarif_impact")),
                    faskes=proc.get("faskes"),
                    rawat_inap=proc.get("rawat_inap"),
                    syarat_klinis=proc.get("syarat_klinis"),
                ))
                stored_items["procedure_evaluations"] += 1
            except Exception as e:
                print(f"[AI STORAGE] Error storing procedure evaluation: {str(e)}")

        # Commit changes and log results
        db.commit()
        print(f"[AI STORAGE] Successfully stored AI results:")
        for key, count in stored_items.items():
            print(f"  - {key}: {count} items")
    except Exception as e:
        print(f"[AI STORAGE] Error in bulk storage: {str(e)}")
        db.rollback()
        raise

def get_regulation_details(db: Session, claim_id: int, context_type: str = None, item_id: int = None):
    """
    Ambil regulasi dari DB untuk klaim tertentu (opsional filter berdasarkan context).
    context_type: "diagnosis" | "procedure" | "combos"
    """
    query = db.query(models.ClaimRegulationDetail).filter_by(
        claim_id=claim_id,
        is_deleted=False
    )

    if context_type == "diagnosis" and item_id:
        query = query.filter(models.ClaimRegulationDetail.diagnosis_id == item_id)
    elif context_type == "procedure" and item_id:
        query = query.filter(models.ClaimRegulationDetail.procedure_id == item_id)
    elif context_type == "combos" and item_id:
        query = query.filter(models.ClaimRegulationDetail.diagnosis_evaluation_id == item_id)

    return query.all()
