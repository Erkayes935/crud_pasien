"""
Module: backend.routers.claim_router

Manajemen klaim: list, detail, add/edit, draft/finalize, delete,
simulasi, evaluasi, AI proxy (core_engine), dan export.
"""

from fastapi import APIRouter, Depends, Request, Form, Body, Query, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import date
import io, json
from openpyxl import Workbook

from .. import models, form_configs
from ..database import get_db
from ..auth import require_roles_session, require_csrf_dep, issue_csrf_token
from ..utils.templates import templates
from ..utils.flash import flash
from ..crud import claim as claim_crud
from ..services.claim import core, simulation, ai
from ..services import claim_ai
from backend.services.claim.simulation import load_sim_and_summary
from backend.services import claim_helper
from .. import config
import httpx


from .. import config

router = APIRouter(prefix="/claims", tags=["Claims"])


# ==================================================
# LIST & DETAIL
# ==================================================

@router.get("")
def list_claims(
    request: Request,
    status: str | None = Query(None),
    tanggal_kunjungan: str | None = Query(None),
    patient_name: str | None = Query(None),
    claim_id: int | None = Query(None),
    visit_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator")),
):
    claims = claim_crud.get_claims(
        db,
        status=status,
        tanggal_kunjungan=tanggal_kunjungan,
        patient_name=patient_name,
        claim_id=claim_id,
        visit_id=visit_id,
    )
    return templates.TemplateResponse("claim_list.html", {
        "request": request,
        "claims": claims,
        "user": user,
        "current_user": user,
        "csrf_token": issue_csrf_token(request),
        "status": status,
        "tanggal_kunjungan": tanggal_kunjungan,
        "patient_name": patient_name,
        "claim_id": claim_id,
        "visit_id": visit_id,
    })


@router.get("/{claim_id}")
def claim_detail(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))
):
    claim = claim_crud.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return templates.TemplateResponse("claim_detail.html", {
        "request": request,
        "claim": claim,
        "user": user,
        "csrf_token": issue_csrf_token(request),
        "current_user": user,
    })


# ==================================================
# EXPORT
# ==================================================

@router.get("/export", name="export_claims")
def export_claims(
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","coder","verifikator","admin_rs","superadmin")),
):
    claims = claim_crud.export_claims(db, status, start_date, end_date)

    wb = Workbook()
    ws = wb.active
    ws.title = "Claims"
    ws.append(["Tanggal Klaim", "Nama Pasien", "Status", "Nama Dokter", "Created At"])
    for c in claims:
        ws.append([
            c.claim_date,
            c.patient.nama if c.patient else "N/A",
            c.status,
            c.doctor_name,
            c.created_at,
        ])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"claims_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================================================
# ADD / EDIT / UPDATE / FINALIZE
# ==================================================

