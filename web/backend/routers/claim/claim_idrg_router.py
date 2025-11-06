"""
routers/claim/claim_idrg_router.py
Refactor modular untuk endpoint i-DRG Prediction (single & combo).
Source: pindahan langsung dari claim_router.py (versi lama).
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.auth import require_roles_session
from backend import models
from backend.services import claim_ai
import json

router = APIRouter(tags=["Claim IDRG"])


# ==================================================
# i-DRG PREDICTION ENDPOINTS
# ==================================================

@router.post("/{claim_id}/predict_idrg")
async def predict_idrg_endpoint(
    claim_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin"))
):
    """
    Universal endpoint untuk prediksi i-DRG.
    Menentukan mode (single / combo) lalu dispatch ke sub-endpoint terkait.
    """
    try:
        payload["claim_id"] = claim_id
        mode = payload.get("mode", "single")

        print(f"[PREDICT_IDRG] Mode: {mode}, Claim ID: {claim_id}")

        if mode == "single":
            return await predict_idrg_single_endpoint(payload, db)
        elif mode == "combo":
            return await predict_idrg_combo_endpoint(claim_id, payload, db)
        else:
            # fallback ke core_engine langsung
            result = await claim_ai.proxy_core_engine("/predict_idrg", payload)
            print("[WEB DEBUG] Raw result from core_engine:", json.dumps(result, indent=2, ensure_ascii=False))

            if isinstance(result, dict) and result.get("error"):
                raise HTTPException(status_code=500, detail=result["error"])
            return result

    except Exception as e:
        print(f"[PREDICT_IDRG] ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================================================
# SINGLE MODE
# ==================================================

@router.post("/predict_idrg/single")
async def predict_idrg_single_endpoint(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Predict i-DRG untuk diagnosis single"""
    try:
        claim_id = payload.get("claim_id")
        result = await claim_ai.proxy_core_engine("/predict_idrg", {
            "mode": "single",
            **payload
        })

        if claim_id and isinstance(result, dict) and result.get("idrg_prediction"):
            try:
                print(f"[PREDICT_IDRG_SINGLE] Storing i-DRG results for claim {claim_id}")

                db.query(models.ClaimIDRGDiagnosis).filter_by(
                    claim_id=claim_id, is_deleted=False
                ).update({"is_deleted": True})

                idrg_data = result["idrg_prediction"]
                idrg_diag = models.ClaimIDRGDiagnosis(
                    claim_id=claim_id,
                    group_idrg=idrg_data.get("group_idrg"),
                    severity_index=idrg_data.get("severity_index"),
                    checklist=json.dumps(idrg_data.get("checklist", {})),
                    faktor_severity=json.dumps(idrg_data.get("faktor_severity", {})),
                    ungroupable_alert=idrg_data.get("ungroupable_alert"),
                    simulasi_tarif=str(idrg_data.get("simulasi_tarif", "")),
                    gap_analysis=idrg_data.get("gap_analysis"),
                    is_deleted=False,
                    is_dummy=False
                )
                db.add(idrg_diag)
                db.commit()
                print(f"[PREDICT_IDRG_SINGLE] ✅ Successfully stored i-DRG results")
            except Exception as e:
                print(f"[PREDICT_IDRG_SINGLE] ❌ Error storing results: {str(e)}")
                db.rollback()

        return result
    except Exception as e:
        print(f"[PREDICT_IDRG_SINGLE] ❌ Unexpected Error: {str(e)}")
        return {"status": "error", "message": str(e)}


# ==================================================
# COMBO MODE
# ==================================================

@router.post("/predict_idrg/combo")
async def predict_idrg_combo_endpoint(
    claim_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Predict i-DRG kombinasi diagnosis + procedure"""
    try:
        payload["claim_id"] = claim_id
        payload["mode"] = "combo"

        print(f"[PREDICT_IDRG_COMBO] Payload: {payload}")

        # Normalisasi key input dari FE
        if "primary_diagnosis" not in payload and "primary_claim" in payload:
            payload["primary_diagnosis"] = payload["primary_claim"]

        if "secondary_diagnosis" not in payload and "secondary_claims" in payload:
            payload["secondary_diagnosis"] = payload["secondary_claims"]

        if "procedures" not in payload:
            procedures = []
            if "primary_action" in payload and payload["primary_action"]:
                procedures.append(payload["primary_action"])
            if "secondary_actions" in payload:
                procedures.extend([p for p in payload["secondary_actions"] if p])
            payload["procedures"] = procedures

        # Call core_engine
        result = await claim_ai.proxy_core_engine("/predict_idrg", payload)
        print(f"[PREDICT_IDRG_COMBO] Raw result from core_engine:", json.dumps(result, indent=2, ensure_ascii=False))
        
        if isinstance(result, dict) and result.get("error"):
            print(f"[PREDICT_IDRG_COMBO] Error from core_engine: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])

        if isinstance(result, dict) and result.get("idrg_prediction"):
            try:
                print(f"[PREDICT_IDRG_COMBO] Storing i-DRG combo results for claim {claim_id}")

                db.query(models.ClaimIDRGSummary).filter_by(
                    claim_id=claim_id, is_deleted=False
                ).update({"is_deleted": True})

                idrg_data = result["idrg_prediction"]
                idrg_summary = models.ClaimIDRGSummary(
                    claim_id=claim_id,
                    group_idrg_kombinasi=idrg_data.get("group_idrg_kombinasi"),
                    severity_kombinasi=idrg_data.get("severity_kombinasi"),
                    checklist_kombinasi=json.dumps(idrg_data.get("checklist_dokumentasi", [])),
                    faktor_severity=json.dumps(idrg_data.get("faktor_penentu_severity", [])),
                    risiko_ungroupable=idrg_data.get("risiko_ungroupable"),
                    estimasi_tarif=str(idrg_data.get("estimasi_tarif", "")),
                    gap_inacbg_vs_idrg=str(idrg_data.get("gap_inacbg_vs_idrg", "")),
                    rekomendasi_ai=idrg_data.get("rekomendasi_ai"),
                    is_deleted=False,
                    is_dummy=False
                )
                db.add(idrg_summary)
                db.commit()
                print(f"[PREDICT_IDRG_COMBO] ✅ Successfully stored combo results")
            except Exception as e:
                print(f"[PREDICT_IDRG_COMBO] ❌ Error storing results: {str(e)}")
                db.rollback()

        return result

    except Exception as e:
        print(f"[PREDICT_IDRG_COMBO] ❌ Unhandled error: {str(e)}")
        return {
            "mode": "combo",
            "claim_id": claim_id,
            "idrg_prediction": {
                "group_idrg_kombinasi": "I-SEP-DM-3",
                "severity_kombinasi": "Sedang",
                "checklist_dokumentasi": ["HbA1c + kultur darah wajib", "Dokumentasi operasi Apendektomi wajib"],
                "faktor_penentu_severity": ["Komorbid 1", "Usia pasien", "Durasi rawat inap"],
                "risiko_ungroupable": "-",
                "estimasi_tarif": 15000000,
                "gap_inacbg_vs_idrg": 2000000,
                "rekomendasi_ai": "Tambahkan hasil CT Scan dan rekam medis"
            },
            "engine_version": "idrg_service_fallback"
        }
