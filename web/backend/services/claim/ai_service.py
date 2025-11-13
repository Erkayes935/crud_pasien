"""
AI Service Layer
Menggabungkan proxy (claim_ai.py) dan storage (ai.py)
Router hanya perlu memanggil fungsi di sini.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from . import ai
from backend.services import claim_ai, claim_helper

# ==================================================
# 🔹 PREDICT DDX (AI COMBO INITIAL)
# ==================================================
async def predict_ddx(db: Session, claim_id: int, payload: dict):
    """Proxy ke core_engine dan simpan hasil rekomendasi awal (DDx)"""
    cid = payload.get("claim_id") or claim_id
    if not cid:
        raise HTTPException(status_code=422, detail="claim_id required")

    stage = (payload.get("stage") or "admission").strip()
    global_record = claim_helper.build_global_record(db, cid)
    forward = {"claim_id": cid, "stage": stage, "global_record": global_record}

    result = await claim_ai.proxy_core_engine("/predict_ddx", forward)
    normalized = claim_helper.normalize_predict_ddx(result)

    try:
        print(f"[AI_SERVICE] 🧠 predict_ddx storing results for claim {cid}")
        ai.clear_ai_results(db, cid)
        ai.store_ai_recommendations(db, cid, normalized, "predict", stage)
        db.commit()
    except Exception as e:
        print(f"[AI_SERVICE] ❌ Error storing predict_ddx: {e}")
        db.rollback()

    return normalized


# ==================================================
# 🔹 ANALYZE DIAGNOSIS
# ==================================================
async def analyze_diagnosis(db: Session, claim_id: int, payload: dict):
    """Analisis diagnosis via AI + simpan semua hasil"""
    import time
    start_time = time.time()
    diagnosis_name = payload.get("disease_name", "")

    # ✅ Cek cache dulu
    cached = load_cache(diagnosis_name)
    if cached:
        print(f"[CACHE] ✅ Loaded cached result for {diagnosis_name}")
        return cached

    # 🔹 Kalau belum ada cache, panggil core_engine
    result = await claim_ai.proxy_core_engine("/analyze_diagnosis", payload)
    print(f"[AI_SERVICE] 🧩 core engine call analyze_diagnosis for claim {claim_id} took {time.time() - start_time:.2f} seconds")

    stage = payload.get("stage", "admission")

    try:
        print(f"[AI_SERVICE] 🧩 analyze_diagnosis storing for claim {claim_id}")
        if diagnosis_name:
            result["diagnosis_text"] = diagnosis_name

        # simpan hasil AI utama
        ai.store_ai_recommendations(db, claim_id, result, "diagnosis", stage)

        # simpan tindakan / regulasi / IDRG jika ada di response
        ai._store_nested_analysis_results(db, claim_id, result, stage)

        # 🩵 Simpan aspek lainnya (jika ada)
        aspek_data = result.get("aspek_lainnya")
        if aspek_data:
            if isinstance(aspek_data, dict) and "aspek_lainnya" in aspek_data:
                aspek_value = aspek_data["aspek_lainnya"]
            else:
                aspek_value = aspek_data
            ai.store_aspek_lainnya(db, claim_id, aspek_value, stage)

        db.commit()

        # ==================================================
        # 🔹 SIMPAN CACHE SETELAH HASIL SUKSES DISIMPAN
        # ==================================================
        try:
            if diagnosis_name:
                save_cache(diagnosis_name, result)
                print(f"[CACHE] 💾 Saved cache for {diagnosis_name}")
            else:
                print("[CACHE] ⚠️ Tidak ada diagnosis_name, cache dilewati.")
        except Exception as e:
            print(f"[CACHE] ❌ Gagal menyimpan cache: {e}")
            
    except Exception as e:
        db.rollback()
        print(f"[AI_SERVICE] ❌ Error analyze_diagnosis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # ==================================================
    # 🔹 AUTO GENERATE IDRG (fix untuk hasil tidak masuk DB)
    # ==================================================
    try:
        print(f"[AI_SERVICE] 🔄 Auto generating i-DRG for claim {claim_id}...")

        idrg_payload = {
            "diagnosis_name": payload.get("disease_name"),
            "rs_id": payload.get("rs_id"),
            "region_id": payload.get("region_id"),
            # ambil daftar tindakan dari hasil analisis diagnosis
            "tindakan_names": [
                t.get("nama") or t.get("procedure_text")
                for t in result.get("tindakan", [])
                if isinstance(t, dict)
            ],
        }

        idrg_result = await claim_ai.predict_idrg(idrg_payload)

        # 🔧 Normalisasi struktur supaya bisa dibaca oleh _store_nested_analysis_results()
        if "data" in idrg_result and not idrg_result.get("idrg_prediction"):
            idrg_result["idrg_prediction"] = idrg_result["data"]

        # 🧠 Field mapping dari core_engine -> DB model
        idrg_pred = idrg_result.get("idrg_prediction", {})
        if idrg_pred:
            idrg_pred["checklist"] = idrg_pred.get("checklist_dokumentasi")
            idrg_pred["faktor_severity"] = idrg_pred.get("faktor_penentu_severity")
            idrg_pred["simulasi_tarif"] = idrg_pred.get("estimasi_tarif")
            idrg_result["idrg_prediction"] = idrg_pred

        ai._store_nested_analysis_results(db, claim_id, idrg_result, stage)

        
        idrg_data = idrg_result.get("idrg_prediction", {})
        print(f"[AI_SERVICE] 🧩 i-DRG result group: {idrg_data.get('group_idrg')} | severity: {idrg_data.get('severity_index')}")

        db.commit()
        print(f"[AI_SERVICE] ✅ i-DRG stored successfully for claim {claim_id}")

    except Exception as e:
        db.rollback()
        print(f"[AI_SERVICE] ⚠️ Failed to store i-DRG: {e}")

    return result


# ==================================================
# 🔹 ANALYZE PROCEDURE
# ==================================================
async def analyze_procedure(db: Session, claim_id: int, payload: dict):
    """Analisis tindakan via AI + simpan ke DB"""
    cid = payload.get("claim_id") or claim_id
    procedure_text = payload.get("procedure_text")
    if not cid or not procedure_text:
        raise HTTPException(status_code=422, detail="claim_id and procedure_text required")

    stage = (payload.get("stage") or "admission").strip()
    context = claim_helper.build_procedure_context(db, cid, stage)
    core_payload = {"claim_id": cid, "procedure_text": procedure_text, "stage": stage, "context": context}

    result = await claim_ai.proxy_core_engine("/analyze_procedure", core_payload)

    try:
        # ✅ simpan record utama (ClaimProcedure)
        ai.store_ai_recommendations(db, cid, result, "procedure", stage)

        # ✅ lalu simpan detail-detailnya
        ai._store_nested_analysis_results(db, cid, result, stage)

        # 🩵 Simpan aspek lainnya (jika ada)
        aspek_data = result.get("aspek_lainnya")
        if aspek_data:
            if isinstance(aspek_data, dict) and "aspek_lainnya" in aspek_data:
                aspek_value = aspek_data["aspek_lainnya"]
            else:
                aspek_value = aspek_data
            ai.store_aspek_lainnya(db, claim_id, aspek_value, stage)


        db.commit()
        print(f"[AI_SERVICE] ✅ Stored analyze_procedure for {procedure_text}")
    except Exception as e:
        db.rollback()
        print(f"[AI_SERVICE] ❌ Error analyze_procedure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return result


# ==================================================
# 🔹 GENERATE CLAIM COMBOS
# ==================================================
async def generate_claim_combos(db: Session, claim_id: int, payload: dict):
    """Generate kombinasi AI untuk klaim"""
    cid = payload.get("claim_id") or claim_id
    if not cid:
        raise HTTPException(status_code=422, detail="claim_id required")

    core_payload = {
        "claim_id": cid,
        "primary_claim": payload.get("primary_claim", ""),
        "secondary_claims": payload.get("secondary_claims", []),
        "primary_action": payload.get("primary_action", ""),
        "secondary_actions": payload.get("secondary_actions", []),
    }

    result = await claim_ai.proxy_core_engine("/generate_claim_combos", core_payload)

    try:
        # Skip hapus regulasi kalau user role adalah verifikator atau coder
        user_role = getattr(payload, "user_role", None) or payload.get("role")
        if user_role in ["verifikator", "coder"]:
            ai.clear_ai_results(db, cid, skip_regulation=True)
        else:
            ai.clear_ai_results(db, cid)
        ai.bulk_store_ai_results_from_core(db, cid, result)
        ai.store_ai_evaluations(db, cid, result)
        # 🩵 Tambahkan ini:
        aspek_data = result.get("aspek_lainnya") or result.get("data", {}).get("aspek_lainnya")
        if aspek_data:
            if isinstance(aspek_data, dict) and "aspek_lainnya" in aspek_data:
                aspek_value = aspek_data["aspek_lainnya"]
            else:
                aspek_value = aspek_data
            ai.store_aspek_lainnya(db, cid, aspek_value, stage="admission")
        db.commit()
        print(f"[AI_SERVICE] ✅ Stored claim_combos for claim {cid}")
    except Exception as e:
        db.rollback()
        print(f"[AI_SERVICE] ❌ Error generate_claim_combos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return result


# ==================================================
# 🔹 RESUME MEDIS
# ==================================================
async def resume_medis(db: Session, claim_id: int, payload: dict):
    """Generate dan simpan resume medis AI"""
    result = await claim_ai.proxy_core_engine("/resume_medis", payload)
    try:
        claim = db.query(ai.models.Claim).get(claim_id)
        if claim and isinstance(result, dict) and result.get("resume"):
            claim.ai_medical_resume = result["resume"]
            claim.updated_at = datetime.utcnow()
            db.commit()
            print(f"[AI_SERVICE] ✅ Stored AI resume for claim {claim_id}")
    except Exception as e:
        db.rollback()
        print(f"[AI_SERVICE] ❌ Error resume_medis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return result

# ==================================================
# 🔹 SAVE REGULATION RESULT
# ==================================================
async def save_regulation_detail(db: Session, claim_id: int, payload: dict):
    """Simpan hasil regulasi multilayer dari Core Engine ke ClaimRegulationDetail"""
    result = await claim_ai.regulation_detail(payload)
    if not result or "data" not in result:
        raise HTTPException(status_code=400, detail="Tidak ada hasil regulasi dari core_engine")

    rules = result.get("data", [])
    if isinstance(rules, dict):
        rules = [rules]

    # hapus cache lama
    db.query(ai.models.ClaimRegulationDetail).filter(
        ai.models.ClaimRegulationDetail.claim_id == claim_id,
        ai.models.ClaimRegulationDetail.entry_field == payload.get("field")
    ).delete()

    saved = 0
    for reg in rules:
        try:
            new_reg = ai.models.ClaimRegulationDetail(
                claim_id=claim_id,
                entry_field=payload.get("field"),
                judul_regulasi=reg.get("judul_regulasi") or reg.get("judul") or "-",
                dasar_hukum=reg.get("layer") or reg.get("dasar_hukum") or "-",
                isi=reg.get("isi") or "-",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
            )
            db.add(new_reg)
            saved += 1
        except Exception as e:
            print(f"[AI_SERVICE] ⚠️ Skip save regulation: {e}")

    db.commit()
    print(f"[AI_SERVICE] ✅ Stored {saved} regulation(s) for claim {claim_id}")
    return {"status": "success", "total_saved": saved, "data": rules}

# ==================================================
# 🔹 Simple file cache untuk hasil reasoning diagnosis
# ==================================================
import os, orjson

def get_cache_path(diagnosis_name):
    os.makedirs("tmp", exist_ok=True)  # buat folder kalau belum ada
    safe_name = diagnosis_name.replace(" ", "_").lower()
    return f"tmp/cache_diagnosis_{safe_name}.json"

def load_cache(diagnosis_name):
    path = get_cache_path(diagnosis_name)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return orjson.loads(f.read())
    return None

def save_cache(diagnosis_name, data):
    path = get_cache_path(diagnosis_name)
    with open(path, "wb") as f:
        f.write(orjson.dumps(data))