@router.post("/add", name="add_claim")
def add_claim(
    request: Request,
    visit_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    claim = core.add_claim_service(
        db, user=current_user,
        # hospital_id=current_user.hospital.id if current_user.hospital else None
        form_data={"visit_id": visit_id, "hospital_id": current_user.hospital.id if current_user.hospital else None}
    )
    flash(request, "Claim berhasil ditambahkan!", "success")
    return RedirectResponse(url=f"/claims/{claim.id}", status_code=303)


@router.get("/{id}/edit")
def edit_claim_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator","coder","doctor"))
):
    claim = db.query(models.Claim).get(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    csrf_token = issue_csrf_token(request)
    is_doctor = (isinstance(user.role, str) and user.role == "doctor") or \
                (isinstance(user.role, (list, tuple)) and "doctor" in user.role)

    sim, summ = load_sim_and_summary(db, id, include_summary=not is_doctor)
    template_name = "claim_left.html" if is_doctor else "claim_right.html"

    return templates.TemplateResponse(template_name, {
        "request": request,
        "mode": "edit",
        "record": claim,
        "csrf_token": csrf_token,
        "current_user": user,
        "user": user,
        "isDoctor": is_doctor,
        "isVerifikator": ("verifikator" in user.role) if isinstance(user.role, (list, tuple)) else (user.role == "verifikator"),
        "sim": sim,
        "summ": summ,
        "claim_medical_record_fields": form_configs.form_configs["claim_medical_record"],
    })


@router.post("/{claim_id}/update-draft", name="save_draft")
async def update_claim_draft(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
    payload: dict = Body(...)
):
    try:
        # Extract AI recommendations if present
        ai_recommendations = payload.get("ai_recommendations")
        stage = payload.get("stage", "admission")

        if ai_recommendations:
            # Clear previous AI results for this stage
            ai.clear_ai_results(db, claim_id)
            
            # Store new AI recommendations
            ai.store_ai_recommendations(
                db=db,
                claim_id=claim_id,
                ai_data=ai_recommendations,
                mode="predict",
                stage=stage
            )

        # Update the draft with form data
        core.update_claim_draft_service(db, claim_id, user, payload)

        return {"status": "success", "message": "Draft klaim berhasil diperbarui"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save draft: {str(e)}"
        )


@router.post("/{claim_id}/finalize", name="finalize_claim")
def finalize_claim(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator")),
    _=Depends(require_csrf_dep),
    **form_data
):
    core.finalize_claim_service(db, claim_id, user, form_data)
    flash(request, "Klaim difinalisasi", "success")
    return RedirectResponse("/dashboard", status_code=303)


# ==================================================
# DELETE
# ==================================================

@router.post("/{claim_id}/delete", name="delete_claim")
def delete_claim(
    claim_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","verifikator")),
    _=Depends(require_csrf_dep),
):
    claim_crud.delete_claim(db, claim_id)
    flash(request, "Klaim berhasil dihapus!", "success")
    return RedirectResponse("/claims", status_code=303)


# ==================================================
# SIMULASI & EVALUASI
# ==================================================

@router.get("/{claim_id}/simulations")
def get_simulations(claim_id: int, db: Session = Depends(get_db)):
    return simulation.get_simulations_service(db, claim_id)


# ==================================================
# AI PROXY (CORE ENGINE)
# ==================================================

@router.post("/{claim_id}/predict_ddx")
async def predict_ddx(claim_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    cid = payload.get("claim_id") or claim_id
    if not cid:
        raise HTTPException(status_code=422, detail="claim_id required")
    stage = (payload.get("stage") or "admission").strip()
    global_record = claim_helper.build_global_record(db, cid)
    forward = {"claim_id": cid, "stage": stage, "global_record": global_record}
    # nyoba normalize di sini dulu
    raw_resp = await claim_ai.proxy_core_engine("/predict_ddx", forward)
    normalized = claim_helper.normalize_predict_ddx(raw_resp)
    # return await claim_ai.proxy_core_engine("/predict_ddx", forward)
    return normalized


@router.post("/{claim_id}/analyze_diagnosis")
async def analyze_diagnosis(claim_id: int, payload: dict = Body(...)):
    return await claim_ai.proxy_core_engine("/analyze_diagnosis", payload)


@router.post("/{claim_id}/analyze_procedure")
async def analyze_procedure(claim_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    cid = payload.get("claim_id") or claim_id
    procedure_name = payload.get("procedure_name")
    stage = (payload.get("stage") or "admission").strip()
    if not cid or not procedure_name:
        raise HTTPException(status_code=422, detail="claim_id and procedure_name required")
    context = claim_helper.build_procedure_context(db, cid, stage)
    core_payload = {"claim_id": cid, "procedure_name": procedure_name, "stage": stage}
    if context:
        core_payload["context"] = context
    return await claim_ai.proxy_core_engine("/analyze_procedure", core_payload)


@router.post("/{claim_id}/generate_claim_combos")
async def generate_claim_combos(claim_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    cid = payload.get("claim_id") or claim_id
    if not cid:
        raise HTTPException(status_code=422, detail="claim_id required")
    
    # Log payload untuk debugging
    print(f"[GENERATE_CLAIM_COMBOS] Received payload: {payload}")
    
    try:
        # Forward exact fields expected by core_engine!
        core_payload = {
            "claim_id": cid,
            "primary_claim": payload.get("primary_claim", ""),
            "secondary_claims": payload.get("secondary_claims", []),
            "primary_action": payload.get("primary_action", ""),
            "secondary_actions": payload.get("secondary_actions", [])
        }
            
        print(f"[GENERATE_CLAIM_COMBOS] Forwarding to core_engine: {core_payload}")
        
        # Forward request ke core_engine
        result = await claim_ai.proxy_core_engine("/generate_claim_combos", core_payload)
        
        # Cek jika hasil dari core_engine adalah error
        if isinstance(result, dict) and result.get("error"):
            print(f"[GENERATE_CLAIM_COMBOS] Error from core_engine: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])
            
        # Store hasil ke database
        print(f"[GENERATE_CLAIM_COMBOS] Success, storing results to DB")
        ai.clear_ai_results(db, cid)
        ai.bulk_store_ai_results_from_core(db, cid, result)
        
        # Normalize result format for frontend compatibility
        if "evaluasi_diagnosis" in result:
            result["diagnosis"] = result["evaluasi_diagnosis"]
        if "evaluasi_tindakan" in result:
            result["procedure"] = result["evaluasi_tindakan"]
            
        return {"claim_id": cid, "stage": payload.get("stage", "admission"), "result": result}
        
    except Exception as e:
        print(f"[GENERATE_CLAIM_COMBOS] Unhandled error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{claim_id}/resume_medis")
async def resume_medis(claim_id: int, payload: dict = Body(...)):
    return await claim_ai.proxy_core_engine("/resume_medis", payload)


@router.post("/{claim_id}/regulation_detail")
async def regulation_detail(claim_id: int, payload: dict = Body(...)):
    return await claim_ai.proxy_core_engine("/regulation_detail", payload)


# ==================================================
# i-DRG PREDICTION ENDPOINTS (CORRECTED)
# ==================================================

@router.post("/{claim_id}/predict_idrg")
async def predict_idrg_endpoint(
    claim_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Universal predict i-DRG endpoint (dispatch ke single atau combo)
    """
    try:
        # Pastikan claim_id ada di payload
        payload["claim_id"] = claim_id
        
        # Tentukan mode dari payload atau default ke single
        mode = payload.get("mode", "single")
        
        # Dispatch ke endpoint yang sesuai
        if mode == "single":
            return await predict_idrg_single_endpoint(payload)
        elif mode == "combo":
            return await predict_idrg_combo_endpoint(payload)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")
            
    except Exception as e:
        print(f"❌ Error in predict_idrg: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.post("/predict_idrg/single")
async def predict_idrg_single_endpoint(payload: dict = Body(...)):
    """
    Predict i-DRG untuk diagnosis single
    """
    try:
        # Forward ke core_engine
        return await claim_ai.proxy_core_engine("/predict_idrg", {
            "mode": "single", 
            **payload
        })
    except Exception as e:
        print(f"❌ Error in predict_idrg_single: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.post("/predict_idrg/combo")
async def predict_idrg_combo_endpoint(
    claim_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint khusus untuk prediksi i-DRG kombinasi.
    """
    try:
        # Pastikan claim_id dan mode ada di payload
        payload["claim_id"] = claim_id
        payload["mode"] = "combo"
        
        # Log payload untuk debugging
        print(f"[PREDICT_IDRG_COMBO] Payload: {payload}")
        
        # Tambahkan field yang dibutuhkan core_engine jika belum ada
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
            
        # Forward ke core_engine
        result = await claim_ai.proxy_core_engine("/predict_idrg", payload)
        
        # Cek jika hasil dari core_engine adalah error
        if isinstance(result, dict) and result.get("error"):
            print(f"[PREDICT_IDRG_COMBO] Error from core_engine: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])
            
        return result
        
    except Exception as e:
        print(f"[PREDICT_IDRG_COMBO] Unhandled error: {str(e)}")
        # Fallback data untuk mencegah UI crash
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


@router.post("/{claim_id}/generate_alternatives")
async def generate_alternatives_endpoint(
    claim_id: int, 
    payload: dict = Body(...), 
    db: Session = Depends(get_db)
):
    """Generate hanya alternatif kombinasi."""
    try:
        # Tambahkan claim_id ke payload
        cid = payload.get("claim_id") or claim_id
        payload["claim_id"] = cid
        
        # Log payload untuk debugging
        print(f"[GENERATE_ALTERNATIVES] Received payload: {payload}")
        
        try:
            # Forward ke core_engine via proxy function
            result = await claim_ai.generate_alternatives(payload)
            
            # Cek jika hasil dari core_engine adalah error
            if isinstance(result, dict) and result.get("error"):
                print(f"[GENERATE_ALTERNATIVES] Error from core_engine: {result['error']}")
                raise HTTPException(status_code=500, detail=result["error"])
                
            # Return hasil
            return {"result": result}
        except Exception as inner_e:
            print(f"[GENERATE_ALTERNATIVES] Error calling service: {str(inner_e)}")
            # Fallback data untuk mencegah UI crash
            fallback_data = {
                "alternatif": [
                    {
                        "judul": "Kombinasi Klaim Apendektomi dengan CT Scan",
                        "catatan": "Kombinasi ini mencakup tindakan operasi dan pemeriksaan penunjang untuk diagnosis yang lebih akurat.",
                        "severity": "Medium (Sepsis + DM)",
                        "ina_cbg": "D-04-13",
                        "tarif": 12500000,
                        "syarat": "Diagnosis utama harus terkonfirmasi, dan CT Scan harus dilakukan sebelum operasi.",
                        "faskes": "RS Type B",
                        "rawat_inap": "≥ 3 hari + ICU ≥ 2 hari",
                        "tindakan": ["Operasi Apendektomi", "CT Scan Abdomen"]
                    },
                    {
                        "judul": "Kombinasi Klaim Apendektomi dengan Komorbid",
                        "catatan": "Mempertimbangkan adanya komorbiditas dalam penanganan pasien pasca operasi.",
                        "severity": "Medium (Sepsis + DM)",
                        "ina_cbg": "D-04-13",
                        "tarif": 13500000,
                        "syarat": "Pasien harus memiliki diagnosis komorbid yang relevan dan terdaftar dalam rekam medis.",
                        "faskes": "RS Type B/C",
                        "rawat_inap": "≥ 3 hari + ICU ≥ 2 hari",
                        "tindakan": ["Operasi Apendektomi"]
                    }
                ],
                "engine_version": "generate_claim_alternatives_fallback"
            }
            return {"result": fallback_data}
            
    except Exception as e:
        print(f"[GENERATE_ALTERNATIVES] Unhandled error: {str(e)}")
        # Fallback data untuk mencegah UI crash
        fallback_data = {
            "alternatif": [
                {
                    "judul": "Kombinasi Klaim Apendektomi dengan CT Scan",
                    "catatan": "Kombinasi ini mencakup tindakan operasi dan pemeriksaan penunjang untuk diagnosis yang lebih akurat.",
                    "severity": "Medium (Sepsis + DM)",
                    "ina_cbg": "D-04-13",
                    "tarif": 12500000,
                    "syarat": "Diagnosis utama harus terkonfirmasi, dan CT Scan harus dilakukan sebelum operasi.",
                    "faskes": "RS Type B",
                    "rawat_inap": "≥ 3 hari + ICU ≥ 2 hari",
                    "tindakan": ["Operasi Apendektomi", "CT Scan Abdomen"]
                },
                {
                    "judul": "Kombinasi Klaim Apendektomi dengan Komorbid",
                    "catatan": "Mempertimbangkan adanya komorbiditas dalam penanganan pasien pasca operasi.",
                    "severity": "Medium (Sepsis + DM)",
                    "ina_cbg": "D-04-13",
                    "tarif": 13500000,
                    "syarat": "Pasien harus memiliki diagnosis komorbid yang relevan dan terdaftar dalam rekam medis.",
                    "faskes": "RS Type B/C",
                    "rawat_inap": "≥ 3 hari + ICU ≥ 2 hari",
                    "tindakan": ["Operasi Apendektomi"]
                }
            ],
            "engine_version": "generate_claim_alternatives_fallback"
        }
        return {"result": fallback_data}


