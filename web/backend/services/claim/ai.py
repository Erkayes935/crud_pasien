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
from backend.services.claim_helper import parse_number

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

        # ✅ Validation
        if not claim_id:
            raise ValueError("claim_id is required")
        if not isinstance(ai_data, dict):
            raise ValueError("ai_data must be a dictionary")
        if mode not in ["predict", "diagnosis", "procedure", "combos", "regulation"]:
            raise ValueError(f"Invalid mode: {mode}")

        # ✅ Validate claim exists
        claim = db.query(models.Claim).filter_by(id=claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")

        # ============================================================
        # MODE: PREDICT
        # ============================================================
        if mode == "predict":
            # cari simulasi
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

            # Soft-clearing old AI data    

            print(f"[AI STORAGE] Soft-clearing old AI data for claim {claim_id}")
            old_recs = db.query(models.ClaimAIRecommendation).filter_by(
                claim_id=claim_id, stage=stage, is_deleted=False
            ).all()
            for rec in old_recs:
                rec.is_deleted = True
                rec.updated_at = datetime.utcnow()

            old_diags = db.query(models.ClaimDiagnosis).filter_by(
                claim_id=claim_id, diagnosis_source="ai", is_deleted=False
            ).all()
            for diag in old_diags:
                diag.is_deleted = True
                diag.updated_at = datetime.utcnow()

            db.commit()

            # Simpan hasil baru
            for category in ["diagnosis", "komorbid", "komplikasi"]:
                for item in ai_data.get(category, []):
                    # --- parent diagnosis ---
                    diag = models.ClaimDiagnosis(
                        claim_id=claim_id,
                        diagnosis_type=category,
                        diagnosis_text=item.get("name") or item.get("kategori"),
                        diagnosis_source="ai",
                        is_deleted=False,
                        is_dummy=False,
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
                        confidence_score=item.get("score") or item.get("confidence_score") or 0,
                        child=False,
                        is_deleted=False,
                        is_dummy=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(rec)

                    # --- child diagnosis ---
                    for child in item.get("children", []):
                        child_diag = models.ClaimDiagnosis(
                            claim_id=claim_id,
                            diagnosis_type=category,
                            diagnosis_text=child.get("name") or child.get("kategori"),
                            diagnosis_source="ai",
                            is_deleted=False,
                            is_dummy=False,
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
                            confidence_score=child.get("score") or child.get("confidence_score") or 0,
                            child=True,
                            is_deleted=False,
                            is_dummy=False,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        db.add(child_rec)

            db.commit()

        # ============================================================
        # MODE: DIAGNOSIS
        # ============================================================
        elif mode == "diagnosis":
            # --- deteksi apakah ini child ---
            is_child = ai_data.get("child", False)
            category = ai_data.get("category", "diagnosis")
            diagnosis_text = ai_data.get("diagnosis_text") or ai_data.get("diagnosis") or "-"
            diagnosis_source = ai_data.get("diagnosis_source", "ai")

            # --- nested JSON dari payload core_engine ---
            klinis_data = ai_data.get("klinis", {})
            icd10_data = ai_data.get("icd10", {})
            rawat_data = ai_data.get("rawat_inap", {})
            faskes_data = ai_data.get("faskes", {})
            rujukan_data = ai_data.get("rujukan", {})
            ina_cbg_data = ai_data.get("inaCbg", {})

            # --- confidence ---
            confidence_str = klinis_data.get("confidence_ai", "0%").replace("%", "")
            confidence = int(confidence_str) if confidence_str.isdigit() else 0

            # --- field klinis utama ---
            justifikasi_klinis = klinis_data.get("justifikasi")
            bukti_klinis = klinis_data.get("bukti_klinis")
            syarat_klinis = klinis_data.get("syarat_klinis")
            klinis_value = " | ".join([p for p in [justifikasi_klinis, bukti_klinis, syarat_klinis] if p])

            # --- field tambahan ---
            icd10_code = (
                ai_data.get("icd10_code")
                or ai_data.get("kode_icd10")
                or icd10_data.get("kode_icd")
            )
            kode_ganda_icd10 = icd10_data.get("kode_ganda")
            z_code_icd10 = icd10_data.get("z_code")
            kode_bpjs_khusus_icd10 = icd10_data.get("kode_bpjs_khusus")

            lama_rawat_inap = rawat_data.get("lama_rawat")
            kriteria_rawat_inap = rawat_data.get("kriteria")
            indikasi_rawat_inap = rawat_data.get("indikasi")

            tingkat_faskes = faskes_data.get("tingkat")
            justifikasi_faskes = faskes_data.get("justifikasi")
            kompetensi_faskes = faskes_data.get("kompetensi")

            indikasi_rujukan = rujukan_data.get("indikasi")
            kriteria_rujukan = rujukan_data.get("kriteria")
            tujuan_rujukan = rujukan_data.get("tujuan")

            # --- cek apakah diagnosis sudah ada ---
            existing_diag = db.query(models.ClaimDiagnosis).filter_by(
                claim_id=claim_id,
                diagnosis_text=diagnosis_text,
                diagnosis_source="ai",
                is_deleted=False
            ).first()

            if existing_diag:
                print(f"[AI STORAGE] Updating existing diagnosis: {diagnosis_text}")
                existing_diag.icd10_code = icd10_code
                existing_diag.justifikasi_klinis = justifikasi_klinis
                existing_diag.bukti_klinis = bukti_klinis
                existing_diag.syarat_klinis = syarat_klinis
                existing_diag.klinis = klinis_value
                existing_diag.tingkat_faskes = tingkat_faskes
                existing_diag.justifikasi_faskes = justifikasi_faskes
                existing_diag.kompetensi_faskes = kompetensi_faskes
                existing_diag.kode_ganda_icd10 = kode_ganda_icd10
                existing_diag.z_code_icd10 = z_code_icd10
                existing_diag.kode_bpjs_khusus_icd10 = kode_bpjs_khusus_icd10
                existing_diag.lama_rawat_inap = lama_rawat_inap
                existing_diag.kriteria_rawat_inap = kriteria_rawat_inap
                existing_diag.indikasi_rawat_inap = indikasi_rawat_inap
                existing_diag.indikasi_rujukan = indikasi_rujukan
                existing_diag.kriteria_rujukan = kriteria_rujukan
                existing_diag.tujuan_rujukan = tujuan_rujukan
                existing_diag.updated_at = datetime.utcnow()
                diag = existing_diag
            else:
                print(f"[AI STORAGE] Inserting new diagnosis: {diagnosis_text}")
                diag = models.ClaimDiagnosis(
                    claim_id=claim_id,
                    diagnosis_type=category,
                    diagnosis_text=diagnosis_text,
                    diagnosis_source=diagnosis_source,
                    icd10_code=icd10_code,
                    justifikasi_klinis=justifikasi_klinis,
                    bukti_klinis=bukti_klinis,
                    syarat_klinis=syarat_klinis,
                    klinis=klinis_value,
                    tingkat_faskes=tingkat_faskes,
                    justifikasi_faskes=justifikasi_faskes,
                    kompetensi_faskes=kompetensi_faskes,
                    kode_ganda_icd10=kode_ganda_icd10,
                    z_code_icd10=z_code_icd10,
                    kode_bpjs_khusus_icd10=kode_bpjs_khusus_icd10,
                    lama_rawat_inap=lama_rawat_inap,
                    kriteria_rawat_inap=kriteria_rawat_inap,
                    indikasi_rawat_inap=indikasi_rawat_inap,
                    indikasi_rujukan=indikasi_rujukan,
                    kriteria_rujukan=kriteria_rujukan,
                    tujuan_rujukan=tujuan_rujukan,
                    is_deleted=False,
                    is_dummy=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(diag)
                db.flush()

            # --- simpan informasi INA-CBG (kode, deskripsi, tarif) ---
            if ina_cbg_data:
                kode_inacbg = ina_cbg_data.get("kode")
                deskripsi_inacbg = ina_cbg_data.get("deskripsi")
                tarif_inacbg = ina_cbg_data.get("tarif")
                parsed_tarif = parse_number(tarif_inacbg)

                if kode_inacbg or tarif_inacbg:
                    cbg_entry = models.ClaimTariff(
                        claim_id=claim_id,
                        cbg_code=kode_inacbg,
                        description=deskripsi_inacbg,
                        tariff_amount=parsed_tarif,
                        status="draft",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=False,
                    )
                    db.add(cbg_entry)
                    db.flush()

            # --- buat rekomendasi AI ---
            existing_rec = db.query(models.ClaimAIRecommendation).filter_by(
                claim_id=claim_id,
                diagnosis_id=diag.id,
                stage=stage,
                is_deleted=False
            ).first()

            if existing_rec:
                print(f"[AI STORAGE] Updating existing recommendation: {diagnosis_text}")
                existing_rec.confidence_score = confidence
                existing_rec.updated_at = datetime.utcnow()
            else:
                print(f"[AI STORAGE] Inserting new recommendation: {diagnosis_text}")
                rec = models.ClaimAIRecommendation(
                    claim_id=claim_id,
                    stage=stage,
                    category=category,
                    diagnosis_id=diag.id,
                    confidence_score=confidence,
                    child=is_child,
                    is_deleted=False,
                    is_dummy=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(rec)



        # ============================================================
        # MODE: PROCEDURE
        # ============================================================
        elif mode == "procedure":
            category = ai_data.get("category", "procedure")
            procedure_text = ai_data.get("procedure_text") or ai_data.get("procedure_name") or "-"
            if not procedure_text or procedure_text.strip() == "":
                print(f"[AI STORAGE] ⚠️ Skipped storing procedure because text is empty")
                return  # jangan insert kalau kosong

            # ✅ pastikan tidak duplikat & source selalu "ai"
            existing_proc = db.query(models.ClaimProcedure).filter(
                models.ClaimProcedure.claim_id == claim_id,
                models.ClaimProcedure.procedure_text == procedure_text.strip(),
                models.ClaimProcedure.procedure_source == "ai",
                models.ClaimProcedure.is_deleted == False,
            ).first()

            icd9_code = ai_data.get("icd9_code")
            if isinstance(icd9_code, str) and "," in icd9_code:
                icd9_code = icd9_code.split(",")[0].strip()
            elif isinstance(icd9_code, list):
                icd9_code = icd9_code[0]

            if not existing_proc:
                proc = models.ClaimProcedure(
                    claim_id=claim_id,
                    procedure_text=procedure_text.strip(),
                    procedure_source="ai",  # ✅ hardcode AI di sini
                    icd9_code=icd9_code,
                    requirement_flag=False,
                    stage=stage,
                    is_deleted=False,
                    is_dummy=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(proc)
                db.flush()
                print(f"[AI STORAGE] Inserted new AI procedure: {procedure_text} (ID {proc.id})")

                # Tambahkan detail ICD-9
                if icd9_code:
                    db.add(models.ClaimProcedureDetail(
                        procedure_id=proc.id,
                        icd9_tindakan=icd9_code,
                        deskripsi_tindakan=f"ICD-9: {icd9_code}",
                        is_deleted=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    ))
            else:
                existing_proc.icd9_code = icd9_code or existing_proc.icd9_code
                existing_proc.updated_at = datetime.utcnow()
                print(f"[AI STORAGE] Updated existing AI procedure: {procedure_text}")



        # ============================================================
        # MODE: REGULATION
        # ============================================================
        elif mode == "regulation":
            regulation_data = ai_data
            if "data" in ai_data and isinstance(ai_data["data"], list) and len(ai_data["data"]) > 0:
                regulation_data = ai_data["data"][0]

            isi = regulation_data.get("isi", [])
            if isinstance(isi, list):
                isi = "\n".join(isi) if isi else ""

            # ✅ Ambil diagnosis_id / procedure_id dari payload utama juga (kalau dikirim lewat router)
            diagnosis_id = (
                regulation_data.get("diagnosis_id")
                or ai_data.get("diagnosis_id")
                or ai_data.get("item_id")
            )
            procedure_id = (
                regulation_data.get("procedure_id")
                or ai_data.get("procedure_id")
                or ai_data.get("item_id")
            )

            reg = models.ClaimRegulationDetail(
                claim_id=claim_id,
                diagnosis_id=diagnosis_id,
                procedure_id=procedure_id,
                entry_field=regulation_data.get("entry_field") or ai_data.get("field"),
                dasar_hukum=regulation_data.get("dasar_hukum", ""),
                judul_regulasi=regulation_data.get("judul_regulasi", "") or regulation_data.get("judul", ""),
                # bab_pasal removed - column deleted from database
                isi=isi,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(reg)



        # ============================================================
        # COMMIT & LOG
        # ============================================================
        db.commit()
        print(f"[AI STORAGE] ✅ Successfully stored recommendations for mode={mode}, stage={stage}")

    except Exception as e:
        db.rollback()
        print(f"[AI STORAGE] ❌ Error storing recommendations: {str(e)}")
        raise

def clear_ai_results(db: Session, claim_id: int, skip_regulation: bool = False):
    """
    Hapus seluruh hasil rekomendasi dan evaluasi AI untuk klaim tertentu.
    Biasanya dipanggil sebelum hasil baru dari core_engine disimpan ulang.
    """
    print(f"[AI STORAGE] Clearing AI results for claim {claim_id}")
    try:
        print("[AI STORAGE] Removing AI recommendations and evaluations")

        # 🧹 1️⃣ Hapus dulu regulasi (kecuali kalau disuruh skip)
        if not locals().get("skip_regulation", False):
            deleted_regs = db.query(models.ClaimRegulationDetail).filter(
                models.ClaimRegulationDetail.claim_id == claim_id
            ).delete(synchronize_session=False)
            print(f"[AI STORAGE] 🗑️ Deleted {deleted_regs} linked regulation details")
        else:
            print("[AI STORAGE] ⚠️ Skipping deletion of regulation details (preserved for verifier/coder)")

        # 🧹 2️⃣ Baru hapus hasil evaluasi & rekomendasi
        db.query(models.ClaimCombinationAlternative).filter_by(claim_id=claim_id).delete()
        db.query(models.ClaimDiagnosisEvaluation).filter_by(claim_id=claim_id).delete()
        db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=claim_id).delete()
        db.query(models.ClaimIDRGSummary).filter_by(claim_id=claim_id).delete()

        db.commit()
        print(f"[AI STORAGE] ✅ Cleared all AI results for claim {claim_id}")

    except Exception as e:
        db.rollback()
        print(f"[AI STORAGE] ❌ Failed to clear AI results: {e}")

# ==================================================
# 🔄 STORE NESTED ANALYSIS RESULTS (Diagnosis / Procedure)
# ==================================================
def _store_nested_analysis_results(db, claim_id: int, result: dict, stage: str = "admission"):
    from backend.models import (
        ClaimProcedure, ClaimProcedureDetail,
        ClaimRegulationDetail, ClaimIDRGDiagnosis, ClaimDiagnosis
    )

    try:
        print(f"[_STORE_NESTED_ANALYSIS] 🔍 Processing claim_id={claim_id}, stage={stage}")
        print(f"[_STORE_NESTED_ANALYSIS] 🔍 Available keys:", list(result.keys()))

        # ======================================================
        # 1️⃣ Clear old data (safe)
        # ======================================================
        old_procs = db.query(ClaimProcedure.id).filter_by(claim_id=claim_id, is_deleted=False).all()
        old_ids = [p.id for p in old_procs]
        if old_ids:
            db.query(ClaimProcedureDetail).filter(
                ClaimProcedureDetail.procedure_id.in_(old_ids)
            ).delete(synchronize_session=False)
        db.query(ClaimProcedure).filter_by(claim_id=claim_id, is_deleted=False).delete()
        db.commit()
        print(f"[_STORE_NESTED_ANALYSIS] 🗑️ Cleared {len(old_ids)} old procedures and their details")

        # ======================================================
        # 2️⃣ Simpan tindakan
        # ======================================================
        tindakan_list = result.get("tindakan", [])
        if not tindakan_list and any(k in result for k in ["icd9", "icd9_code", "status", "ina_cbg"]):
            tindakan_list = [result]

        if not tindakan_list:
            print("[_STORE_NESTED_ANALYSIS] ⚠️ Tidak ada tindakan ditemukan")
        else:
            for tindakan_item in tindakan_list:
                # ---- ambil nama tindakan ----
                name = (
                    tindakan_item.get("procedure_text") or tindakan_item.get("procedure_name")
                    or tindakan_item.get("tindakan") or tindakan_item.get("nama")
                    or tindakan_item.get("name") or tindakan_item.get("procedure") or "-"
                ).strip()
                if not name or name == "-":
                    print("[_STORE_NESTED_ANALYSIS] ⚠️ Skip tindakan tanpa nama")
                    continue

                # ---- ambil ICD utama ----
                icd_raw = tindakan_item.get("icd9") or tindakan_item.get("icd9_code") or ""
                icd9_main = None
                if isinstance(icd_raw, str):
                    parts = [p.strip() for p in icd_raw.split(",") if p.strip()]
                    icd9_main = parts[0] if parts else None
                elif isinstance(icd_raw, list) and icd_raw:
                    icd9_main = str(icd_raw[0]).strip()

                if not icd9_main:
                    icd9_main = "-"  # fallback biar ga null

                # ---- buat procedure record ----
                proc = ClaimProcedure(
                    claim_id=claim_id,
                    procedure_source=tindakan_item.get("procedure_source", "ai"),
                    procedure_text=name,
                    icd9_code=icd9_main,
                    requirement_flag=False,
                    stage=stage,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_deleted=False,
                    is_dummy=False,
                )
                db.add(proc)
                db.flush()

                # ---- ambil field tambahan ----
                status_val = tindakan_item.get("status") or tindakan_item.get("status_tindakan")
                ina_val = tindakan_item.get("ina_cbg_tarif") or tindakan_item.get("ina_cbg")

                # ---- buat deskripsi gabungan ----
                desc = f"ICD-9 utama: {icd9_main}"
                if isinstance(icd_raw, str) and "," in icd_raw:
                    desc += f" (kode lain: {icd_raw})"
                if status_val:
                    desc += f", Status: {status_val}"
                if ina_val:
                    desc += f", INA-CBG: {ina_val}"

                # ---- insert detail ----
                detail = ClaimProcedureDetail(
                    procedure_id=proc.id,
                    icd9_tindakan=icd9_main,
                    validitas_tindakan=tindakan_item.get("validitas") or tindakan_item.get("validitas_tindakan"),
                    status_tindakan=status_val,
                    ina_cbg_tindakan=ina_val,
                    faskes_tindakan=tindakan_item.get("faskes"),
                    rawat_inap_tindakan=tindakan_item.get("rawat_inap"),
                    syarat_klinis_tindakan=tindakan_item.get("syarat_klinis"),
                    deskripsi_tindakan=desc,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_deleted=False,
                    is_dummy=False,
                )
                db.add(detail)

        # ======================================================
        # 3️⃣ Simpan multilayer regulasi
        # ======================================================
        multilayer_rules = result.get("multilayer_rules") or {}
        if multilayer_rules:
            print(f"[_STORE_NESTED_ANALYSIS] 🧩 multilayer_rules: {list(multilayer_rules.keys())}")
            source_diag = db.query(ClaimDiagnosis).filter_by(claim_id=claim_id).first()
            diag_id = source_diag.id if source_diag else None
            source_proc = db.query(ClaimProcedure).filter_by(claim_id=claim_id).first()
            proc_id = source_proc.id if source_proc else None

            for field, field_data in multilayer_rules.items():
                for item in field_data.get("items", []):
                    db.add(ClaimRegulationDetail(
                        claim_id=claim_id,
                        entry_field=field,
                        diagnosis_id=diag_id,
                        procedure_id=proc_id,
                        dasar_hukum=item.get("sumber"),
                        judul_regulasi=item.get("judul_regulasi") or field,
                        isi=item.get("isi"),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=False
                    ))
            print("[_STORE_NESTED_ANALYSIS] ✅ Stored multilayer regulation data")

        # ======================================================
        # 4️⃣ Simpan IDRG (kalau ada)
        # ======================================================
        idrg_data = (
            result.get("idrg_prediction") or result.get("idrg")
            or result.get("idrg_result") or result.get("idrg_summary")
            or result.get("idrg_data") or {}
        )
        if idrg_data:
            db.add(ClaimIDRGDiagnosis(
                claim_id=claim_id,
                group_idrg=idrg_data.get("group_idrg") or idrg_data.get("code"),
                severity_index=idrg_data.get("severity_index") or idrg_data.get("severity"),
                checklist=idrg_data.get("checklist"),
                ungroupable_alert=idrg_data.get("ungroupable_alert"),
                faktor_severity=idrg_data.get("faktor_severity"),
                simulasi_tarif=idrg_data.get("simulasi_tarif"),
                gap_analysis=idrg_data.get("gap_analysis"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
                is_dummy=False,
            ))
            print("[_STORE_NESTED_ANALYSIS] ✅ IDRG data stored")
        else:
            print("[_STORE_NESTED_ANALYSIS] ⚠️ No IDRG data found")

        db.commit()
        print(f"[_STORE_NESTED_ANALYSIS] ✅ Commit complete for claim {claim_id}")

    except Exception as e:
        db.rollback()
        print(f"[_STORE_NESTED_ANALYSIS] ❌ Error: {e}")
        import traceback; traceback.print_exc()
    
# ==================================================
# AI EVALUATIONS (hasil generate_claim_combos / summary)
# ==================================================

def store_ai_evaluations(db: Session, claim_id: int, evaluasi: dict):
    """
    Simpan hasil evaluasi kombinasi ke tabel pecahan:
      - ClaimDiagnosisEvaluation
      - ClaimProcedureEvaluation
      - ClaimCombinationAlternative
    """
    import json

    # 🧹 Bersihkan dulu
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
        if "valid" in raw_lower or "✅" in raw_lower:
            return "valid"
        return None


    # 🔄 Normalisasi key agar kompatibel
    if "evaluasi_diagnosis" in evaluasi:
        evaluasi["kombinasi_diagnosis"] = evaluasi.pop("evaluasi_diagnosis")
    if "evaluasi_tindakan" in evaluasi:
        val = evaluasi.pop("evaluasi_tindakan")
        evaluasi["kombinasi_tindakan"] = [val] if isinstance(val, dict) else val
    if not evaluasi.get("alternatif"):
        evaluasi["alternatif"] = evaluasi.get("alternatives", [])


    # === Diagnosis ===
    diag = evaluasi.get("kombinasi_diagnosis", {})
    if isinstance(diag, str):
        try:
            diag = json.loads(diag)
        except Exception:
            print(f"[AI STORAGE] ⚠️ Failed to parse string diag: {diag}")
            diag = {}

    if diag:
        # 🧠 Pisahkan validitas dan detail
        raw_valid = diag.get("validitas", "")
        parsed_valid = parse_validitas(raw_valid)
        # Hilangkan emoji/ikon dan sisakan kalimat lengkap
        clean_detail = (
            raw_valid.replace("✅", "")
            .replace("❌", "")
            .replace("⚠️", "")
            .strip()
        )

        # Kalau validitas_detail belum ada, pakai hasil ekstraksi dari validitas
        validitas_detail = diag.get("validitas_detail") or clean_detail or None

        db.add(models.ClaimDiagnosisEvaluation(
            claim_id=claim_id,
            validitas=parsed_valid,
            validitas_detail=validitas_detail,
            severity=diag.get("severity"),
            kode_ina_cbg=diag.get("kode_ina_cbg") or diag.get("kode_cbg"),
            estimasi_tarif=parse_number(diag.get("estimasi_tarif")),
            syarat_klinis=diag.get("syarat_klinis"),
            evaluasi_faskes=diag.get("evaluasi_faskes"),
            rawat_inap=diag.get("rawat_inap"),
            is_dummy=False,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))
        print(f"[AI STORAGE] ✅ Stored diagnosis evaluation for claim {claim_id}")

    # === Tindakan ===

    for td in evaluasi.get("kombinasi_tindakan", []):
        if isinstance(td, str):
            try:
                td = json.loads(td)
            except Exception:
                td = {}

        db.add(models.ClaimProcedureEvaluation(
            claim_id=claim_id,
            wajib=td.get("wajib"),
            validasi=td.get("validasi"),
            dampak=td.get("dampak"),
            konflik=td.get("konflik"),
            is_dummy=False,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))
        print(f"[AI STORAGE] ✅ Stored procedure evaluation for claim {claim_id}")


    # === Alternatif (with fallback & parsing) ===
    alt_list = evaluasi.get("alternatif") or evaluasi.get("alternatives") or []

    print(f"[AI STORAGE] 🧩 Alt list length: {len(alt_list)}")
    for alt in alt_list:
        if isinstance(alt, str):
            try:
                alt = json.loads(alt)
            except Exception:
                alt = {}

        db.add(models.ClaimCombinationAlternative(
            claim_id=claim_id,
            kombinasi_nama=alt.get("kombinasi_nama") or alt.get("nama") or alt.get("judul"),
            severity=alt.get("severity"),
            kode_ina_cbg=alt.get("kode_ina_cbg") or alt.get("kode_cbg") or alt.get("ina_cbg"),
            estimasi_tarif=parse_number(alt.get("estimasi_tarif") or alt.get("tarif")),
            syarat_klinis=alt.get("syarat_klinis") or alt.get("syarat"),
            faskes=alt.get("faskes"),
            rawat_inap=alt.get("rawat_inap"),
            tindakan_wajib=alt.get("tindakan_wajib") or json.dumps(alt.get("tindakan") or []),
            is_dummy=False,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))


    # === iDRG Summary (hasil predict_combo_idrg) ===
    try:
        idrg_summary = (
            evaluasi.get("idrg_summary")
            or evaluasi.get("idrg_prediction")
            or evaluasi.get("data")
            or {}
        )
        if idrg_summary:
            db.query(models.ClaimIDRGSummary).filter_by(claim_id=claim_id).delete(synchronize_session=False)

            db.add(models.ClaimIDRGSummary(
                claim_id=claim_id,
                group_idrg_kombinasi=idrg_summary.get("group_idrg_kombinasi") or idrg_summary.get("group_idrg"),
                severity_kombinasi=idrg_summary.get("severity_kombinasi") or idrg_summary.get("severity"),
                checklist_kombinasi=json.dumps(idrg_summary.get("checklist_kombinasi") or [], ensure_ascii=False),
                faktor_severity=json.dumps(idrg_summary.get("faktor_severity_kombinasi") or [], ensure_ascii=False),
                risiko_ungroupable=idrg_summary.get("risiko_ungroupable"),
                estimasi_tarif=idrg_summary.get("estimasi_tarif"),
                gap_inacbg_vs_idrg=idrg_summary.get("gap_vs_cbg") or idrg_summary.get("gap_analysis"),
                rekomendasi_ai=idrg_summary.get("rekomendasi_ai") or idrg_summary.get("notification", {}).get("message"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
                is_dummy=False
            ))
            print(f"[AI STORAGE] ✅ Stored iDRG summary for claim {claim_id}")
        else:
            print(f"[AI STORAGE] ⚠️ No iDRG summary found in evaluation payload")

    except Exception as e:
        print(f"[AI STORAGE] ❌ Error storing ClaimIDRGSummary: {e}")


    db.commit()
    print(f"[AI STORAGE] ✅ Stored {len(alt_list)} alternatives for claim {claim_id}")
    print(f"[AI STORAGE] ✅ Successfully stored AI evaluations for claim {claim_id}")

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
        "procedure_evaluations": 0,
        "idrg_summary": 0
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
        alternatives = result.get("alternatif") or result.get("alternatives") or []
        for alt in alternatives:
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
                    is_dummy=False,
                    is_deleted=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
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

        # Store iDRG summary
        idrg_summary = result.get("idrg_summary") or {}
        try:
            if idrg_summary:
                db.add(models.ClaimIDRGSummary(
                    claim_id=claim_id,
                    group_idrg_kombinasi=idrg_summary.get("group_idrg_kombinasi"),
                    severity_kombinasi=idrg_summary.get("severity_kombinasi"),
                    checklist_kombinasi=json.dumps(idrg_summary.get("checklist_kombinasi") or [], ensure_ascii=False),
                    faktor_severity=json.dumps(idrg_summary.get("faktor_severity_kombinasi") or [], ensure_ascii=False),
                    risiko_ungroupable=idrg_summary.get("risiko_ungroupable"),
                    estimasi_tarif=idrg_summary.get("estimasi_tarif"),
                    gap_inacbg_vs_idrg=idrg_summary.get("gap_inacbg_vs_idrg"),
                    rekomendasi_ai=idrg_summary.get("rekomendasi_ai"),
                ))
                stored_items["idrg_summary"] = 1
        except Exception as e:
            print(f"[AI STORAGE] Error storing iDRG summary: {str(e)}")
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