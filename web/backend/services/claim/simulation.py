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
            "klinis": rec.diagnosis.justifikasi_klinis if rec.diagnosis else "",
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
                "diagnosis": [],
                "komorbid": [],
                "komplikasi": [],
                "utama": None,
                "sekunder": [],
                "tindakanUtama": None,
                "tindakanSekunder": [],
                "tarifDraft": None
            }
        if s.diagnosis_utama_id:
            sim[s.stage]["utama"] = {"id": s.diagnosis_utama_id, "type": "diagnosis"}
        if s.tindakan_utama_id:
            sim[s.stage]["tindakanUtama"] = {"id": s.tindakan_utama_id, "name": "tindakan"}
        if s.diagnosis_sekunder_id:
            if "sekunder" not in sim[s.stage]:
                sim[s.stage]["sekunder"] = []
            sim[s.stage]["sekunder"].append({"id": s.diagnosis_sekunder_id, "type": "diagnosis"})
        if s.tindakan_sekunder_id:
            if "tindakanSekunder" not in sim[s.stage]:
                sim[s.stage]["tindakanSekunder"] = []
            sim[s.stage]["tindakanSekunder"].append({"id": s.tindakan_sekunder_id, "name": "tindakan"})

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

def save_simulasi(db: Session, claim_id: int, sim_data: Dict[str, Any], form_data: Dict[str, Any] = None) -> None:
    """
    Simpan doctor mapping results ke ClaimSimulation table dengan proper foreign key relationships.
    
    ✅ Fixed: Sekarang simpan ke ClaimSimulation (bukan ClaimDiagnosis)
    ✅ Preserve: Workflow fields (coder_verified, is_coder_approved) yang sudah dibuat teammate
    ✅ Enhanced: Extract tindakan mapping dari form_data jika tidak ada di sim_data

    Args:
        db (Session): DB session
        claim_id (int): ID klaim
        sim_data (dict): struktur dict { stage: { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] } }
        form_data (dict, optional): full form data untuk extract tindakan mapping
    """
    print(f"[SAVE_SIMULASI] Saving doctor mapping to ClaimSimulation for claim {claim_id}")
    print(f"[SAVE_SIMULASI] Sim Data: {sim_data}")
    print(f"[SAVE_SIMULASI] Form Data keys: {list(form_data.keys()) if form_data else []}")
    
    # ✅ Clear ALL existing data untuk claim ini (avoid data menumpuk)
    print(f"[SAVE_SIMULASI] Clearing existing data for claim {claim_id}...")
    
    # Clear ClaimSimulation records
    deleted_sims = db.query(models.ClaimSimulation).filter(models.ClaimSimulation.claim_id == claim_id).delete()
    
    # Clear related ClaimDiagnosis records (dari mapping sebelumnya)
    deleted_diags = db.query(models.ClaimDiagnosis).filter(
        models.ClaimDiagnosis.claim_id == claim_id,
        models.ClaimDiagnosis.diagnosis_type.in_(["Diagnosis Utama", "Komorbid", "Komplikasi", "Primary", "Secondary"])
    ).delete(synchronize_session=False)
    
    # Clear related ClaimProcedure records (dari mapping sebelumnya) 
    deleted_procs = db.query(models.ClaimProcedure).filter(
        models.ClaimProcedure.claim_id == claim_id,
        models.ClaimProcedure.procedure_source.in_(["Primary", "Secondary", "Primary Action", "Secondary Actions"])
    ).delete(synchronize_session=False)
    
    print(f"[SAVE_SIMULASI] ✅ Cleared: {deleted_sims} simulations, {deleted_diags} diagnoses, {deleted_procs} procedures")

    for stage, stage_data in (sim_data or {}).items():
        if not isinstance(stage_data, dict):
            continue
            
        print(f"[SAVE_SIMULASI] Processing stage: {stage}")
        
        # Collect mappings by type for this stage
        primary_diagnosis = None
        secondary_diagnoses = []
        primary_procedure = None
        secondary_procedures = []
        
        # Process all diagnosis categories
        for category in ["diagnosis", "komorbid", "komplikasi"]:
            items = stage_data.get(category, [])
            if not isinstance(items, list):
                continue
                
            print(f"[SAVE_SIMULASI] Processing {category}: {len(items)} items")
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                    
                mapping = item.get("mapping", "")
                print(f"[SAVE_SIMULASI] Item mapping: {mapping} for {item.get('name', 'unknown')}")
                
                if mapping:
                    # Create/find ClaimDiagnosis record first
                    diag = models.ClaimDiagnosis(
                        claim_id=claim_id,
                        diagnosis_type=mapping,
                        diagnosis_text=item.get("name") or item.get("kategori") or item.get("nama_kategori"),
                        icd10_code=item.get("icd10_code") or item.get("icd"),
                        justifikasi_klinis=item.get("klinis"),
                        is_deleted=False,
                        is_dummy=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(diag)
                    db.flush()  # Get ID
                    
                    # Categorize by mapping type for ClaimSimulation
                    # ✅ Handle both old format ("Primary"/"Secondary") and new format ("Diagnosis Utama"/"Komorbid"/"Komplikasi")
                    if mapping in ["Primary", "Diagnosis Utama"]:
                        primary_diagnosis = diag.id
                        print(f"[SAVE_SIMULASI] ✅ Set primary diagnosis: {item.get('kategori')} (ID: {diag.id})")
                    elif mapping in ["Secondary", "Komorbid", "Komplikasi"] or mapping.startswith("Secondary"):
                        secondary_diagnoses.append(diag.id)
                        print(f"[SAVE_SIMULASI] ✅ Added secondary diagnosis: {item.get('kategori')} (ID: {diag.id})")
        
        # Process tindakan category from sim_data
        tindakan_items = stage_data.get("tindakan", [])
        if isinstance(tindakan_items, list):
            print(f"[SAVE_SIMULASI] Processing tindakan from sim_data: {len(tindakan_items)} items")
            
            for item in tindakan_items:
                if not isinstance(item, dict):
                    continue
                    
                mapping = item.get("mapping", "")
                print(f"[SAVE_SIMULASI] Procedure mapping: {mapping} for {item.get('name', 'unknown')}")
                
                if mapping:
                    # Create ClaimProcedure record
                    proc = models.ClaimProcedure(
                        claim_id=claim_id,
                        procedure_source=mapping,
                        procedure_text=item.get("name") or item.get("kategori") or item.get("nama_kategori"),
                        requirement_flag=False,  # ✅ Fix: Set required field
                        is_deleted=False,
                        is_dummy=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(proc)
                    db.flush()  # Get ID
                    
                    # Add procedure details if available
                    if item.get("icd9_code") or item.get("icd"):
                        proc_detail = models.ClaimProcedureDetail(
                            procedure_id=proc.id,
                            icd9_tindakan=item.get("icd9_code") or item.get("icd"),
                            nama_tindakan=item.get("name") or item.get("kategori"),
                            is_deleted=False,
                            created_at=datetime.utcnow()
                        )
                        db.add(proc_detail)
                    
                    # Categorize by mapping type
                    # ✅ Handle both old format ("Primary"/"Secondary") and new format ("Primary Action"/"Secondary Actions")
                    if mapping in ["Primary", "Primary Action", "Tindakan Utama"]:
                        primary_procedure = proc.id
                        print(f"[SAVE_SIMULASI] ✅ Set primary procedure: {item.get('name')} (ID: {proc.id})")
                    elif mapping in ["Secondary", "Secondary Action", "Secondary Actions", "Tindakan Sekunder"] or mapping.startswith("Secondary"):
                        secondary_procedures.append(proc.id)
                        print(f"[SAVE_SIMULASI] ✅ Added secondary procedure: {item.get('name')} (ID: {proc.id})")
        
        # ✅ ENHANCED: Extract procedures from BOTH sim_data AND stage_data structure  
        # Check for tindakanUtama & tindakanSekunder in stage_data directly
        if stage_data and isinstance(stage_data, dict):
            # Extract tindakanUtama
            tindakan_utama = stage_data.get("tindakanUtama")
            if tindakan_utama and isinstance(tindakan_utama, dict):
                tindakan_name = tindakan_utama.get("name", "")
                if tindakan_name and tindakan_name.strip() and not primary_procedure:
                    proc = models.ClaimProcedure(
                        claim_id=claim_id,
                        procedure_source="Primary",
                        procedure_text=tindakan_name,
                        requirement_flag=False,
                        is_deleted=False,
                        is_dummy=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(proc)
                    db.flush()
                    primary_procedure = proc.id
                    print(f"[SAVE_SIMULASI] ✅ Created PRIMARY procedure from stage_data: {tindakan_name} (ID: {proc.id})")
            
            # Extract tindakanSekunder (array)
            tindakan_sekunder = stage_data.get("tindakanSekunder", [])
            if isinstance(tindakan_sekunder, list):
                for sekunder_item in tindakan_sekunder:
                    if isinstance(sekunder_item, dict):
                        tindakan_name = sekunder_item.get("name", "")
                        if tindakan_name and tindakan_name.strip():
                            proc = models.ClaimProcedure(
                                claim_id=claim_id,
                                procedure_source="Secondary",
                                procedure_text=tindakan_name,
                                requirement_flag=False,
                                is_deleted=False,
                                is_dummy=False,
                                created_at=datetime.utcnow(),
                                updated_at=datetime.utcnow()
                            )
                            db.add(proc)
                            db.flush()
                            secondary_procedures.append(proc.id)
                            print(f"[SAVE_SIMULASI] ✅ Created SECONDARY procedure from stage_data: {tindakan_name} (ID: {proc.id})")
        
        # ✅ FALLBACK: Extract from form_data if still empty
        if not primary_procedure and not secondary_procedures and form_data and stage == "admission":
            print(f"[SAVE_SIMULASI] No procedures found in stage_data, extracting from form_data...")
            
            # Extract from payload simulasi yang lebih lengkap
            simulasi_raw = form_data.get("simulasi", "")
            if isinstance(simulasi_raw, str):
                try:
                    import json
                    simulasi_parsed = json.loads(simulasi_raw)
                    
                    # Look for tindakan in parsed simulasi
                    for stage_key, stage_val in simulasi_parsed.items():
                        if stage_key == stage and isinstance(stage_val, dict):
                            # Check for tindakanUtama
                            if "tindakanUtama" in stage_val and isinstance(stage_val["tindakanUtama"], dict):
                                tindakan_utama_name = stage_val["tindakanUtama"].get("name", "")
                                if tindakan_utama_name and tindakan_utama_name.strip() and not primary_procedure:
                                    proc = models.ClaimProcedure(
                                        claim_id=claim_id,
                                        procedure_source="Primary",
                                        procedure_text=tindakan_utama_name,
                                        requirement_flag=False,
                                        is_deleted=False,
                                        is_dummy=False,
                                        created_at=datetime.utcnow(),
                                        updated_at=datetime.utcnow()
                                    )
                                    db.add(proc)
                                    db.flush()
                                    primary_procedure = proc.id
                                    print(f"[SAVE_SIMULASI] ✅ Created primary procedure from form_data: {tindakan_utama_name}")
                            
                            # Check for tindakanSekunder (array)
                            if "tindakanSekunder" in stage_val and isinstance(stage_val["tindakanSekunder"], list):
                                for sekunder_item in stage_val["tindakanSekunder"]:
                                    if isinstance(sekunder_item, dict):
                                        tindakan_name = sekunder_item.get("name", "")
                                        if tindakan_name and tindakan_name.strip():
                                            proc = models.ClaimProcedure(
                                                claim_id=claim_id,
                                                procedure_source="Secondary",
                                                procedure_text=tindakan_name,
                                                requirement_flag=False,
                                                is_deleted=False,
                                                is_dummy=False,
                                                created_at=datetime.utcnow(),
                                                updated_at=datetime.utcnow()
                                            )
                                            db.add(proc)
                                            db.flush()
                                            secondary_procedures.append(proc.id)
                                            print(f"[SAVE_SIMULASI] ✅ Created secondary procedure from form_data: {tindakan_name}")
                            
                            break
                            
                except Exception as e:
                    print(f"[SAVE_SIMULASI] Error parsing simulasi from form_data: {e}")
        
        # Log final procedure counts
        print(f"[SAVE_SIMULASI] Final procedures for stage {stage}: primary={primary_procedure}, secondary_count={len(secondary_procedures)}")
        
        # ✅ CREATE MULTIPLE ClaimSimulation RECORDS untuk support multiple secondary procedures
        
        # Strategy: Create base record with primary mappings, then additional records for extra secondaries
        
        # Record 1: Main record with primary + first secondary
        main_simulation = models.ClaimSimulation(
            claim_id=claim_id,
            stage=stage,
            diagnosis_utama_id=primary_diagnosis,
            diagnosis_sekunder_id=secondary_diagnoses[0] if secondary_diagnoses else None,
            tindakan_utama_id=primary_procedure,
            tindakan_sekunder_id=secondary_procedures[0] if secondary_procedures else None,
            is_deleted=False,
            is_dummy=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            # ✅ PRESERVE teammate's workflow fields dengan default values
            coder_verified=False,
            is_coder_approved=False,
            coder_verified_by=None,
            coder_verified_at=None,
            coder_notes=None,
            verified_icd10=None,
            verified_icd10_name=None,
            verified_icd9=None,
            verified_icd9_name=None
        )
        db.add(main_simulation)
        print(f"[SAVE_SIMULASI] ✅ Created MAIN ClaimSimulation for stage {stage}: primary_diag={primary_diagnosis}, secondary_diag={secondary_diagnoses}, primary_proc={primary_procedure}, first_secondary_proc={secondary_procedures[0] if secondary_procedures else None}")
        
        # Records 2+: Additional records for extra secondary procedures
        if len(secondary_procedures) > 1:
            for i, extra_proc_id in enumerate(secondary_procedures[1:], 1):
                extra_simulation = models.ClaimSimulation(
                    claim_id=claim_id,
                    stage=stage,
                    diagnosis_utama_id=None,  # Only in main record
                    diagnosis_sekunder_id=secondary_diagnoses[i] if i < len(secondary_diagnoses) else None,
                    tindakan_utama_id=None,   # Only in main record
                    tindakan_sekunder_id=extra_proc_id,
                    is_deleted=False,
                    is_dummy=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    # Inherit workflow status from main record
                    coder_verified=False,
                    is_coder_approved=False,
                    coder_verified_by=None,
                    coder_verified_at=None,
                    coder_notes=None,
                    verified_icd10=None,
                    verified_icd10_name=None,
                    verified_icd9=None,
                    verified_icd9_name=None
                )
                db.add(extra_simulation)
                print(f"[SAVE_SIMULASI] ✅ Created EXTRA ClaimSimulation #{i+1} for stage {stage}: extra_secondary_proc={extra_proc_id}")
        
        # Additional records for extra secondary diagnoses (if more than procedures)
        if len(secondary_diagnoses) > len(secondary_procedures):
            for i, extra_diag_id in enumerate(secondary_diagnoses[len(secondary_procedures):], len(secondary_procedures)):
                extra_simulation = models.ClaimSimulation(
                    claim_id=claim_id,
                    stage=stage,
                    diagnosis_utama_id=None,
                    diagnosis_sekunder_id=extra_diag_id,
                    tindakan_utama_id=None,
                    tindakan_sekunder_id=None,
                    is_deleted=False,
                    is_dummy=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    coder_verified=False,
                    is_coder_approved=False,
                    coder_verified_by=None,
                    coder_verified_at=None,
                    coder_notes=None,
                    verified_icd10=None,
                    verified_icd10_name=None,
                    verified_icd9=None,
                    verified_icd9_name=None
                )
                db.add(extra_simulation)
                print(f"[SAVE_SIMULASI] ✅ Created EXTRA ClaimSimulation for extra diagnosis: secondary_diag={extra_diag_id}")
        
        total_records = 1 + max(0, len(secondary_procedures) - 1) + max(0, len(secondary_diagnoses) - len(secondary_procedures))
        print(f"[SAVE_SIMULASI] ✅ Created {total_records} ClaimSimulation records for stage {stage} (1 main + {total_records-1} extra)")

    db.commit()
    print(f"[SAVE_SIMULASI] ✅ Successfully saved doctor mapping to ClaimSimulation for claim {claim_id}")


# ==================================================
# LOAD EXISTING MAPPINGS
# ==================================================

def load_existing_mappings(db: Session, claim_id: int) -> Dict[str, Any]:
    """
    Load existing doctor mappings from ClaimSimulation table.
    
    ✅ Enhanced: Support multiple secondary procedures/diagnoses from multiple records
    ✅ Proper mapping format for frontend consumption
    
    Returns:
        dict: { stage: { category: [items_with_mappings] } }
    """
    print(f"[LOAD_MAPPINGS] Loading existing mappings for claim {claim_id}")
    
    # Query ClaimSimulation dengan related diagnosis/procedures
    sims = (
        db.query(models.ClaimSimulation)
        .options(
            joinedload(models.ClaimSimulation.diagnosis_utama),
            joinedload(models.ClaimSimulation.diagnosis_sekunder),
            joinedload(models.ClaimSimulation.tindakan_utama),
            joinedload(models.ClaimSimulation.tindakan_sekunder),
        )
        .filter(
            models.ClaimSimulation.claim_id == claim_id,
            models.ClaimSimulation.is_deleted == False
        )
        .order_by(models.ClaimSimulation.stage.asc(), models.ClaimSimulation.id.asc())
        .all()
    )
    
    if not sims:
        print(f"[LOAD_MAPPINGS] No existing mappings found for claim {claim_id}")
        return {}
    
    mappings = {}
    
    # Track unique items to avoid duplicates
    seen_items = {
        "diagnosis": set(),
        "komorbid": set(), 
        "komplikasi": set(),
        "tindakan": set()
    }
    
    for sim in sims:
        stage = sim.stage
        if stage not in mappings:
            mappings[stage] = {
                "diagnosis": [],
                "komorbid": [],
                "komplikasi": [],
                "tindakan": []
            }
        
        # ✅ Primary Diagnosis (only from main records)
        if sim.diagnosis_utama_id and sim.diagnosis_utama:
            diag = sim.diagnosis_utama
            if diag.id not in seen_items["diagnosis"]:
                seen_items["diagnosis"].add(diag.id)
                item_data = {
                    "id": f"existing-diag-{diag.id}",
                    "name": diag.diagnosis_text,
                    "kategori": diag.diagnosis_text,
                    "nama_kategori": diag.diagnosis_text,
                    "mapping": "Diagnosis Utama",  # Use frontend format
                    "icd10_code": diag.icd10_code or "",
                    "klinis": diag.justifikasi_klinis or "",
                    "confidence": 1.0,
                    "child": False,
                    "stage": stage,
                    "category": "diagnosis",
                    "existing": True  # Mark as existing data
                }
                mappings[stage]["diagnosis"].append(item_data)
                print(f"[LOAD_MAPPINGS] ✅ Added primary diagnosis: {diag.diagnosis_text}")
        
        # ✅ Secondary Diagnosis (dapat dari semua records)
        if sim.diagnosis_sekunder_id and sim.diagnosis_sekunder:
            diag = sim.diagnosis_sekunder
            if diag.id not in seen_items["diagnosis"] and diag.id not in seen_items["komorbid"] and diag.id not in seen_items["komplikasi"]:
                # Tentukan category berdasarkan diagnosis_type
                category = "diagnosis"
                mapping_type = diag.diagnosis_type or "Secondary"
                
                if "Komorbid" in mapping_type:
                    category = "komorbid"
                    seen_items["komorbid"].add(diag.id)
                elif "Komplikasi" in mapping_type:
                    category = "komplikasi"
                    seen_items["komplikasi"].add(diag.id)
                else:
                    category = "diagnosis"
                    seen_items["diagnosis"].add(diag.id)
                
                item_data = {
                    "id": f"existing-diag-{diag.id}",
                    "name": diag.diagnosis_text,
                    "kategori": diag.diagnosis_text,
                    "nama_kategori": diag.diagnosis_text,
                    "mapping": mapping_type,  # Keep original mapping type
                    "icd10_code": diag.icd10_code or "",
                    "klinis": diag.justifikasi_klinis or "",
                    "confidence": 0.9,
                    "child": False,
                    "stage": stage,
                    "category": category,
                    "existing": True
                }
                mappings[stage][category].append(item_data)
                print(f"[LOAD_MAPPINGS] ✅ Added secondary diagnosis: {diag.diagnosis_text} (category: {category})")
        
        # ✅ Primary Procedure (only from main records) 
        if sim.tindakan_utama_id and sim.tindakan_utama:
            proc = sim.tindakan_utama
            if proc.id not in seen_items["tindakan"]:
                seen_items["tindakan"].add(proc.id)
                # Get ICD-9 from procedure details
                icd9_code = ""
                if hasattr(proc, 'procedure_details') and proc.procedure_details:
                    icd9_code = proc.procedure_details[0].icd9_tindakan or ""
                
                item_data = {
                    "id": f"existing-proc-{proc.id}",
                    "name": proc.procedure_text,
                    "kategori": proc.procedure_text,
                    "nama_kategori": proc.procedure_text,
                    "mapping": "Primary Action",  # Use frontend format
                    "icd9_code": icd9_code,
                    "klinis": "",
                    "confidence": 1.0,
                    "child": False,
                    "stage": stage,
                    "category": "tindakan",
                    "existing": True
                }
                mappings[stage]["tindakan"].append(item_data)
                print(f"[LOAD_MAPPINGS] ✅ Added primary procedure: {proc.procedure_text}")
        
        # ✅ Secondary Procedures (dari semua records - INI YANG PENTING!)
        if sim.tindakan_sekunder_id and sim.tindakan_sekunder:
            proc = sim.tindakan_sekunder
            if proc.id not in seen_items["tindakan"]:
                seen_items["tindakan"].add(proc.id)
                # Get ICD-9 from procedure details
                icd9_code = ""
                if hasattr(proc, 'procedure_details') and proc.procedure_details:
                    icd9_code = proc.procedure_details[0].icd9_tindakan or ""
                
                item_data = {
                    "id": f"existing-proc-{proc.id}",
                    "name": proc.procedure_text,
                    "kategori": proc.procedure_text,
                    "nama_kategori": proc.procedure_text,
                    "mapping": "Secondary Actions",  # Use frontend format
                    "icd9_code": icd9_code,
                    "klinis": "",
                    "confidence": 0.9,
                    "child": False,
                    "stage": stage,
                    "category": "tindakan", 
                    "existing": True
                }
                mappings[stage]["tindakan"].append(item_data)
                print(f"[LOAD_MAPPINGS] ✅ Added secondary procedure: {proc.procedure_text}")
    
    total_items = sum(len(stage_data[cat]) for stage_data in mappings.values() for cat in stage_data)
    print(f"[LOAD_MAPPINGS] ✅ Loaded {total_items} existing mappings from {len(sims)} ClaimSimulation records for claim {claim_id}")
    print(f"[LOAD_MAPPINGS] Breakdown: {dict((stage, {cat: len(items) for cat, items in stage_data.items()}) for stage, stage_data in mappings.items())}")
    
    return mappings


def apply_mappings_to_simulasi(simulasi_data: Dict[str, Any], mappings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply saved mappings back to simulasi data structure.
    ✅ Enhanced: Properly populate frontend expected structure (utama, sekunder, tindakanUtama, tindakanSekunder)
    """
    print(f"[APPLY_MAPPINGS] Applying {len(mappings)} stage mappings to simulasi")
    
    for stage, stage_mappings in mappings.items():
        if stage not in simulasi_data:
            simulasi_data[stage] = {
                "diagnosis": [],
                "komorbid": [], 
                "komplikasi": [],
                "tindakan": [],
                "utama": None,
                "sekunder": [],
                "tindakanUtama": None,
                "tindakanSekunder": []
            }
            
        # Ensure all expected keys exist
        for key in ["diagnosis", "komorbid", "komplikasi", "tindakan", "utama", "sekunder", "tindakanUtama", "tindakanSekunder"]:
            if key not in simulasi_data[stage]:
                if key in ["sekunder", "tindakanSekunder"]:
                    simulasi_data[stage][key] = []
                else:
                    simulasi_data[stage][key] = None if key in ["utama", "tindakanUtama"] else []
        
        # Process each category
        for category, mapped_items in stage_mappings.items():
            if not isinstance(mapped_items, list):
                continue
                
            # Populate category arrays
            if category not in simulasi_data[stage]:
                simulasi_data[stage][category] = []
            
            # Add mapped items to category (merge with existing)
            for mapped_item in mapped_items:
                # Check if already exists to avoid duplicates
                existing_names = [item.get("name") or item.get("kategori") for item in simulasi_data[stage][category]]
                mapped_name = mapped_item.get("name") or mapped_item.get("kategori")
                
                if mapped_name not in existing_names:
                    simulasi_data[stage][category].append(mapped_item)
                    print(f"[APPLY_MAPPINGS] ✅ Added to {category}: {mapped_name}")
                
                # ✅ POPULATE FRONTEND EXPECTED STRUCTURE
                mapping_type = mapped_item.get("mapping", "")
                
                # Primary Diagnosis → utama
                if mapping_type in ["Diagnosis Utama", "Primary"] and category == "diagnosis":
                    simulasi_data[stage]["utama"] = {
                        "diagnosis_utama_id": mapped_item.get("id"),
                        "name": mapped_name,
                        "kategori": mapped_name,
                        "mapping": mapping_type,
                        "label": "Utama Klinis",
                        **mapped_item
                    }
                    print(f"[APPLY_MAPPINGS] ✅ Set utama: {mapped_name}")
                
                # Secondary Diagnoses → sekunder array
                elif mapping_type in ["Komorbid", "Komplikasi", "Secondary"] and category in ["komorbid", "komplikasi"]:
                    # Check for duplicates in sekunder array
                    existing_sekunder_names = [item.get("name") for item in simulasi_data[stage]["sekunder"]]
                    if mapped_name not in existing_sekunder_names:
                        simulasi_data[stage]["sekunder"].append({
                            "diagnosis_sekunder_id": mapped_item.get("id"),
                            "name": mapped_name,
                            "kategori": mapped_name,
                            "mapping": mapping_type,
                            "label": "Komorbid" if mapping_type == "Komorbid" else "Komplikasi",
                            **mapped_item
                        })
                        print(f"[APPLY_MAPPINGS] ✅ Added to sekunder: {mapped_name}")
                
                # Primary Procedure → tindakanUtama
                elif mapping_type in ["Primary", "Primary Action"] and category == "tindakan":
                    simulasi_data[stage]["tindakanUtama"] = {
                        "tindakan_utama_id": mapped_item.get("id"),
                        "name": mapped_name,
                        **mapped_item
                    }
                    print(f"[APPLY_MAPPINGS] ✅ Set tindakanUtama: {mapped_name}")
                
                # Secondary Procedures → tindakanSekunder array
                elif mapping_type in ["Secondary", "Secondary Actions"] and category == "tindakan":
                    # Check for duplicates in tindakanSekunder array  
                    existing_sekunder_proc_names = [item.get("name") for item in simulasi_data[stage]["tindakanSekunder"]]
                    if mapped_name not in existing_sekunder_proc_names:
                        simulasi_data[stage]["tindakanSekunder"].append({
                            "tindakan_sekunder_id": mapped_item.get("id"),
                            "name": mapped_name,
                            **mapped_item
                        })
                        print(f"[APPLY_MAPPINGS] ✅ Added to tindakanSekunder: {mapped_name}")
    
    # Log final structure for debugging
    for stage, stage_data in simulasi_data.items():
        if isinstance(stage_data, dict):
            print(f"[APPLY_MAPPINGS] Final {stage}: utama={bool(stage_data.get('utama'))}, sekunder={len(stage_data.get('sekunder', []))}, tindakanUtama={bool(stage_data.get('tindakanUtama'))}, tindakanSekunder={len(stage_data.get('tindakanSekunder', []))}")
    
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

# ==================================================
# GET SIMULASI UNTUK CODER (HYBRID)
# ==================================================

def get_simulations_for_coder(db: Session, claim_id: int):
    """
    Ambil seluruh kombinasi diagnosis & tindakan dokter untuk diverifikasi coder.
    Return: { stage: { diagnosis: [...], procedure: [...] } }

    ⚙️ Hybrid version:
    - Tetap gunakan ClaimSimulation (jika tersedia)
    - Jika tidak ada data simulasi, fallback ke ClaimDiagnosis & ClaimProcedure
    """

    sims = (
        db.query(models.ClaimSimulation)
        .options(
            joinedload(models.ClaimSimulation.diagnosis_utama),
            joinedload(models.ClaimSimulation.diagnosis_sekunder),
            joinedload(models.ClaimSimulation.tindakan_utama),
            joinedload(models.ClaimSimulation.tindakan_sekunder),
        )
        .filter(
            models.ClaimSimulation.claim_id == claim_id,
            models.ClaimSimulation.is_deleted == False,
        )
        .order_by(models.ClaimSimulation.stage.asc(), models.ClaimSimulation.id.asc())
        .all()
    )

    stages: Dict[str, Any] = {}

    # =============== CASE 1: ADA DATA SIMULASI ===============
    if sims:
        for s in sims:
            if s.stage not in stages:
                stages[s.stage] = {"diagnosis": [], "procedure": []}

            # Diagnosis Utama
            if s.diagnosis_utama_id and s.diagnosis_utama:
                stages[s.stage]["diagnosis"].append({
                    "type": "Diagnosis Utama",
                    "text": s.diagnosis_utama.diagnosis_text,
                    "icd_doctor": s.diagnosis_utama.icd10_code,
                    "icd_final": s.coder_icd10_utama if hasattr(s, "coder_icd10_utama") else None,
                    "verified_by": s.coder_verified_by,
                    "verified_at": s.coder_verified_at,
                    "field": "primary_diagnosis",
                    "item_id": s.diagnosis_utama_id,
                })

            # Diagnosis Sekunder
            if s.diagnosis_sekunder_id and s.diagnosis_sekunder:
                stages[s.stage]["diagnosis"].append({
                    "type": "Diagnosis Sekunder",
                    "text": s.diagnosis_sekunder.diagnosis_text,
                    "icd_doctor": s.diagnosis_sekunder.icd10_code,
                    "icd_final": s.coder_icd10_sekunder if hasattr(s, "coder_icd10_sekunder") else None,
                    "verified_by": s.coder_verified_by,
                    "verified_at": s.coder_verified_at,
                    "field": "secondary_diagnosis",
                    "item_id": s.diagnosis_sekunder_id,
                })

            # Tindakan Utama
            if s.tindakan_utama_id and s.tindakan_utama:
                icd9_code = None
                if s.tindakan_utama.procedure_details:
                    icd9_code = s.tindakan_utama.procedure_details[0].icd9_tindakan
                stages[s.stage]["procedure"].append({
                    "type": "Tindakan Utama",
                    "text": s.tindakan_utama.procedure_text,
                    "icd_doctor": icd9_code,
                    "icd_final": s.coder_icd9_utama if hasattr(s, "coder_icd9_utama") else None,
                    "verified_by": s.coder_verified_by,
                    "verified_at": s.coder_verified_at,
                    "field": "primary_action",
                    "item_id": s.tindakan_utama_id,
                })

            # Tindakan Sekunder
            if s.tindakan_sekunder_id and s.tindakan_sekunder:
                icd9_code = None
                if s.tindakan_sekunder.procedure_details:
                    icd9_code = s.tindakan_sekunder.procedure_details[0].icd9_tindakan
                stages[s.stage]["procedure"].append({
                    "type": "Tindakan Sekunder",
                    "text": s.tindakan_sekunder.procedure_text,
                    "icd_doctor": icd9_code,
                    "icd_final": s.coder_icd9_sekunder if hasattr(s, "coder_icd9_sekunder") else None,
                    "verified_by": s.coder_verified_by,
                    "verified_at": s.coder_verified_at,
                    "field": "secondary_action",
                    "item_id": s.tindakan_sekunder_id,
                })

    # =============== CASE 2: FALLBACK (TIDAK ADA SIMULASI) ===============
    else:
        stages["admission"] = {"diagnosis": [], "procedure": []}

        # Diagnosis
        diags = db.query(models.ClaimDiagnosis).filter_by(claim_id=claim_id).all()
        for d in diags:
            stages["admission"]["diagnosis"].append({
                "type": d.diagnosis_type or "Diagnosis",
                "text": d.diagnosis_text,
                "icd_doctor": d.icd10_code,
                "icd_final": getattr(d, "icd10_final_by_coder", None),
                "verified_by": getattr(d, "verified_by", None),
                "verified_at": getattr(d, "verified_at", None),
                "item_id": d.id,
                "field": "diagnosis"
            })

        # Tindakan
        procs = db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).all()
        for p in procs:
            icd9_code = None
            if hasattr(p, "procedure_details") and p.procedure_details:
                icd9_code = p.procedure_details[0].icd9_tindakan
            stages["admission"]["procedure"].append({
                "type": "Tindakan",
                "text": p.procedure_text,
                "icd_doctor": icd9_code,
                "icd_final": getattr(p, "icd9_final_by_coder", None),
                "verified_by": getattr(p, "verified_by", None),
                "verified_at": getattr(p, "verified_at", None),
                "item_id": p.id,
                "field": "procedure"
            })

    print(f"[CODER_VIEW] Loaded {sum(len(v['diagnosis'])+len(v['procedure']) for v in stages.values())} items for coder review")
    return stages


# ==================================================
# GET SIMULASI UNTUK VERIFICATOR (APPROVED MAPPINGS)
# ==================================================

def get_simulations_for_verificator(db: Session, claim_id: int):
    """
    Ambil simulasi yang sudah di-approve coder untuk verificator.
    Return: formatted mapping data untuk auto-populate generate_claim_combos
    
    Returns:
        dict: {
            "primary_claim": "Pneumonia",
            "secondary_claims": ["Diabetes", "Hipertensi"], 
            "primary_action": "Bronkoskopi",
            "secondary_actions": ["Lab Test", "CT Scan"],
            "stages": { stage: { utama: {...}, sekunder: {...} } }
        }
    """
    
    # Query ClaimSimulation yang sudah verified & approved coder
    approved_sims = (
        db.query(models.ClaimSimulation)
        .options(
            joinedload(models.ClaimSimulation.diagnosis_utama),
            joinedload(models.ClaimSimulation.diagnosis_sekunder),
            joinedload(models.ClaimSimulation.tindakan_utama),
            joinedload(models.ClaimSimulation.tindakan_sekunder),
        )
        .filter(
            models.ClaimSimulation.claim_id == claim_id,
            models.ClaimSimulation.coder_verified == True,      # Sudah verified coder
            models.ClaimSimulation.is_coder_approved == True,   # Sudah approved coder
            models.ClaimSimulation.is_deleted == False,
        )
        .order_by(models.ClaimSimulation.stage.asc(), models.ClaimSimulation.id.asc())
        .all()
    )
    
    if not approved_sims:
        print(f"[VERIFICATOR] No approved simulations found for claim {claim_id}")
        return {
            "primary_claim": "",
            "secondary_claims": [],
            "primary_action": "",
            "secondary_actions": [],
            "stages": {},
            "message": "Belum ada mapping yang di-approve coder untuk claim ini"
        }
    
    # Collect unique mappings across all stages
    primary_claims = set()
    secondary_claims = set()
    primary_actions = set()
    secondary_actions = set()
    
    stages_data = {}
    
    for sim in approved_sims:
        stage = sim.stage
        if stage not in stages_data:
            stages_data[stage] = {
                "utama_diagnosis": None,
                "sekunder_diagnosis": [],
                "utama_tindakan": None,
                "sekunder_tindakan": []
            }
        
        # Primary Diagnosis
        if sim.diagnosis_utama_id and sim.diagnosis_utama:
            diag_text = sim.diagnosis_utama.diagnosis_text
            primary_claims.add(diag_text)
            stages_data[stage]["utama_diagnosis"] = {
                "id": sim.diagnosis_utama_id,
                "name": diag_text,
                "icd10_code": sim.diagnosis_utama.icd10_code,
                "verified_icd10": sim.verified_icd10,
                "verified_by": sim.coder_verified_by,
                "verified_at": sim.coder_verified_at.isoformat() if sim.coder_verified_at else None
            }
        
        # Secondary Diagnosis  
        if sim.diagnosis_sekunder_id and sim.diagnosis_sekunder:
            diag_text = sim.diagnosis_sekunder.diagnosis_text
            secondary_claims.add(diag_text)
            stages_data[stage]["sekunder_diagnosis"].append({
                "id": sim.diagnosis_sekunder_id,
                "name": diag_text,
                "icd10_code": sim.diagnosis_sekunder.icd10_code,
                "verified_icd10": sim.verified_icd10,
                "verified_by": sim.coder_verified_by,
                "verified_at": sim.coder_verified_at.isoformat() if sim.coder_verified_at else None
            })
        
        # Primary Action
        if sim.tindakan_utama_id and sim.tindakan_utama:
            proc_text = sim.tindakan_utama.procedure_text
            primary_actions.add(proc_text)
            # Get ICD-9 from procedure details
            icd9_code = None
            if sim.tindakan_utama.procedure_details:
                icd9_code = sim.tindakan_utama.procedure_details[0].icd9_tindakan
            
            stages_data[stage]["utama_tindakan"] = {
                "id": sim.tindakan_utama_id,
                "name": proc_text,
                "icd9_code": icd9_code,
                "verified_icd9": sim.verified_icd9,
                "verified_by": sim.coder_verified_by,
                "verified_at": sim.coder_verified_at.isoformat() if sim.coder_verified_at else None
            }
        
        # Secondary Action
        if sim.tindakan_sekunder_id and sim.tindakan_sekunder:
            proc_text = sim.tindakan_sekunder.procedure_text
            secondary_actions.add(proc_text)
            # Get ICD-9 from procedure details
            icd9_code = None
            if sim.tindakan_sekunder.procedure_details:
                icd9_code = sim.tindakan_sekunder.procedure_details[0].icd9_tindakan
                
            stages_data[stage]["sekunder_tindakan"].append({
                "id": sim.tindakan_sekunder_id,
                "name": proc_text,
                "icd9_code": icd9_code,
                "verified_icd9": sim.verified_icd9,
                "verified_by": sim.coder_verified_by,
                "verified_at": sim.coder_verified_at.isoformat() if sim.coder_verified_at else None
            })
    
    # Format output untuk generate_claim_combos endpoint
    result = {
        "primary_claim": list(primary_claims)[0] if primary_claims else "",
        "secondary_claims": list(secondary_claims),
        "primary_action": list(primary_actions)[0] if primary_actions else "",
        "secondary_actions": list(secondary_actions),
        "stages": stages_data,
        "total_approved": len(approved_sims),
        "message": f"Found {len(approved_sims)} approved simulations across {len(stages_data)} stages"
    }
    
    print(f"[VERIFICATOR] Loaded approved mappings: {result['message']}")
    return result


# ==================================================
# SAVE VERIFIKASI CODER
# ==================================================

def save_coder_verification(db: Session, claim_id: int, form_data: dict, coder_name: str):
    """
    Simpan hasil verifikasi ICD Final oleh coder.
    ✅ Mendukung:
        - Update ICD final di ClaimDiagnosis & ClaimProcedure (lama)
        - Update ClaimSimulation (baru)
        - Simpan catatan coder
        - Sinkronisasi tracking ke klaim
    """
    now = datetime.utcnow()
    updated = 0

    # ============================================================
    # 1️⃣ UPDATE DIAGNOSIS DAN TINDAKAN (VERSI LAMA)
    # ============================================================
    diags = db.query(models.ClaimDiagnosis).filter_by(claim_id=claim_id).all()
    for d in diags:
        icd_key = f"icd_final_diag_{d.id}"
        icd_final = form_data.get(icd_key)

        if icd_final and icd_final.strip():
            d.icd10_final_by_coder = icd_final.strip()
        else:
            d.icd10_final_by_coder = d.icd10_code

        d.verified_by = coder_name
        d.verified_at = now
        updated += 1

    procs = db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).all()
    for p in procs:
        icd_key = f"icd_final_proc_{p.id}"
        icd_final = form_data.get(icd_key)

        if icd_final and icd_final.strip():
            p.icd9_final_by_coder = icd_final.strip()
        else:
            if p.procedure_details and len(p.procedure_details) > 0:
                p.icd9_final_by_coder = p.procedure_details[0].icd9_tindakan
            else:
                p.icd9_final_by_coder = None

        p.verified_by = coder_name
        p.verified_at = now
        updated += 1

    # ============================================================
    # 2️⃣ UPDATE SIMULATION (VERSI BARU PER ITEM)
    # ============================================================
    for key, value in form_data.items():
        if not value:
            continue

        # ICD10
        if key.startswith("icd10_"):
            item_id = key.replace("icd10_", "")
            sim = (
                db.query(models.ClaimSimulation)
                .filter(models.ClaimSimulation.claim_id == claim_id,
                        models.ClaimSimulation.id == int(item_id))
                .first()
            )
            if sim:
                sim.verified_icd10 = value.strip()
                sim.coder_verified = True
                sim.coder_verified_by = coder_name
                sim.coder_verified_at = now
                sim.is_coder_approved = True

                # optional lookup ICD10 master (jika ada)
                if hasattr(models, "ICD10Master"):
                    master = db.query(models.ICD10Master).filter_by(code=value.strip()).first()
                    if master:
                        sim.verified_icd10_name = master.name
                updated += 1

        # ICD9
        elif key.startswith("icd9_"):
            item_id = key.replace("icd9_", "")
            sim = (
                db.query(models.ClaimSimulation)
                .filter(models.ClaimSimulation.claim_id == claim_id,
                        models.ClaimSimulation.id == int(item_id))
                .first()
            )
            if sim:
                sim.verified_icd9 = value.strip()
                sim.coder_verified = True
                sim.coder_verified_by = coder_name
                sim.coder_verified_at = now
                sim.is_coder_approved = True

                if hasattr(models, "ICD9Master"):
                    master = db.query(models.ICD9Master).filter_by(code=value.strip()).first()
                    if master:
                        sim.verified_icd9_name = master.name
                updated += 1

        # Catatan coder
        elif key.startswith("note_"):
            item_id = key.replace("note_", "")
            sim = (
                db.query(models.ClaimSimulation)
                .filter(models.ClaimSimulation.claim_id == claim_id,
                        models.ClaimSimulation.id == int(item_id))
                .first()
            )
            if sim:
                sim.coder_notes = value.strip()
                print(f"📝 Note saved for item {item_id}: {value[:40]}...")

    # ============================================================
    # 3️⃣ UPDATE STATUS CLAIM (workflow)
    # ============================================================
    claim = db.query(models.Claim).filter_by(id=claim_id).first()
    if claim:
        claim.workflow_status = "coder_verified"
        claim.coder_verified_by = coder_name
        claim.coder_verified_at = now

    db.commit()
    print(f"✅ save_coder_verification: {updated} items verified/updated by {coder_name}")
    return updated
