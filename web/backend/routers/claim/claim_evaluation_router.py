"""
routers/claim/claim_evaluation_router.py
Refactor modular dari claim_router.py
Fokus: endpoint simulasi & evaluasi hasil AI.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.auth import require_roles_session
from backend.services.claim.simulation import get_simulations_service, get_simulations_for_verificator

router = APIRouter(tags=["Claim Evaluation"])


# ======================================================
# 🧠 GET SIMULATIONS (CODER / VERIFIKATOR)
# ======================================================

@router.get("/{claim_id}/simulations")
def get_simulations(
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """
    Ambil daftar hasil simulasi atau hasil verifikasi tergantung peran user.
    """
    try:
        role_names = user.role_names or []
        # 🔹 Jika user adalah verifikator, ambil dari hasil verifikasi coder
        if "verifikator" in role_names:
            data = get_simulations_for_verificator(db, claim_id)
        else:
            data = get_simulations_service(db, claim_id)
        return {"status": "ok", "data": data}
    except Exception as e:
        print(f"[GET_SIMULATIONS] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal ambil data simulasi: {e}")

@router.post("/{claim_id}/generate_claim_combos", name="generate_claim_combos")
async def generate_claim_combos(
    claim_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """
    Endpoint untuk evaluasi kombinasi diagnosis dan tindakan (summary evaluasi).
    Mengirim payload ke core_engine → menyimpan hasil → flatten ke FE.
    """
    from backend.services import claim_ai
    from backend.services.claim import ai

    cid = payload.get("claim_id") or claim_id
    if not cid:
        raise HTTPException(status_code=422, detail="claim_id required")

    print(f"[GENERATE_CLAIM_COMBOS] ▶️ Received payload for claim {cid}")

    try:
        # 🔹 Siapkan payload untuk core_engine
        core_payload = {
            "claim_id": cid,
            "primary_claim": payload.get("primary_claim", ""),
            "secondary_claims": payload.get("secondary_claims", []),
            "primary_action": payload.get("primary_action", ""),
            "secondary_actions": payload.get("secondary_actions", []),
        }

        print(f"[GENERATE_CLAIM_COMBOS] ▶️ Forwarding to core_engine with payload: {core_payload}")
        result = await claim_ai.proxy_core_engine("/generate_claim_combos", core_payload)

        # 🔴 Kalau core_engine balikin error
        if isinstance(result, dict) and result.get("error"):
            print(f"[GENERATE_CLAIM_COMBOS] ❌ Error from core_engine: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])

        print(f"[GENERATE_CLAIM_COMBOS] ✅ Got result from core_engine, storing results to DB")

        # 🔹 Step 1: Clear hasil lama
        ai.clear_ai_results(db, cid)

        # 🔹 Step 2: Simpan hasil utama (summary & kombinasi)
        ai.bulk_store_ai_results_from_core(db, cid, result)

        # 🔹 Step 3: Simpan hasil evaluasi tambahan (jika ada)
        core_data = result.get("result") or result or {}
        if isinstance(core_data, dict) and any(
            k in core_data for k in ["evaluasi_diagnosis", "evaluasi_tindakan", "alternatif"]
        ):
            try:
                print(f"[GENERATE_CLAIM_COMBOS] 🧠 Storing AI evaluations for claim {cid}")
                print("[DEBUG] Raw result keys:", list(core_data.keys()))
                ai.store_ai_evaluations(db, cid, core_data)
                print(f"[GENERATE_CLAIM_COMBOS] ✅ AI evaluations stored successfully")
                # 🔹 Step 3.1: Simpan aspek_lainnya ke claim_combo_evaluations jika ada
                if "aspek_lainnya" in result:
                    try:
                        print(f"[GENERATE_CLAIM_COMBOS] 💾 Storing aspek_lainnya for claim_combo_evaluations ({cid})")
                        ai.store_aspek_lainnya(db, cid, result["aspek_lainnya"], stage="kombinasi")
                        print(f"[GENERATE_CLAIM_COMBOS] ✅ Aspek Lainnya stored successfully")
                    except Exception as e:
                        print(f"[GENERATE_CLAIM_COMBOS] ⚠️ Failed to store aspek_lainnya for combo: {e}")

            except Exception as e:
                import traceback

                traceback.print_exc()
                print(f"[GENERATE_CLAIM_COMBOS] ⚠️ Failed to store evaluations: {e}")
                # Jangan raise — tetap commit hasil utama

        # 🔹 Step 4: Alias key untuk FE compatibility
        if "evaluasi_diagnosis" in result:
            result["diagnosis"] = result["evaluasi_diagnosis"]
        if "evaluasi_tindakan" in result:
            result["procedure"] = result["evaluasi_tindakan"]
        if "alternatif" in result:
            result["alternatives"] = result["alternatif"]
        # Tambah alias untuk aspek_lainnya (jika ada)
        if "aspek_lainnya" in result:
            result["aspek_lainnya"] = result["aspek_lainnya"]

        # 🔹 Step 5: Commit global
        db.commit()
        print(f"[GENERATE_CLAIM_COMBOS] 💾 All AI results committed successfully")

        return {
            "claim_id": cid,
            "stage": payload.get("stage", "admission"),
            "status": "success",
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[GENERATE_CLAIM_COMBOS] ❌ Unhandled error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate claim combos: {str(e)}")
