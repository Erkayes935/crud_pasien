"""
routers/claim/claim_ai_router.py
Refactor modular dari claim_router.py
Fokus: endpoint AI untuk analisis diagnosis dan procedure.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.auth import require_roles_session
from backend import models
from backend.services import claim_ai, claim_helper
from backend.services.claim import ai, ai_service
from backend.services.claim.simulation import models
from backend.utils.dummy_data import (
    dummy_diagnosis_list,
    dummy_tindakan_list,
    dummy_diagnosis_detail,
    dummy_tindakan_detail,
)
from sqlalchemy import func

router = APIRouter(tags=["Claim AI"])

# ======================================================
# 🧠 PREDICT DIFFERENTIAL DIAGNOSIS (AI)
# ======================================================

@router.post("/{claim_id}/predict_ddx")
async def predict_ddx(
    claim_id: int,
    payload: dict = Body(...),
    db=Depends(get_db),
    user=Depends(require_roles_session("doctor")),
):
    try:
        # panggil helper & core engine langsung
        return await ai_service.predict_ddx(db, claim_id, payload)
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ======================================================
# 🧠 ANALYZE DIAGNOSIS (dokter)
# ======================================================
@router.post("/{claim_id}/analyze_diagnosis")
async def analyze_diagnosis(
    claim_id: int,
    payload: dict = Body(...),
    db=Depends(get_db),
    user=Depends(require_roles_session("doctor")),
):
    import time
    start_time = time.time()
    try:
        result = await ai_service.analyze_diagnosis(db, claim_id, payload)
        # 🩵 kalau FE kirim aspek_lainnya, simpan juga langsung di sini
        if payload.get("aspek_lainnya"):
            from backend.services.claim import ai
            ai.store_aspek_lainnya(db, claim_id, payload["aspek_lainnya"], payload.get("stage", "admission"))

        elapsed_time = time.time() - start_time
        print(f"[ANALYZE_DIAGNOSIS] 🧩 analyze_diagnosis for claim {claim_id} took {elapsed_time:.2f} seconds")
        return {"status": "success", "data": result}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Gagal analyze_diagnosis: {str(e)}")

# ======================================================
# ⚙️ ANALYZE PROCEDURE (dokter)
# ======================================================
@router.post("/{claim_id}/analyze_procedure")
async def analyze_procedure(
    claim_id: int,
    payload: dict = Body(...),
    db=Depends(get_db),
    user=Depends(require_roles_session("doctor")),
):
    try:
        result = await ai_service.analyze_procedure(db, claim_id, payload)
        # 🩵 simpan aspek_lainnya kalau dikirim
        if payload.get("aspek_lainnya"):
            from backend.services.claim import ai
            ai.store_aspek_lainnya(db, claim_id, payload["aspek_lainnya"], payload.get("stage", "admission"))

        return {"status": "success", "data": result}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Gagal analyze_procedure: {str(e)}")

# ======================================================
# 🧠 GENERATE ALTERNATIVE COMBINATIONS (AI META)
# ======================================================
@router.post("/{claim_id}/generate_alternatives")
async def generate_alternatives(
    claim_id: int,
    payload: dict = Body(...),
    db=Depends(get_db),
    user=Depends(require_roles_session("verifikator")),
):
    try:
        result = await ai_service.generate_claim_combos(db, claim_id, payload)
        return {"status": "success", "data": result}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Gagal generate_alternatives: {str(e)}")

# ==================================================
# 🔎 SEARCH AUTOCOMPLETE (DUMMY UNTIL BRIDGING READY)
# ==================================================

@router.get("/search/diagnosis")
def search_diagnosis(query: str = ""):
    """
    Autocomplete pencarian diagnosis (dummy sementara).
    Nanti bisa diganti ke DataHub / CoreEngine search endpoint.
    """
    dummy = dummy_diagnosis_list()
    results = [d for d in dummy if query.lower() in d["name"].lower()]
    return {"status": "ok", "data": results}


@router.get("/search/diagnosis/detail/{code}")
def search_diagnosis_detail(code: str):
    return {"status": "ok", "data": dummy_diagnosis_detail(code)}


@router.get("/search/tindakan")
def search_tindakan(query: str = ""):
    dummy = dummy_tindakan_list()
    if query:
        results = [d for d in dummy if query.lower() in d["procedure_text"].lower()]
    else:
        results = dummy
    return {"status": "ok", "data": results}


@router.get("/search/tindakan/detail/{procedure_text}")
def search_tindakan_detail(procedure_text: str):
    return {"status": "ok", "data": dummy_tindakan_detail(procedure_text)}
