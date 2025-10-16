"""
Module: backend.routers.claim_router

Manajemen klaim dengan workflow: Doctor -> Coder -> Verifikator
Fixed: Alur data dari coder ke verifikator
"""

from fastapi import (
    APIRouter, Depends, Request, Form, Body, Query, HTTPException, File, UploadFile
)
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import io
import json
import os
import uuid
from openpyxl import Workbook

from .. import models, form_configs
from ..database import get_db
from ..auth import require_roles_session, require_csrf_dep, issue_csrf_token
from ..utils.templates import templates
from ..utils.flash import flash
from ..utils.dummy_data import make_dummy, dummy_diagnosis_list, dummy_diagnosis_detail, dummy_tindakan_list, dummy_tindakan_detail
from ..crud import claim as claim_crud
from ..crud import claim_note as note_crud
from ..services.claim import core, simulation, ai
from ..services import claim_ai, claim_helper
from backend.services.claim.simulation import load_sim_and_summary, load_existing_mappings, apply_mappings_to_simulasi

router = APIRouter(prefix="/claims", tags=["Claims"])


# ==================================================
# EXPORT
# ==================================================

@router.get("/export", name="export_claims")
def export_claims(
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """Ekspor data klaim ke Excel dengan tampilan rapi untuk user."""
    claims = db.query(models.Claim).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Data Klaim"

    headers = [
        "ID Klaim", "Tanggal Klaim", "Nama Pasien", "No. RM", "Rumah Sakit",
        "Dokter", "Status", "Workflow Status", "Final", "Total Diagnosis", "Total Tindakan",
        "ICD10 Utama", "ICD9 Utama", "Status Verifikasi", "Verified By Coder", "Dibuat"
    ]
    ws.append(headers)

    for c in claims:
        data = c.to_export_dict()
        ws.append([data.get(h, "") for h in headers])

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
# LIST & DETAIL (WITH ROLE-BASED FILTERING)
# ==================================================

from typing import Optional

@router.get("")
def list_claims(
    request: Request,
    status: Optional[str] = Query(None),
    tanggal_kunjungan: Optional[str] = Query(None),
    patient_name: Optional[str] = Query(None),
    claim_id: Optional[str] = Query(None),   # ubah ke str agar aman parse manual
    visit_id: Optional[str] = Query(None),   # ubah ke str juga
    workflow_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "admin_rs", "superadmin", "coder", "verifikator")),
):
    """List klaim dengan filter berdasarkan role"""

    query = db.query(models.Claim)

    # ✅ ROLE-BASED FILTERING
    roles = user.role_names or []

    if "verifikator" in roles and "coder" not in roles and "doctor" not in roles:
        query = query.filter(
            models.Claim.workflow_status.in_(["coder_verified", "verifikator_review", "finalized"])
        )
    elif "coder" in roles and "verifikator" not in roles and "doctor" not in roles:
        query = query.filter(
            models.Claim.workflow_status.in_(["doctor_submitted", "coder_review", "coder_verified"])
        )
    elif "doctor" in roles and "coder" not in roles and "verifikator" not in roles:
        query = query.filter(models.Claim.doctor_id == user.id)

    # ✅ NORMALIZE EMPTY STRINGS TO NONE
    if claim_id == "":
        claim_id = None
    if visit_id == "":
        visit_id = None
    if tanggal_kunjungan == "":
        tanggal_kunjungan = None
    if patient_name == "":
        patient_name = None
    if workflow_status == "":
        workflow_status = None
    if status == "":
        status = None

    # ✅ Apply additional filters
    if status:
        query = query.filter(models.Claim.status == status)
    if workflow_status:
        query = query.filter(models.Claim.workflow_status == workflow_status)
    if tanggal_kunjungan:
        query = query.filter(models.Claim.tanggal_kunjungan == tanggal_kunjungan)
    if patient_name:
        query = query.filter(models.Claim.patient_name.ilike(f"%{patient_name}%"))
    if claim_id and str(claim_id).isdigit():
        query = query.filter(models.Claim.id == int(claim_id))
    if visit_id and str(visit_id).isdigit():
        query = query.filter(models.Claim.visit_id == int(visit_id))

    claims = query.order_by(models.Claim.created_at.desc()).all()

    return templates.TemplateResponse(
        "claim_list.html",
        {
            "request": request,
            "claims": claims,
            "user": user,
            "current_user": user,
            "csrf_token": issue_csrf_token(request),
            "status": status,
            "workflow_status": workflow_status,
            "tanggal_kunjungan": tanggal_kunjungan,
            "patient_name": patient_name,
            "claim_id": claim_id,
            "visit_id": visit_id,
        },
    )


# ==================================================
# GROUP (EPISODE KLAIM)
# ==================================================
@router.get("/select-group")
def select_group_page(
    request: Request,
    patient_id: int = Query(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """Halaman memilih group klaim: buat baru atau lanjut yang sudah ada"""
    groups = db.query(models.ClaimGroup).filter_by(patient_id=patient_id).all()
    csrf_token = issue_csrf_token(request)

    return templates.TemplateResponse(
        "claim_group_select.html",
        {
            "request": request,
            "groups": groups,
            "patient_id": patient_id,
            "csrf_token": csrf_token,
            "user": user,              # ✅ penting untuk navbar
            "current_user": user,      # ✅ konsisten dengan halaman lain
        },
    )


@router.get("/select-visit")
def select_visit_page(
    request: Request,
    group_id: int = Query(...),
    patient_id: int = Query(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
):
    """Halaman memilih kunjungan (visit) untuk klaim baru di episode tertentu"""
    visits = (
        db.query(models.Visit)
        .filter(models.Visit.patient_id == patient_id)
        .order_by(models.Visit.tanggal_kunjungan.desc())
        .all()
    )
    group = db.query(models.ClaimGroup).get(group_id)
    csrf_token = issue_csrf_token(request)

    return templates.TemplateResponse("claim_visit_select.html", {
        "request": request,
        "group": group,
        "visits": visits,
        "csrf_token": csrf_token,
        "patient_id": patient_id,
        "flow": "claim",            # 🧩 inilah kunci yang hilang
        "current_user": user,       # opsional tapi aman untuk template
        "user": user,
    })

@router.get("/group/{group_id}", name="group_detail")
def group_detail_page(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """Halaman detail 1 Group (Episode Klaim)"""
    group = db.query(models.ClaimGroup).get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group tidak ditemukan")

    # Ambil semua klaim dalam group ini
    claims = (
        db.query(models.Claim)
        .filter(models.Claim.group_id == group_id)
        .order_by(models.Claim.created_at.desc())
        .all()
    )

    # Hitung ringkasan status
    total_klaim = len(claims)
    selesai = len([c for c in claims if c.workflow_status == "finalized"])
    belum = total_klaim - selesai

    csrf_token = issue_csrf_token(request)

    return templates.TemplateResponse(
        "claim_group_detail.html",
        {
            "request": request,
            "group": group,
            "claims": claims,
            "user": user,
            "current_user": user,
            "csrf_token": csrf_token,
            "total_klaim": total_klaim,
            "selesai": selesai,
            "belum": belum,
        },
    )


@router.get("/{claim_id}")
def claim_detail(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "admin_rs", "superadmin", "coder", "verifikator")),
):
    claim = claim_crud.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Load coder verification results if available
    coder_results = db.query(models.ClaimSimulation).filter(
        models.ClaimSimulation.claim_id == claim_id,
        models.ClaimSimulation.coder_verified == True
    ).all()
    
    # Load approved mappings for verificator (if user is verificator)
    approved_mappings = {}
    user_roles = user.role_names if hasattr(user, 'role_names') else [user.role] if user.role else []
    
    if "verifikator" in user_roles:
        from ..services.claim import simulation as sim_service
        approved_mappings = sim_service.get_simulations_for_verificator(db, claim_id)
    
    return templates.TemplateResponse("claim_detail.html", {
        "request": request,
        "claim": claim,
        "user": user,
        "csrf_token": issue_csrf_token(request),
        "current_user": user,
        "coder_results": coder_results,
        "approved_mappings": approved_mappings,  # ✅ New: Untuk verificator
    })


# ==================================================
# ADD / EDIT / UPDATE / FINALIZE
# ==================================================

@router.post("/create-group")
def create_group(
    request: Request,
    patient_id: int = Form(...),
    nama_group_baru: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    """Buat group (episode) baru"""
    hospital_id = getattr(user.hospital, "id", None)
    kode_group = f"E{int(datetime.now().timestamp())}"  # contoh kode: E1739412934
    group = models.ClaimGroup(
        kode_group=kode_group,
        nama_group=nama_group_baru or f"Episode {kode_group}",
        patient_id=patient_id,
        hospital_id=hospital_id,
        created_by=user.name
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    flash(request, f"✅ Group baru '{group.nama_group}' berhasil dibuat", "success")
    return RedirectResponse(
        url=f"/claims/select-group?patient_id={patient_id}", status_code=303
    )


@router.post("/add", name="add_claim")
def add_claim(
    request: Request,
    visit_id: int = Form(...),
    group_id: Optional[int] = Form(None),
    nama_group_baru: Optional[str] = Form(None),
    patient_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    """
    Tambah klaim baru:
    - Jika group_id dikirim → klaim masuk ke group tersebut
    - Jika tidak ada → buat group baru
    """
    hospital_id = getattr(current_user.hospital, "id", None)

    # 🔹 Pastikan group tersedia
    group = None
    if group_id:
        group = db.query(models.ClaimGroup).get(group_id)
    elif nama_group_baru and patient_id:
        kode_group = f"E{int(datetime.now().timestamp())}"
        group = models.ClaimGroup(
            kode_group=kode_group,
            nama_group=nama_group_baru,
            patient_id=patient_id,
            hospital_id=hospital_id,
            created_by=current_user.name,
        )
        db.add(group)
        db.commit()
        db.refresh(group)

    if not group:
        flash(request, "⚠️ Harus memilih atau membuat Group terlebih dahulu", "error")
        return RedirectResponse(url="/claims/select-group", status_code=303)

    # 🔹 Buat klaim baru
    claim = core.add_claim_service(db, visit_id, current_user, hospital_id)
    if not claim:
        raise HTTPException(status_code=400, detail="Visit ID tidak valid atau tidak ditemukan.")

    claim.group_id = group.id
    claim.workflow_status = "draft"
    db.commit()

    flash(request, f"✅ Klaim berhasil ditambahkan ke Group {group.kode_group}", "success")
    return RedirectResponse(url=f"/claims/{claim.id}", status_code=303)


@router.get("/{claim_id}/edit")
def edit_claim_form(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator", "coder", "doctor")),
):
    """Form edit klaim dinamis berdasarkan role dengan workflow tracking"""
    
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    csrf_token = issue_csrf_token(request)

    # Get user roles
    roles = user.role_names or []
    has_doctor = "doctor" in roles
    has_coder = "coder" in roles
    has_verifikator = "verifikator" in roles

    # Count total roles
    total_roles = sum([has_doctor, has_coder, has_verifikator])
    
    # WORKFLOW VALIDATION (skip for multi-role users)
    current_workflow = claim.workflow_status or "draft"
    
    # Multi-role users can bypass workflow checks
    if total_roles == 1:  # Single role user
        if has_doctor and current_workflow not in ["draft", "doctor_submitted"]:
            flash(request, "⚠️ Klaim sudah masuk ke tahap coder/verifikator", "warning")
            return RedirectResponse(url=f"/claims/{claim_id}", status_code=303)
        
        if has_coder and current_workflow not in ["doctor_submitted", "coder_review", "coder_verified"]:
            flash(request, "⚠️ Klaim belum siap untuk review coder atau sudah selesai", "warning")
            return RedirectResponse(url=f"/claims/{claim_id}", status_code=303)
        
        if has_verifikator and current_workflow not in ["coder_verified", "verifikator_review"]:
            flash(request, "⚠️ Klaim belum diverifikasi coder", "warning")
            return RedirectResponse(url=f"/claims/{claim_id}", status_code=303)
    else:
        # Multi-role: No workflow restriction
        print(f"✅ Multi-role user {user.name} - bypassing workflow checks")

    # TEMPLATE SELECTION
    if total_roles > 1:
        # Multi-role: Combine view (doctor left + verifikator right)
        template_name = "claim_combine.html"
        print(f"🎯 Using combined template for multi-role user")
    elif has_verifikator:
        template_name = "claim_right.html"
    elif has_coder:
        template_name = "edit_coder.html"
    elif has_doctor:
        template_name = "claim_left.html"
    else:
        template_name = "claim_right.html"  # fallback

    # Load simulation & summary
    sim, summ = load_sim_and_summary(db, claim_id, include_summary=not has_doctor or total_roles > 1)

    # Load medical record data
    existing_medical_data = {}
    if claim.medical_record_id:
        medical_record = db.query(models.MedicalRecord).get(claim.medical_record_id)
        if medical_record:
            for field in form_configs.form_configs["claim_medical_record"]:
                fname = field.get("name")
                if fname and hasattr(medical_record, fname):
                    existing_medical_data[fname] = getattr(medical_record, fname)

    # Apply existing mappings to simulation
    existing_mappings = load_existing_mappings(db, claim_id)
    if existing_mappings and sim and "simulasi" in sim:
        sim["simulasi"] = apply_mappings_to_simulasi(sim["simulasi"], existing_mappings)

    # Load coder results for verifikator
    coder_results = None
    if has_verifikator or total_roles > 1:
        coder_results = db.query(models.ClaimSimulation).filter(
            models.ClaimSimulation.claim_id == claim_id,
            models.ClaimSimulation.coder_verified == True
        ).all()

    # Base context
    context = {
        "request": request,
        "mode": "edit",
        "record": claim,
        "csrf_token": csrf_token,
        "current_user": user,
        "user": user,
        "roles": roles,
        "isDoctor": has_doctor,
        "isVerifikator": has_verifikator,
        "isCoder": has_coder,
        "isMultiRole": total_roles > 1,  # New flag for multi-role
        "sim": sim,
        "summ": summ,
        "claim_medical_record_fields": form_configs.form_configs["claim_medical_record"],
        "existing_medical_data": existing_medical_data,
        "coder_results": coder_results,
        "workflow_status": current_workflow,
    }

    # Special handling for coder template
    if template_name == "edit_coder.html":
        from ..services.claim import simulation as sim_service
        stages = sim_service.get_simulations_for_coder(db, claim_id)
        context["claim"] = claim
        context["stages"] = stages

    return templates.TemplateResponse(template_name, context)

@router.post("/{claim_id}/update-draft", name="save_draft")
async def update_claim_draft(
    request: Request,
    claim_id: int,
    payload: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    """Update draft klaim oleh dokter"""
    try:
        # Parse JSON payload
        payload_dict = json.loads(payload)

        ai_recommendations = payload_dict.get("ai_recommendations")
        stage = payload_dict.get("stage", "admission")

        if ai_recommendations:
            ai.clear_ai_results(db, claim_id)
            ai.store_ai_recommendations(
                db=db, claim_id=claim_id, ai_data=ai_recommendations, mode="predict", stage=stage
            )

        # simpan draft isi form & simulasi
        core.update_claim_draft_service(db, claim_id, user, payload_dict)

        # ✅ otomatis ubah workflow ke doctor_submitted agar coder bisa review
        claim = db.query(models.Claim).filter_by(id=claim_id).first()
        if claim:
            if claim.workflow_status in [None, "", "draft"]:
                claim.workflow_status = "doctor_submitted"
                claim.doctor_submitted_by = user.name
                claim.doctor_submitted_at = datetime.now()
                db.commit()

        return {"status": "success", "message": "Draft klaim berhasil diperbarui"}

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save draft: {str(e)}")


@router.post("/{claim_id}/submit-to-coder", name="submit_to_coder")
async def submit_to_coder(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    """Submit klaim ke coder setelah dokter selesai"""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Validasi: pastikan ada diagnosis
    simulations = db.query(models.ClaimSimulation).filter(
        models.ClaimSimulation.claim_id == claim_id
    ).count()
    
    if simulations == 0:
        flash(request, "⚠️ Minimal harus ada 1 diagnosis sebelum submit ke coder", "error")
        return RedirectResponse(url=f"/claims/{claim_id}/edit", status_code=303)
    
    # Update workflow status
    claim.workflow_status = "doctor_submitted"
    claim.doctor_submitted_at = datetime.now()
    claim.doctor_submitted_by = user.name
    db.commit()
    
    flash(request, "✅ Klaim berhasil disubmit ke Coder untuk verifikasi ICD", "success")
    return RedirectResponse(url="/claims", status_code=303)


@router.post("/{claim_id}/finalize", name="finalize_claim")
async def finalize_claim(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator")),
    _=Depends(require_csrf_dep),
):
    """
    Finalize klaim oleh verifikator.
    Multi-role user (doctor + verifikator) bisa BYPASS workflow coder.
    """
    form_data = await request.form()
    form_dict = dict(form_data)

    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Check user roles
    roles = user.role_names or []
    has_doctor = "doctor" in roles
    has_verifikator = "verifikator" in roles
    bypass_coder = has_doctor and has_verifikator

    # Validasi minimal diagnosis
    sim_count = db.query(models.ClaimSimulation).filter(
        models.ClaimSimulation.claim_id == claim_id
    ).count()
    if sim_count == 0:
        flash(request, "⚠️ Minimal harus ada 1 diagnosis/simulasi sebelum finalisasi", "error")
        return RedirectResponse(url=f"/claims/{claim_id}", status_code=303)

    # Workflow validation
    if not bypass_coder:
        # Normal flow: harus sudah coder_verified
        if claim.workflow_status != "coder_verified":
            flash(request, "⚠️ Klaim harus diverifikasi coder terlebih dahulu", "error")
            return RedirectResponse(url=f"/claims/{claim_id}", status_code=303)
    else:
        # BYPASS FLOW: Isi historis workflow untuk audit trail
        now = datetime.now()
        
        # Auto-fill doctor submission jika belum
        if not getattr(claim, "doctor_submitted_at", None):
            claim.doctor_submitted_at = now
            claim.doctor_submitted_by = user.name
        
        # Auto-fill coder verification (self-verify karena bypass)
        if not getattr(claim, "coder_verified_at", None):
            claim.coder_verified_at = now
            claim.coder_verified_by = f"{user.name} (bypass)"
        
        # Set workflow ke coder_verified sebelum finalize
        claim.workflow_status = "coder_verified"
        db.commit()  # Commit intermediate state
        
        print(f"✅ BYPASS MODE: User {user.name} has both doctor+verifikator roles")

    # Execute finalize service
    try:
        core.finalize_claim_service(db, claim_id, user, form_dict)
    except Exception as e:
        flash(request, f"⚠️ Gagal finalize klaim: {str(e)}", "error")
        return RedirectResponse(url=f"/claims/{claim_id}", status_code=303)

    # Update final status
    claim.workflow_status = "finalized"
    claim.finalized_at = datetime.now()
    claim.finalized_by = user.name
    db.commit()

    flash(request, "✅ Klaim berhasil difinalisasi", "success")
    return RedirectResponse("/dashboard", status_code=303)
# ==================================================
# DELETE
# ==================================================

@router.post("/{claim_id}/delete", name="delete_claim")
def delete_claim(
    claim_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "verifikator", "admin_rs", "superadmin")),
    _=Depends(require_csrf_dep),
):
    claim = db.query(models.Claim).get(claim_id)
    if claim:
        # Hanya doctor yang buat atau admin yang bisa delete
        if "doctor" in user.role_names:
            if claim.created_by != user.name:
                flash(request, "⚠️ Anda hanya bisa menghapus klaim yang Anda buat", "error")
                return RedirectResponse("/claims", status_code=303)
    
    claim_crud.delete_claim(db, claim_id)
    flash(request, "Klaim berhasil dihapus!", "success")
    return RedirectResponse("/claims", status_code=303)


@router.post("/add-multi", name="add_claim_multi")
def add_claim_multi(
    request: Request,
    patient_id: int = Form(...),
    visit_ids: list[str] = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    """Buat klaim baru dengan beberapa kunjungan (multi-visit grouping)"""
    print("🩺 ADD_CLAIM_MULTI: visits =", visit_ids)
    hospital_id = getattr(current_user.hospital, "id", None)

    if not visit_ids:
        raise HTTPException(status_code=400, detail="Minimal 1 kunjungan harus dipilih")

    # Visit pertama sebagai visit utama
    main_visit_id = int(visit_ids[0])
    claim = core.add_claim_service(db, main_visit_id, current_user, hospital_id)
    if not claim:
        raise HTTPException(status_code=400, detail="Visit utama tidak valid.")

    # Set workflow status
    claim.workflow_status = "draft"

    # Tambahkan kunjungan tambahan
    for vid in visit_ids[1:]:
        link = models.ClaimVisitLink(
            claim_id=claim.id,
            external_visit_id=str(vid),
            hospital_id=hospital_id,
        )
        db.add(link)

    db.commit()
    flash(request, f"✅ Klaim berhasil dibuat dengan {len(visit_ids)} kunjungan", "success")
    return RedirectResponse(url=f"/claims/{claim.id}", status_code=303)


# ==================================================
# SIMULASI & EVALUASI
# ==================================================

@router.get("/{claim_id}/simulations")
def get_simulations(claim_id: int, db: Session = Depends(get_db)):
    return simulation.get_simulations_service(db, claim_id)


# ==================================================
# CODER (VERSI FIXED)
# ==================================================

from ..services.claim import simulation as sim_service

@router.get("/{claim_id}/coder", response_class=HTMLResponse)
def coder_review_page(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("coder")),
):
    """Halaman verifikasi ICD oleh coder"""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Validasi workflow
    if claim.workflow_status not in ["doctor_submitted", "coder_review", "coder_verified"]:
        flash(request, "⚠️ Klaim belum siap untuk review coder", "warning")
        return RedirectResponse(url="/claims", status_code=303)

    stages = sim_service.get_simulations_for_coder(db, claim_id)
    csrf_token = issue_csrf_token(request)

    return templates.TemplateResponse(
        "edit_coder.html",
        {
            "request": request,
            "claim": claim,
            "stages": stages,
            "user": user,
            "current_user": user,
            "csrf_token": csrf_token,
        },
    )


@router.post("/{claim_id}/coder")
async def coder_submit_verification(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("coder")),
    _=Depends(require_csrf_dep),
):
    """Simpan hasil verifikasi ICD coder dan update workflow"""
    form_data = await request.form()
    
    # Simpan verifikasi
    updated = sim_service.save_coder_verification(db, claim_id, form_data, user.name)
    
    # ✅ UPDATE WORKFLOW STATUS
    claim = db.query(models.Claim).get(claim_id)
    if claim:
        claim.workflow_status = "coder_verified"
        claim.coder_verified_at = datetime.now()
        claim.coder_verified_by = user.name
        db.commit()
    
    flash(request, f"✅ {updated} entri berhasil diverifikasi oleh coder. Klaim siap untuk verifikator.", "success")
    return RedirectResponse(url="/claims", status_code=303)


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
    
    raw_resp = await claim_ai.proxy_core_engine("/predict_ddx", forward)
    normalized = claim_helper.normalize_predict_ddx(raw_resp)

    try:
        print(f"[PREDICT_DDX] Storing AI results for claim {cid}, stage {stage}")
        ai.clear_ai_results(db, cid)
        
        # ✅ CLEAR EXISTING MAPPINGS saat generate AI ulang
        print(f"[PREDICT_DDX] Clearing existing mappings to prevent duplicates...")
        from backend.services.claim.simulation import models
        
        # Clear existing ClaimSimulation mappings
        deleted_sims = db.query(models.ClaimSimulation).filter(models.ClaimSimulation.claim_id == cid).delete()
        
        # Clear mapped diagnoses & procedures (yang dari mapping, bukan AI original)
        deleted_diags = db.query(models.ClaimDiagnosis).filter(
            models.ClaimDiagnosis.claim_id == cid,
            models.ClaimDiagnosis.diagnosis_type.in_(["Diagnosis Utama", "Komorbid", "Komplikasi", "Primary", "Secondary"])
        ).delete(synchronize_session=False)
        
        deleted_procs = db.query(models.ClaimProcedure).filter(
            models.ClaimProcedure.claim_id == cid,
            models.ClaimProcedure.procedure_type.in_(["Primary", "Secondary", "Primary Action", "Secondary Actions"])
        ).delete(synchronize_session=False)
        
        print(f"[PREDICT_DDX] ✅ Cleared existing mappings: {deleted_sims} simulations, {deleted_diags} diagnoses, {deleted_procs} procedures")
        
        ai.store_ai_recommendations(db, cid, normalized, "predict", stage)
        db.commit()
        print(f"[PREDICT_DDX] Successfully stored AI results with clean mappings")
    except Exception as e:
        print(f"[PREDICT_DDX] Error storing results: {str(e)}")
        db.rollback()
    return normalized


@router.post("/{claim_id}/analyze_diagnosis")
async def analyze_diagnosis(claim_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    result = await claim_ai.proxy_core_engine("/analyze_diagnosis", payload)
    
    try:
        print(f"[ANALYZE_DIAGNOSIS] Storing analysis results for claim {claim_id}")
        stage = payload.get("stage", "admission")
        
        # ✅ Store diagnosis (existing functionality)
        ai.store_ai_recommendations(db, claim_id, result, "diagnosis", stage)
        
        # 🔥 NEW: Store tindakan yang muncul di modal detail diagnosis
        if "tindakan" in result and isinstance(result["tindakan"], list):
            print(f"[ANALYZE_DIAGNOSIS] Found {len(result['tindakan'])} procedures in modal, storing to database")
            
            for tindakan_item in result["tindakan"]:
                if not tindakan_item or not tindakan_item.get("name"):
                    continue
                    
                # Create ClaimProcedure entry
                procedure = models.ClaimProcedure(
                    claim_id=claim_id,
                    procedure_type="modal_diagnosis",  # Mark as procedure from modal diagnosis
                    procedure_text=tindakan_item.get("name", ""),
                    requirement_flag=False,  # Add required field
                    stage=stage,
                    is_deleted=False,
                    is_dummy=False,  # Add required field
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(procedure)
                db.flush()  # Get the ID
                
                # Create ClaimProcedureDetail if detailed info available
                if any(key in tindakan_item for key in ["icd9", "validitas", "status", "ina_cbg", "syarat_klinis"]):
                    # Find related ClaimSimulation or create temporary one
                    simulation = db.query(models.ClaimSimulation).filter_by(
                        claim_id=claim_id, stage=stage, is_deleted=False
                    ).first()
                    
                    if not simulation:
                        simulation = models.ClaimSimulation(
                            claim_id=claim_id,
                            stage=stage,
                            is_deleted=False,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        db.add(simulation)
                        db.flush()
                    
                    procedure_detail = models.ClaimProcedureDetail(
                        claim_simulation_id=simulation.id,
                        procedure_id=procedure.id,
                        icd9_tindakan=tindakan_item.get("icd9", ""),
                        validitas_tindakan=tindakan_item.get("validitas", ""),
                        status_tindakan=tindakan_item.get("status", ""),
                        ina_cbg_tindakan=tindakan_item.get("ina_cbg", ""),
                        syarat_klinis_tindakan=tindakan_item.get("syarat_klinis", ""),
                        is_deleted=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(procedure_detail)
                
                print(f"[ANALYZE_DIAGNOSIS] Stored procedure: {tindakan_item.get('name', 'Unknown')}")
        
        # 🔥 NEW: Store regulasi detail jika ada di response
        if "regulasi" in result and isinstance(result["regulasi"], list):
            print(f"[ANALYZE_DIAGNOSIS] Found {len(result['regulasi'])} regulation details, storing to database")
            
            for reg_item in result["regulasi"]:
                if not reg_item or not reg_item.get("judul"):
                    continue
                    
                regulation_detail = models.ClaimRegulationDetail(
                    claim_id=claim_id,
                    judul_regulasi=reg_item.get("judul", ""),
                    dasar_hukum=reg_item.get("dasar_hukum", ""),
                    bab_pasal=reg_item.get("bab_pasal", ""),
                    isi=reg_item.get("isi", ""),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(regulation_detail)
                print(f"[ANALYZE_DIAGNOSIS] Stored regulation: {reg_item.get('judul', 'Unknown')}")
        
        # 🔥 NEW: Store IDRG per diagnosis jika ada di response
        if "idrg_prediction" in result and isinstance(result["idrg_prediction"], dict):
            print(f"[ANALYZE_DIAGNOSIS] Found IDRG prediction, storing to claim_idrg_diagnosis")
            
            idrg_data = result["idrg_prediction"]
            # Check for existing IDRG for this diagnosis to avoid duplicates
            diagnosis_name = payload.get("diagnosis_name", "")
            existing_idrg = db.query(models.ClaimIDRGDiagnosis).filter_by(
                claim_id=claim_id,
                is_deleted=False
            ).filter(
                models.ClaimIDRGDiagnosis.group_idrg == idrg_data.get("group_idrg")
            ).first() if diagnosis_name else None
            
            if not existing_idrg:
                idrg_diagnosis = models.ClaimIDRGDiagnosis(
                    claim_id=claim_id,
                    group_idrg=idrg_data.get("group_idrg", ""),
                    severity_index=idrg_data.get("severity_index", ""),
                    checklist=json.dumps(idrg_data.get("checklist", {})) if idrg_data.get("checklist") else "",
                    faktor_severity=json.dumps(idrg_data.get("faktor_severity", {})) if idrg_data.get("faktor_severity") else "",
                    ungroupable_alert=idrg_data.get("ungroupable_alert", ""),
                    simulasi_tarif=str(idrg_data.get("simulasi_tarif", "")),
                    gap_analysis=idrg_data.get("gap_analysis", ""),
                    is_deleted=False,
                    is_dummy=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(idrg_diagnosis)
                print(f"[ANALYZE_DIAGNOSIS] Stored IDRG: {idrg_data.get('group_idrg', 'Unknown')}")
        
        db.commit()
        print(f"[ANALYZE_DIAGNOSIS] ✅ Successfully stored all analysis results including procedures and regulations")
    except Exception as e:
        print(f"[ANALYZE_DIAGNOSIS] ❌ Error storing results: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to store analysis results: {str(e)}")
    
    return result


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

    result = await claim_ai.proxy_core_engine("/analyze_procedure", core_payload)

    try:
        print(f"[ANALYZE_PROCEDURE] Storing analysis results for claim {cid} - procedure: {procedure_name}")
        
        # ✅ Store basic procedure info (existing functionality)
        ai.store_ai_recommendations(db, cid, result, "procedure", stage)
        
        # 🔥 NEW: Store detailed procedure analysis to claim_procedure_details
        if result and isinstance(result, dict):
            # Find or create ClaimProcedure for this analysis
            existing_procedure = db.query(models.ClaimProcedure).filter_by(
                claim_id=cid,
                procedure_text=procedure_name,
                procedure_type="modal_procedure",  # Mark as procedure from modal
                is_deleted=False
            ).first()
            
            if not existing_procedure:
                # Create new ClaimProcedure
                existing_procedure = models.ClaimProcedure(
                    claim_id=cid,
                    procedure_type="modal_procedure",
                    procedure_text=procedure_name,
                    requirement_flag=False,  # Add required field
                    stage=stage,
                    is_deleted=False,
                    is_dummy=False,  # Add required field
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(existing_procedure)
                db.flush()
                print(f"[ANALYZE_PROCEDURE] Created new procedure record for: {procedure_name}")
            
            # Find or create ClaimSimulation
            simulation = db.query(models.ClaimSimulation).filter_by(
                claim_id=cid, stage=stage, is_deleted=False
            ).first()
            
            if not simulation:
                simulation = models.ClaimSimulation(
                    claim_id=cid,
                    stage=stage,
                    is_deleted=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(simulation)
                db.flush()
                print(f"[ANALYZE_PROCEDURE] Created simulation record for stage: {stage}")
            
            # Create or update ClaimProcedureDetail
            existing_detail = db.query(models.ClaimProcedureDetail).filter_by(
                claim_simulation_id=simulation.id,
                procedure_id=existing_procedure.id,
                is_deleted=False
            ).first()
            
            if existing_detail:
                # Update existing detail
                existing_detail.icd9_tindakan = result.get("icd9_code", existing_detail.icd9_tindakan or "")
                existing_detail.validitas_tindakan = result.get("validitas", existing_detail.validitas_tindakan or "")
                existing_detail.status_tindakan = result.get("status_tindakan", existing_detail.status_tindakan or "")
                existing_detail.ina_cbg_tindakan = result.get("ina_cbg", existing_detail.ina_cbg_tindakan or "")
                existing_detail.syarat_klinis_tindakan = result.get("syarat_klinis", existing_detail.syarat_klinis_tindakan or "")
                existing_detail.updated_at = datetime.utcnow()
                print(f"[ANALYZE_PROCEDURE] Updated existing procedure detail for: {procedure_name}")
            else:
                # Create new detail
                procedure_detail = models.ClaimProcedureDetail(
                    claim_simulation_id=simulation.id,
                    procedure_id=existing_procedure.id,
                    icd9_tindakan=result.get("icd9_code", ""),
                    validitas_tindakan=result.get("validitas", ""),
                    status_tindakan=result.get("status_tindakan", ""),
                    ina_cbg_tindakan=result.get("ina_cbg", ""),
                    syarat_klinis_tindakan=result.get("syarat_klinis", ""),
                    is_deleted=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(procedure_detail)
                print(f"[ANALYZE_PROCEDURE] Created new procedure detail for: {procedure_name}")
            
            # 🔥 NEW: Store regulasi detail jika ada di response
            if "regulasi" in result and isinstance(result["regulasi"], list):
                print(f"[ANALYZE_PROCEDURE] Found {len(result['regulasi'])} regulation details, storing to database")
                
                for reg_item in result["regulasi"]:
                    if not reg_item or not reg_item.get("judul"):
                        continue
                        
                    # Check if regulation already exists to avoid duplicates
                    existing_reg = db.query(models.ClaimRegulationDetail).filter_by(
                        claim_id=cid,
                        procedure_id=existing_procedure.id,
                        judul_regulasi=reg_item.get("judul", "")
                    ).first()
                    
                    if not existing_reg:
                        regulation_detail = models.ClaimRegulationDetail(
                            claim_id=cid,
                            procedure_id=existing_procedure.id,
                            judul_regulasi=reg_item.get("judul", ""),
                            dasar_hukum=reg_item.get("dasar_hukum", ""),
                            bab_pasal=reg_item.get("bab_pasal", ""),
                            isi=reg_item.get("isi", ""),
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        db.add(regulation_detail)
                        print(f"[ANALYZE_PROCEDURE] Stored regulation: {reg_item.get('judul', 'Unknown')}")
        
        db.commit()
        print(f"[ANALYZE_PROCEDURE] ✅ Successfully stored all procedure analysis results")
    except Exception as e:
        print(f"[ANALYZE_PROCEDURE] ❌ Error storing results: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to store procedure analysis: {str(e)}")
    
    return result


@router.post("/{claim_id}/generate_claim_combos")
async def generate_claim_combos(claim_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    cid = payload.get("claim_id") or claim_id
    if not cid:
        raise HTTPException(status_code=422, detail="claim_id required")
    
    print(f"[GENERATE_CLAIM_COMBOS] Received payload: {payload}")
    
    try:
        core_payload = {
            "claim_id": cid,
            "primary_claim": payload.get("primary_claim", ""),
            "secondary_claims": payload.get("secondary_claims", []),
            "primary_action": payload.get("primary_action", ""),
            "secondary_actions": payload.get("secondary_actions", [])
        }
            
        print(f"[GENERATE_CLAIM_COMBOS] Forwarding to core_engine: {core_payload}")
        
        result = await claim_ai.proxy_core_engine("/generate_claim_combos", core_payload)
        
        if isinstance(result, dict) and result.get("error"):
            print(f"[GENERATE_CLAIM_COMBOS] Error from core_engine: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])
            
        print(f"[GENERATE_CLAIM_COMBOS] Success, storing results to DB")
        ai.clear_ai_results(db, cid)
        ai.bulk_store_ai_results_from_core(db, cid, result)
        
        if "evaluasi_diagnosis" in result:
            result["diagnosis"] = result["evaluasi_diagnosis"]
        if "evaluasi_tindakan" in result:
            result["procedure"] = result["evaluasi_tindakan"]
            
        return {"claim_id": cid, "stage": payload.get("stage", "admission"), "result": result}
        
    except Exception as e:
        print(f"[GENERATE_CLAIM_COMBOS] Unhandled error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{claim_id}/resume_medis")
async def resume_medis(claim_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    result = await claim_ai.proxy_core_engine("/resume_medis", payload)
    
    try:
        print(f"[RESUME_MEDIS] Storing resume results for claim {claim_id}")
        if isinstance(result, dict) and result.get("resume"):
            claim = db.query(models.Claim).get(claim_id)
            if claim:
                claim.ai_medical_resume = result["resume"]
                db.commit()
                print(f"[RESUME_MEDIS] Successfully stored resume results")
    except Exception as e:
        print(f"[RESUME_MEDIS] Error storing results: {str(e)}")
        db.rollback()
    
    return result


@router.post("/{claim_id}/regulation_detail")
async def regulation_detail(claim_id: int, payload: dict = Body(...)):
    """
    Proxy dari frontend → core_engine untuk menampilkan regulasi multilayer
    sesuai field yang diklik user di UI (diagnosis/tindakan).
    """
    # pastikan claim_id disertakan
    payload["claim_id"] = claim_id

    # fallback default kalau UI belum kirim
    payload.setdefault("kategori", payload.get("kategori") or "Pneumonia")  # contoh default
    payload.setdefault("rs_id", payload.get("rs_id") or "RS-NOTOPURO")
    payload.setdefault("region_id", payload.get("region_id") or "JATIM")

    print(f"[WEB] 🔁 Forwarding regulation detail request to core_engine: {payload}")

    # kirim ke core_engine melalui claim_ai proxy
    try:
        result = await claim_ai.regulation_detail(payload)
        return result
    except Exception as e:
        print(f"[WEB] ❌ Error calling regulation_detail: {str(e)}")
        # Return graceful error as regulation items
        return {
            "status": "error",
            "message": str(e),
            "data": [{
                "layer": "error",
                "sumber": "Error",
                "judul_regulasi": "Error",
                "isi": f"Terjadi kesalahan saat memuat regulasi: {str(e)}",
                "update": None,
                "status": "Error",
                "color": "#ef4444",
            }]
        }


# ==================================================
# i-DRG PREDICTION ENDPOINTS
# ==================================================

@router.post("/{claim_id}/predict_idrg")
async def predict_idrg_endpoint(
    claim_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Universal predict i-DRG endpoint (dispatch ke single atau combo/core_engine)"""
    try:
        payload["claim_id"] = claim_id
        mode = payload.get("mode", "single")

        print(f"[PREDICT_IDRG] Mode: {mode}, Claim ID: {claim_id}")

        # 🔀 Kalau sudah ada endpoint modular, gunakan itu
        if mode == "single":
            return await predict_idrg_single_endpoint(payload, db)
        elif mode == "combo":
            return await predict_idrg_combo_endpoint(claim_id, payload, db)
        else:
            # 🔥 fallback ke core_engine langsung
            result = await claim_ai.proxy_core_engine("/predict_idrg", payload)
            if isinstance(result, dict) and result.get("error"):
                raise HTTPException(status_code=500, detail=result["error"])
            return result

    except Exception as e:
        print(f"[ERROR PREDICT_IDRG] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        print(f"❌ Error in predict_idrg_endpoint: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.post("/predict_idrg/single")
async def predict_idrg_single_endpoint(payload: dict = Body(...), db: Session = Depends(get_db)):
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
                print(f"[PREDICT_IDRG_SINGLE] Successfully stored i-DRG results")
            except Exception as e:
                print(f"[PREDICT_IDRG_SINGLE] Error storing results: {str(e)}")
                db.rollback()
                
        return result
    except Exception as e:
        print(f"❌ Error in predict_idrg_single: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.post("/predict_idrg/combo")
async def predict_idrg_combo_endpoint(
    claim_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Endpoint khusus untuk prediksi i-DRG kombinasi"""
    try:
        payload["claim_id"] = claim_id
        payload["mode"] = "combo"
        
        print(f"[PREDICT_IDRG_COMBO] Payload: {payload}")
        
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
            
        result = await claim_ai.proxy_core_engine("/predict_idrg", payload)
        
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
                print(f"[PREDICT_IDRG_COMBO] Successfully stored i-DRG combo results")
            except Exception as e:
                print(f"[PREDICT_IDRG_COMBO] Error storing results: {str(e)}")
                db.rollback()    
        return result
        
    except Exception as e:
        print(f"[PREDICT_IDRG_COMBO] Unhandled error: {str(e)}")
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
    """Generate hanya alternatif kombinasi"""
    try:
        cid = payload.get("claim_id") or claim_id
        payload["claim_id"] = cid
        
        print(f"[GENERATE_ALTERNATIVES] Received payload: {payload}")
        
        try:
            result = await claim_ai.generate_alternatives(payload)
            
            if isinstance(result, dict) and result.get("error"):
                print(f"[GENERATE_ALTERNATIVES] Error from core_engine: {result['error']}")
                raise HTTPException(status_code=500, detail=result["error"])
                
            return {"result": result}
        except Exception as inner_e:
            print(f"[GENERATE_ALTERNATIVES] Error calling service: {str(inner_e)}")
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


# ==================================================
# SEARCH AUTOCOMPLETE
# ==================================================

@router.get("/search/diagnosis")
def search_diagnosis(query: str):
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


# ==================================================
# NOTES
# ==================================================

@router.get("/{claim_id}/notes")
def get_notes(claim_id: int, db: Session = Depends(get_db)):
    notes = db.query(models.ClaimNote).filter(models.ClaimNote.claim_id == claim_id).all()
    return {"data": [
        {
            "id": n.id,
            "item_id": n.item_id,
            "role": n.role,
            "user_id": n.user_id,
            "note_text": n.note_text,
            "timestamp": n.timestamp.isoformat()
        } for n in notes
    ]}


@router.post("/{claim_id}/notes")
async def add_note(
    claim_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator")),
    _=Depends(require_csrf_dep),
):
    """Add note to claim item"""
    form_data = await request.form()
    item_id = form_data.get("item_id")
    note_text = form_data.get("note_text")
    
    if not item_id or not note_text:
        raise HTTPException(status_code=400, detail="item_id and note_text required")
    
    note = models.ClaimNote(
        claim_id=claim_id,
        item_id=item_id,
        role=user.role_names[0] if user.role_names else "unknown",
        user_id=user.id,
        note_text=note_text,
        timestamp=datetime.now()
    )
    db.add(note)
    db.commit()
    
    return {"status": "success", "message": "Note added"}


# ==================================================
# CSRF TOKEN REFRESH
# ==================================================

@router.get("/csrf/refresh")
def refresh_csrf_token(request: Request):
    from ..auth import issue_csrf_token
    return {"csrf_token": issue_csrf_token(request)}


# ==================================================  
# MULTI-LAYER RULE ENDPOINTS
# ==================================================

@router.get("/rules/load")
async def load_multilayer_rules(
    diagnosis: str = Query(..., description="Nama diagnosis (e.g., 'Pneumonia')"),
    rs_id: Optional[str] = Query(None, description="ID rumah sakit (e.g., 'rs_notopuro')"),
    region_id: Optional[str] = Query(None, description="ID wilayah (e.g., 'jatim')"),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "verifikator", "coder", "admin_rs"))
):
    """
    Load rules multilayer untuk diagnosis tertentu.
    
    Returns JSON dengan rules dari semua layer yang berlaku:
    - Layer 1-2: Permenkes & Nasional (static/JSON)
    - Layer 3-8: PPK, Regional, RS, Bridging, Fraud, Temporary (database)
    
    RS rules (layer 3 & 5) override semua layer di atasnya jika tersedia.
    """
    try:
        # Call core_engine via HTTP
        import requests
        import os
        
        core_engine_url = os.getenv("CORE_ENGINE_URL", "http://core_engine:8002")
        
        # Build query parameters
        params = {"diagnosis": diagnosis}
        if rs_id:
            params["rs_id"] = rs_id
        if region_id:
            params["region_id"] = region_id
        
        # Call core_engine endpoint (POST dengan JSON payload)
        payload = {"diagnosis": diagnosis}
        if rs_id:
            payload["rs_id"] = rs_id
        if region_id:
            payload["region_id"] = region_id
            
        response = requests.post(
            f"{core_engine_url}/rules/load",
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Core engine error: {response.text}"
            )
        
        rules_data = response.json()
        
        print(f"[RULES/LOAD] Called core_engine, got {rules_data.get('total_rules', 0)} rules for {diagnosis} (RS: {rs_id})")
        return rules_data
        
    except Exception as e:
        print(f"[RULES/LOAD] Error calling core_engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load rules from core_engine: {str(e)}")

@router.get("/rules/summary")
async def get_rules_summary(
    diagnosis: str = Query(..., description="Nama diagnosis"),
    rs_id: Optional[str] = Query(None, description="ID rumah sakit"),
    region_id: Optional[str] = Query(None, description="ID wilayah"),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "verifikator", "coder", "admin_rs"))
):
    """
    Get summary rules by layer untuk diagnosis tertentu.
    
    Returns ringkasan rules per layer dengan jumlah dan source info.
    """
    try:
        import sys
        import os
        current_dir = os.path.dirname(__file__)
        core_engine_path = os.path.join(current_dir, "..", "..", "..", "core_engine", "services")
        sys.path.insert(0, core_engine_path)
        
        from rules_loader import get_rules_summary_db
        
        summary = get_rules_summary_db(diagnosis, rs_id, region_id, db)
        
        return {
            "status": "success",
            "diagnosis": diagnosis,
            "summary": summary,
            "engine_version": f"multilayer_rules_summary@{datetime.now().strftime('%Y-%m-%d')}"
        }
        
    except Exception as e:
        print(f"[RULES/SUMMARY] Error getting summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get rules summary: {str(e)}")

@router.get("/rules/layers")
async def get_layer_info(
    user=Depends(require_roles_session("doctor", "verifikator", "coder", "admin_rs"))
):
    """
    Get informasi 8 layer system dan prioritas.
    
    Returns struktur 8 layer dengan penjelasan prioritas RS override.
    """
    return {
        "status": "success",
        "layers": [
            {"id": "permenkes", "name": "Permenkes/BPJS Pusat", "priority": 1, "source": "Regulasi resmi", "override": False},
            {"id": "nasional", "name": "Nasional (CP/PNPK/FORNAS/ICD/INA-CBG)", "priority": 2, "source": "Kemenkes/WHO", "override": False},
            {"id": "ppk", "name": "PPK RS", "priority": 3, "source": "Dokumen PPK RS", "override": True},
            {"id": "regional", "name": "Regional (Wilayah/SE BPJS Cabang)", "priority": 4, "source": "SE BPJS/Dinkes", "override": False},
            {"id": "rs", "name": "RS Lokal (BA/SOP)", "priority": 5, "source": "BA/SOP RS", "override": True},
            {"id": "bridging", "name": "Bridging (Teknis SIMRS/BPJS)", "priority": 6, "source": "Panduan BPJS", "override": False},
            {"id": "fraud", "name": "Fraud Rules (AI Anti-Anomali)", "priority": 7, "source": "Model AI", "override": False},
            {"id": "temporary", "name": "Temporary Policy", "priority": 8, "source": "Kebijakan Nasional", "override": False}
        ],
        "priority_rule": "RS rules (layer 3 & 5) override semua layer di atasnya jika tersedia",
        "total_layers": 8,
        "engine_version": f"multilayer_system@{datetime.now().strftime('%Y-%m-%d')}"
    }

# ==================================================
# CRUD ENDPOINTS FOR ADMIN RS (PPK RS & RS LOKAL)
# ==================================================

@router.get("/rules/my_rules")
async def get_my_rs_rules(
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs"))
):
    """
    Get rules yang dibuat oleh Admin RS ini.
    
    Returns:
    - PPK RS rules (layer ppk) 
    - RS Lokal rules (layer rs)
    - Grouped by status: unverified, official, active, rejected
    """
    try:
        # Get user's hospital info untuk filter rs_id
        user_rs_id = None
        if hasattr(user, 'hospital') and user.hospital:
            user_rs_id = user.hospital.kode_hospital or f"rs_{user.hospital.id}"
        
        # Query rules milik RS ini (layer ppk dan rs saja)
        rules_query = db.query(models.RulesMaster).filter(
            and_(
                models.RulesMaster.rs_id == user_rs_id,
                models.RulesMaster.layer.in_(["ppk", "rs"])
            )
        ).order_by(models.RulesMaster.created_at.desc())
        
        rules = rules_query.all()
        
        # Group by status dan layer
        grouped_rules = {
            "ppk": {"unverified": [], "official": [], "active": [], "rejected": []},
            "rs": {"unverified": [], "official": [], "active": [], "rejected": []}
        }
        
        for rule in rules:
            layer = rule.layer
            status = rule.status
            rule_data = {
                "id": rule.id,
                "diagnosis": rule.diagnosis,
                "field": rule.field,
                "isi": rule.isi,
                "sumber": rule.sumber,
                "created_at": rule.created_at.isoformat(),
                "updated_at": rule.updated_at.isoformat(),
                "approved_by": rule.approved_by,
                "approved_date": rule.approved_date.isoformat() if rule.approved_date else None,
                "review_notes": rule.review_notes
            }
            
            if layer in grouped_rules and status in grouped_rules[layer]:
                grouped_rules[layer][status].append(rule_data)
        
        # Summary counts
        total_ppk = sum(len(grouped_rules["ppk"][status]) for status in grouped_rules["ppk"])
        total_rs = sum(len(grouped_rules["rs"][status]) for status in grouped_rules["rs"])
        
        return {
            "status": "success",
            "hospital_id": user_rs_id,
            "rules": grouped_rules,
            "summary": {
                "total_ppk_rules": total_ppk,
                "total_rs_rules": total_rs,
                "total_rules": total_ppk + total_rs,
                "pending_approval": len(grouped_rules["ppk"]["unverified"]) + len(grouped_rules["rs"]["unverified"])
            }
        }
        
    except Exception as e:
        print(f"[MY_RULES] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get rules: {str(e)}")

@router.post("/rules/add")
async def add_rs_rule(
    diagnosis: str = Form(...),
    field: str = Form(...),
    layer: str = Form(...),  # "ppk" atau "rs"
    isi: str = Form(...),
    sumber: str = Form(...),
    pdf_file: UploadFile = File(None),  # Optional PDF file
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs")),
    _=Depends(require_csrf_dep)
):
    """
    Tambah rule baru untuk RS.
    
    Hanya Admin RS yang boleh tambah layer "ppk" dan "rs".
    """
    try:
        # Validasi layer
        if layer not in ["ppk", "rs"]:
            raise HTTPException(
                status_code=400, 
                detail="Admin RS hanya boleh menambah layer 'ppk' atau 'rs'"
            )
        
        # Get user's hospital info
        user_rs_id = None
        user_region_id = None
        if hasattr(user, 'hospital') and user.hospital:
            user_rs_id = user.hospital.kode_hospital or f"rs_{user.hospital.id}"
            # Assume region mapping - bisa diperbaiki nanti
            user_region_id = "jatim"  # default, nanti ambil dari hospital data
        
        # Handle PDF file upload
        pdf_filename = None
        if pdf_file and pdf_file.filename:
            # Create uploads directory if not exists
            upload_dir = "web/uploads/rules_pdf"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Validate file type
            if pdf_file.content_type != 'application/pdf':
                raise HTTPException(status_code=400, detail="Hanya file PDF yang diperbolehkan")
            
            # Generate unique filename
            file_extension = pdf_file.filename.split('.')[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                content = await pdf_file.read()
                buffer.write(content)
            
            pdf_filename = unique_filename
            print(f"[UPLOAD] Saved PDF: {pdf_filename}")
        
        # Create new rule
        new_rule = models.RulesMaster(
            diagnosis=diagnosis.strip(),
            field=field.strip(),
            layer=layer,
            isi=isi.strip(),
            sumber=sumber.strip(),
            pdf_file=pdf_filename,  # Include PDF filename
            rs_id=user_rs_id,
            region_id=user_region_id,
            status="unverified",  # Default status untuk approval workflow
            created_by=f"admin_rs_{user_rs_id}",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        
        print(f"[ADD_RULE] Created rule ID {new_rule.id} for {diagnosis} by {user_rs_id}")
        
        return {
            "status": "success",
            "message": f"Rule {layer.upper()} berhasil ditambahkan dan menunggu verifikasi",
            "rule_id": new_rule.id,
            "diagnosis": diagnosis,
            "layer": layer,
            "approval_status": "unverified"
        }
        
    except Exception as e:
        db.rollback()
        print(f"[ADD_RULE] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add rule: {str(e)}")

@router.get("/rules/{rule_id}/pdf")
async def download_rule_pdf(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs"))
):
    """Download PDF dokumen rule"""
    try:
        # Get rule
        rule = db.query(models.RulesMaster).filter(models.RulesMaster.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule tidak ditemukan")
        
        if not rule.pdf_file:
            raise HTTPException(status_code=404, detail="Rule tidak memiliki file PDF")
        
        # Check file exists
        file_path = os.path.join("web/uploads/rules_pdf", rule.pdf_file)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File PDF tidak ditemukan di server")
        
        # Return file
        def iterfile():
            with open(file_path, "rb") as file_like:
                yield from file_like
                
        headers = {
            "Content-Disposition": f"attachment; filename={rule.diagnosis}_{rule.layer}.pdf"
        }
        
        return StreamingResponse(
            iterfile(),
            media_type="application/pdf",
            headers=headers
        )
        
    except Exception as e:
        print(f"[DOWNLOAD_PDF] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download PDF: {str(e)}")

@router.put("/rules/{rule_id}/update")
async def update_rs_rule(
    rule_id: int,
    diagnosis: str = Form(...),
    field: str = Form(...),
    isi: str = Form(...),
    sumber: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs")),
    _=Depends(require_csrf_dep)
):
    """
    Update rule yang masih berstatus 'unverified'.
    
    Admin RS hanya boleh edit rule milik sendiri yang belum di-approve.
    """
    try:
        # Get user's hospital info
        user_rs_id = None
        if hasattr(user, 'hospital') and user.hospital:
            user_rs_id = user.hospital.kode_hospital or f"rs_{user.hospital.id}"
        
        # Find rule
        rule = db.query(models.RulesMaster).filter(
            and_(
                models.RulesMaster.id == rule_id,
                models.RulesMaster.rs_id == user_rs_id,  # Hanya rule milik sendiri
                models.RulesMaster.layer.in_(["ppk", "rs"])  # Hanya layer yang diizinkan
            )
        ).first()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule tidak ditemukan atau bukan milik RS ini")
        
        # Cek status - hanya unverified yang boleh diedit
        if rule.status != "unverified":
            raise HTTPException(
                status_code=400, 
                detail=f"Rule dengan status '{rule.status}' tidak dapat diedit"
            )
        
        # Update rule
        rule.diagnosis = diagnosis.strip()
        rule.field = field.strip()
        rule.isi = isi.strip()
        rule.sumber = sumber.strip()
        rule.updated_at = datetime.now()
        
        db.commit()
        
        print(f"[UPDATE_RULE] Updated rule ID {rule_id} by {user_rs_id}")
        
        return {
            "status": "success",
            "message": "Rule berhasil diperbarui",
            "rule_id": rule_id,
            "updated_at": rule.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[UPDATE_RULE] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update rule: {str(e)}")

@router.delete("/rules/{rule_id}")
async def delete_rs_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs")),
    _=Depends(require_csrf_dep)
):
    """
    Soft delete rule (hanya yang berstatus unverified).
    
    Admin RS hanya boleh hapus rule milik sendiri yang belum di-approve.
    """
    try:
        # Get user's hospital info
        user_rs_id = None
        if hasattr(user, 'hospital') and user.hospital:
            user_rs_id = user.hospital.kode_hospital or f"rs_{user.hospital.id}"
        
        # Find rule
        rule = db.query(models.RulesMaster).filter(
            and_(
                models.RulesMaster.id == rule_id,
                models.RulesMaster.rs_id == user_rs_id,
                models.RulesMaster.layer.in_(["ppk", "rs"])
            )
        ).first()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule tidak ditemukan atau bukan milik RS ini")
        
        # Cek status - hanya unverified yang boleh dihapus
        if rule.status != "unverified":
            raise HTTPException(
                status_code=400, 
                detail=f"Rule dengan status '{rule.status}' tidak dapat dihapus"
            )
        
        # Soft delete - ubah status jadi "deleted"
        rule.status = "deleted"
        rule.updated_at = datetime.now()
        
        db.commit()
        
        print(f"[DELETE_RULE] Soft deleted rule ID {rule_id} by {user_rs_id}")
        
        return {
            "status": "success",
            "message": "Rule berhasil dihapus",
            "rule_id": rule_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[DELETE_RULE] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete rule: {str(e)}")


# ==============================================
# REGIONAL REPORTS ENDPOINTS (FASE 6C)
# ==============================================

@router.post("/regional-reports/add")
async def add_regional_report(
    title: str = Form(...),
    description: str = Form(""),
    se_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs")),
    _=Depends(require_csrf_dep)
):
    """
    Admin RS melaporkan edaran regional (SE) ke AI META untuk review.
    """
    try:
        # Validate file
        if not se_file.filename or not se_file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Hanya file PDF yang diperbolehkan")
        
        if se_file.size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="Ukuran file maksimal 10MB")
        
        # Get user info
        user_rs_id = None
        user_region_id = "jatim"  # Default region
        if hasattr(user, 'hospital') and user.hospital:
            user_rs_id = user.hospital.kode_hospital or f"rs_{user.hospital.id}"
        
        # Save SE file
        upload_dir = "web/uploads/regional_se"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_extension = se_file.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            content = await se_file.read()
            buffer.write(content)
        
        # Save to database
        new_report = models.RegionalReports(
            title=title.strip(),
            description=description.strip() if description else None,
            se_file=unique_filename,
            region_id=user_region_id,
            rs_id=user_rs_id,
            status="pending",
            reported_by=f"admin_rs_{user_rs_id}",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        
        print(f"[REGIONAL_REPORT] Created report ID {new_report.id} - {title} by {user_rs_id}")
        
        return {
            "status": "success",
            "message": "Laporan SE berhasil dikirim ke AI META untuk review",
            "report_id": new_report.id,
            "title": title
        }
        
    except Exception as e:
        db.rollback()
        print(f"[REGIONAL_REPORT] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit report: {str(e)}")


@router.get("/regional-reports/{report_id}/pdf")
async def download_regional_report_pdf(
    report_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs", "superadmin"))
):
    """Download SE PDF file"""
    try:
        # Get report
        report = db.query(models.RegionalReports).filter(models.RegionalReports.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report tidak ditemukan")
        
        # Check file exists
        file_path = os.path.join("web/uploads/regional_se", report.se_file)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File SE tidak ditemukan di server")
        
        # Return file
        def iterfile():
            with open(file_path, "rb") as file_like:
                yield from file_like
                
        headers = {
            "Content-Disposition": f"attachment; filename=SE_{report.title.replace(' ', '_')}.pdf"
        }
        
        return StreamingResponse(
            iterfile(),
            media_type="application/pdf",
            headers=headers
        )
        
    except Exception as e:
        print(f"[DOWNLOAD_SE] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download SE: {str(e)}")


# ==============================================
# FEEDBACK SYSTEM ENDPOINTS (POINT H)
# ==============================================

@router.post("/rules/{rule_id}/feedback")
async def submit_rule_feedback(
    rule_id: int,
    feedback: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs", "doctor", "verifikator")),
    _=Depends(require_csrf_dep)
):
    """
    Submit feedback untuk rule tertentu.
    RS dapat memberikan masukan tentang aturan yang berlaku.
    """
    try:
        # Get rule
        rule = db.query(models.RulesMaster).filter(models.RulesMaster.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule tidak ditemukan")
        
        # Get user info
        user_identifier = f"{user.role}"
        if hasattr(user, 'hospital') and user.hospital:
            user_identifier += f"_{user.hospital.kode_hospital or f'rs_{user.hospital.id}'}"
        
        # Update feedback
        rule.feedback = feedback.strip()
        rule.feedback_by = user_identifier
        rule.feedback_date = datetime.now()
        rule.updated_at = datetime.now()
        
        db.commit()
        
        print(f"[FEEDBACK] Rule {rule_id} feedback from {user_identifier}: {feedback[:50]}...")
        
        return {
            "status": "success",
            "message": "Feedback berhasil dikirim ke AI META",
            "rule_id": rule_id
        }
        
    except Exception as e:
        db.rollback()
        print(f"[FEEDBACK] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@router.get("/rules/feedback/list")
async def get_rules_with_feedback(
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin", "ai_meta"))
):
    """
    AI META endpoint untuk melihat semua rules yang ada feedback.
    """
    try:
        rules_with_feedback = db.query(models.RulesMaster).filter(
            models.RulesMaster.feedback.isnot(None)
        ).order_by(models.RulesMaster.feedback_date.desc()).all()
        
        result = []
        for rule in rules_with_feedback:
            result.append({
                "id": rule.id,
                "diagnosis": rule.diagnosis,
                "field": rule.field,
                "layer": rule.layer,
                "isi": rule.isi,
                "sumber": rule.sumber,
                "rs_id": rule.rs_id,
                "feedback": rule.feedback,
                "feedback_by": rule.feedback_by,
                "feedback_date": rule.feedback_date.isoformat() if rule.feedback_date else None,
                "status": rule.status
            })
        
        return {
            "status": "success",
            "total_feedback": len(result),
            "rules_with_feedback": result
        }
        
    except Exception as e:
        print(f"[GET_FEEDBACK] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get feedback: {str(e)}")


# ==================================================
# TOOLTIP SYSTEM - Point G from Specification
# ==================================================

@router.get("/tooltip/rules/{field_path}")
async def get_field_tooltip(
    field_path: str,
    diagnosis: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin"))
):
    """
    API endpoint untuk tooltip hover system.
    Mengembalikan ringkasan rules yang relevan untuk field tertentu.
    
    Args:
        field_path: Path field seperti "diagnosis.justifikasi", "rawat_inap.lama_rawat", dll
        diagnosis: Diagnosis code opsional untuk filter rules spesifik
    
    Returns:
        JSON dengan ringkasan rules yang relevan untuk ditampilkan di tooltip
    """
    try:
        # Build query untuk rules yang relevan
        query = db.query(models.RulesMaster).filter(
            models.RulesMaster.field == field_path,
            models.RulesMaster.status.in_(["official", "active"])
        )
        
        # Filter berdasarkan diagnosis jika diberikan
        if diagnosis:
            query = query.filter(
                models.RulesMaster.diagnosis.like(f"%{diagnosis}%")
            )
        
        # Order by priority (layer hierarchy)
        layer_priority = {
            "permenkes": 1,
            "nasional": 2, 
            "ppk": 3,
            "regional": 4,
            "rs": 5,
            "bridging": 6,
            "fraud": 7,
            "temporary": 8
        }
        
        rules = query.all()
        
        # Sort rules by layer priority
        sorted_rules = sorted(rules, key=lambda x: layer_priority.get(x.layer, 99))
        
        # Build tooltip content
        tooltip_sections = []
        
        for rule in sorted_rules[:3]:  # Limit to top 3 most important rules
            # Truncate rule text for tooltip
            rule_text = rule.isi
            if len(rule_text) > 120:
                rule_text = rule_text[:120] + "..."
                
            section = {
                "layer": rule.layer.upper(),
                "text": rule_text,
                "source": rule.sumber,
                "color_class": get_layer_color_class(rule.layer)
            }
            tooltip_sections.append(section)
        
        # Build summary text
        if tooltip_sections:
            summary = f"Ditemukan {len(rules)} aturan untuk field ini"
            if diagnosis:
                summary += f" (diagnosis: {diagnosis})"
        else:
            summary = "Tidak ada aturan khusus untuk field ini"
            
        return {
            "status": "success",
            "field": field_path,
            "diagnosis": diagnosis,
            "summary": summary,
            "total_rules": len(rules),
            "tooltip_sections": tooltip_sections,
            "has_rules": len(rules) > 0
        }
        
    except Exception as e:
        print(f"[TOOLTIP] Error for field {field_path}: {str(e)}")
        return {
            "status": "error",
            "field": field_path,
            "summary": "Error loading tooltip",
            "tooltip_sections": [],
            "has_rules": False
        }


# ==================================================
# API ENDPOINTS FOR AI META DASHBOARD
# ==================================================

@router.get("/api/rules/{rule_id}")
async def get_rule_detail(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin", "admin_rs", "doctor", "coder"))
):
    """
    Get detailed information about a specific rule.
    Used by AI META dashboard and other components.
    """
    rule = db.query(models.RulesMaster).filter(models.RulesMaster.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {
        "id": rule.id,
        "layer": rule.layer,
        "diagnosis": rule.diagnosis,
        "field": rule.field,
        "isi": rule.isi,
        "sumber": rule.sumber,
        "rs_id": rule.rs_id,
        "region_id": rule.region_id,
        "status": rule.status,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "created_by": rule.created_by,
        "approved_by": rule.approved_by,
        "approved_date": rule.approved_date.isoformat() if rule.approved_date else None,
        "review_notes": rule.review_notes,
        "feedback": rule.feedback,
        "feedback_by": rule.feedback_by,
        "feedback_date": rule.feedback_date.isoformat() if rule.feedback_date else None
    }

@router.get("/api/regional-reports/{report_id}")
async def get_regional_report_detail(
    report_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin", "admin_rs"))
):
    """
    Get detailed information about a specific regional report.
    Used by AI META dashboard.
    """
    report = db.query(models.RegionalReports).filter(models.RegionalReports.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Regional report not found")
    
    return {
        "id": report.id,
        "report_type": report.report_type,
        "region_id": report.region_id,
        "rs_id": report.rs_id,
        "period_start": report.period_start.isoformat() if report.period_start else None,
        "period_end": report.period_end.isoformat() if report.period_end else None,
        "content": report.content,
        "status": report.status,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "created_by": report.created_by,
        "reviewed_by": report.reviewed_by,
        "reviewed_date": report.reviewed_date.isoformat() if report.reviewed_date else None,
        "review_notes": report.review_notes
    }


def get_layer_color_class(layer: str) -> str:
    """
    Return CSS color class for different rule layers
    """
    layer_colors = {
        "permenkes": "text-red-600",      # Highest priority - red
        "nasional": "text-orange-600",    # National - orange  
        "ppk": "text-yellow-600",         # PPK - yellow
        "regional": "text-green-600",     # Regional - green
        "rs": "text-blue-600",            # Hospital - blue
        "bridging": "text-indigo-600",    # Bridging - indigo
        "fraud": "text-purple-600",       # Fraud detection - purple
        "temporary": "text-gray-600"      # Temporary - gray
    }
    return layer_colors.get(layer, "text-gray-500")

# ==================================================
# WORKFLOW STATUS ENDPOINTS
# ==================================================

@router.get("/{claim_id}/workflow-status")
def get_workflow_status(
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin"))
):
    """Get current workflow status of a claim"""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    return {
        "claim_id": claim_id,
        "workflow_status": claim.workflow_status or "draft",
        "created_by": claim.created_by,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "doctor_submitted_by": claim.doctor_submitted_by,
        "doctor_submitted_at": claim.doctor_submitted_at.isoformat() if hasattr(claim, 'doctor_submitted_at') and claim.doctor_submitted_at else None,
        "coder_verified_by": claim.coder_verified_by,
        "coder_verified_at": claim.coder_verified_at.isoformat() if hasattr(claim, 'coder_verified_at') and claim.coder_verified_at else None,
        "finalized_by": claim.finalized_by if hasattr(claim, 'finalized_by') else None,
        "finalized_at": claim.finalized_at.isoformat() if hasattr(claim, 'finalized_at') and claim.finalized_at else None,
    }


@router.post("/{claim_id}/return-to-doctor")
async def return_to_doctor(
    claim_id: int,
    request: Request,
    reason: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("coder", "verifikator")),
    _=Depends(require_csrf_dep),
):
    """Return claim to doctor for revision"""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Add note about return reason
    note = models.ClaimNote(
        claim_id=claim_id,
        item_id="0",
        role=user.role_names[0] if user.role_names else "unknown",
        user_id=user.id,
        note_text=f"RETURNED TO DOCTOR: {reason}",
        timestamp=datetime.now()
    )
    db.add(note)
    
    # Reset workflow status
    claim.workflow_status = "draft"
    db.commit()
    
    flash(request, f"✅ Klaim dikembalikan ke dokter dengan alasan: {reason}", "success")
    return RedirectResponse(url="/claims", status_code=303)


# ==================================================
# STEP 2: VERIFY STORAGE TEST ENDPOINTS
# ==================================================

@router.get("/{claim_id}/verify-storage", name="verify_claim_storage")
def verify_claim_storage(
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin"))
):
    """
    Test endpoint untuk verify semua data storage dari STEP 1 fixes.
    Mengembalikan ringkasan data yang tersimpan untuk claim tertentu.
    """
    try:
        result = {
            "claim_id": claim_id,
            "timestamp": datetime.now().isoformat(),
            "storage_verification": {}
        }
        
        # 1. Verify ClaimAIRecommendation (Generate AI)
        ai_recs = db.query(models.ClaimAIRecommendation).filter_by(
            claim_id=claim_id, is_deleted=False
        ).count()
        result["storage_verification"]["ai_recommendations"] = {
            "count": ai_recs,
            "status": "✅ OK" if ai_recs > 0 else "⚠️ Empty"
        }
        
        # 2. Verify ClaimDiagnosis (Modal detail diagnosis)
        diagnoses = db.query(models.ClaimDiagnosis).filter_by(
            claim_id=claim_id, is_deleted=False
        ).all()
        result["storage_verification"]["diagnoses"] = {
            "count": len(diagnoses),
            "types": [d.diagnosis_type for d in diagnoses],
            "status": "✅ OK" if diagnoses else "⚠️ Empty"
        }
        
        # 3. Verify ClaimProcedure (Tindakan dari modal)
        procedures = db.query(models.ClaimProcedure).filter_by(
            claim_id=claim_id, is_deleted=False
        ).all()
        modal_procedures = [p for p in procedures if p.procedure_type in ["modal_diagnosis", "modal_procedure"]]
        result["storage_verification"]["procedures"] = {
            "total_count": len(procedures),
            "modal_count": len(modal_procedures),
            "modal_types": [p.procedure_type for p in modal_procedures],
            "status": "✅ OK" if modal_procedures else "⚠️ No modal procedures"
        }
        
        # 4. Verify ClaimProcedureDetail (Detail tindakan)
        proc_details = db.query(models.ClaimProcedureDetail).filter(
            models.ClaimProcedureDetail.procedure_id.in_([p.id for p in procedures])
        ).count()
        result["storage_verification"]["procedure_details"] = {
            "count": proc_details,
            "status": "✅ OK" if proc_details > 0 else "⚠️ Empty"
        }
        
        # 5. Verify ClaimRegulationDetail (Modal regulasi)
        regulations = db.query(models.ClaimRegulationDetail).filter_by(
            claim_id=claim_id
        ).count()
        result["storage_verification"]["regulations"] = {
            "count": regulations,
            "status": "✅ OK" if regulations > 0 else "⚠️ Empty"
        }
        
        # 6. Verify ClaimIDRGDiagnosis (IDRG per diagnosis - doctor)
        idrg_diagnosis = db.query(models.ClaimIDRGDiagnosis).filter_by(
            claim_id=claim_id, is_deleted=False
        ).count()
        result["storage_verification"]["idrg_diagnosis"] = {
            "count": idrg_diagnosis,
            "status": "✅ OK" if idrg_diagnosis > 0 else "⚠️ Empty"
        }
        
        # 7. Verify ClaimIDRGSummary (IDRG kombinasi - verificator)
        idrg_summary = db.query(models.ClaimIDRGSummary).filter_by(
            claim_id=claim_id, is_deleted=False
        ).count()
        result["storage_verification"]["idrg_summary"] = {
            "count": idrg_summary,
            "status": "✅ OK" if idrg_summary > 0 else "⚠️ Empty (normal untuk doctor)"
        }
        
        # 8. Verify ClaimSimulation (Mapping panel kanan)
        simulations = db.query(models.ClaimSimulation).filter_by(
            claim_id=claim_id, is_deleted=False
        ).count()
        result["storage_verification"]["simulations"] = {
            "count": simulations,
            "status": "✅ OK" if simulations > 0 else "⚠️ Empty"
        }
        
        # Overall status
        issues = [k for k, v in result["storage_verification"].items() 
                 if "⚠️" in v["status"] and k not in ["idrg_summary"]]
        
        result["overall_status"] = "✅ ALL GOOD" if not issues else f"⚠️ Issues: {', '.join(issues)}"
        result["next_step"] = "Ready for STEP 3" if not issues else "Need to test endpoints"
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


# ==================================================
# STEP 3: READ-ONLY ENDPOINTS FOR VERIFICATOR
# ==================================================

@router.get("/{claim_id}/stored-diagnosis-detail/{diagnosis_name}", name="get_stored_diagnosis_detail")
def get_stored_diagnosis_detail(
    claim_id: int,
    diagnosis_name: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator", "coder", "admin_rs", "superadmin"))
):
    """
    Read-only endpoint untuk verificator - mengambil detail diagnosis yang sudah disimpan doctor.
    Data berasal dari database, bukan hit core_engine.
    """
    try:
        print(f"[STORED_DIAGNOSIS_DETAIL] Loading stored data for claim {claim_id}, diagnosis: {diagnosis_name}")
        
        # Find diagnosis in database
        diagnosis = db.query(models.ClaimDiagnosis).filter(
            models.ClaimDiagnosis.claim_id == claim_id,
            models.ClaimDiagnosis.diagnosis_text.ilike(f"%{diagnosis_name}%"),
            models.ClaimDiagnosis.is_deleted == False
        ).first()
        
        if not diagnosis:
            raise HTTPException(status_code=404, detail=f"Stored diagnosis '{diagnosis_name}' not found for claim {claim_id}")
        
        # Build response structure similar to core_engine format
        result = {
            "status": "success",
            "mode": "stored_data",
            "claim_id": claim_id,
            "diagnosis_name": diagnosis_name,
            "diagnosis_detail": {
                "diagnosis_text": diagnosis.diagnosis_text,
                "icd10_code": diagnosis.icd10_code or "",
                "diagnosis_type": diagnosis.diagnosis_type,
                "justifikasi": diagnosis.justifikasi or "",
                "syarat_klinis": diagnosis.syarat_klinis or "",
                "bukti_klinis": diagnosis.bukti_klinis or "",
                "struktur_icd10": diagnosis.struktur_icd10 or "",
                "kode_ganda": diagnosis.kode_ganda or "",
                "z_code": diagnosis.z_code or "",
                "kode_bpjs_khusus": diagnosis.kode_bpjs_khusus or "",
                "indikasi": diagnosis.indikasi or "",
                "lama_rawat": diagnosis.lama_rawat or "",
                "perpanjangan": diagnosis.perpanjangan or "",
                "kesesuaian_rs": diagnosis.kesesuaian_rs or "",
                "syarat": diagnosis.syarat or "",
                "kelayakan": diagnosis.kelayakan or ""
            }
        }
        
        # Get related procedures (tindakan yang muncul di modal diagnosis)
        related_procedures = db.query(models.ClaimProcedure).filter(
            models.ClaimProcedure.claim_id == claim_id,
            models.ClaimProcedure.procedure_type == "modal_diagnosis",
            models.ClaimProcedure.is_deleted == False
        ).all()
        
        if related_procedures:
            result["tindakan"] = []
            for proc in related_procedures:
                # Get procedure details
                proc_detail = db.query(models.ClaimProcedureDetail).filter(
                    models.ClaimProcedureDetail.procedure_id == proc.id,
                    models.ClaimProcedureDetail.is_deleted == False
                ).first()
                
                tindakan_item = {
                    "name": proc.procedure_text,
                    "procedure_type": proc.procedure_type,
                    "icd9": proc_detail.icd9_tindakan if proc_detail else "",
                    "validitas": proc_detail.validitas_tindakan if proc_detail else "",
                    "status": proc_detail.status_tindakan if proc_detail else "",
                    "ina_cbg": proc_detail.ina_cbg_tindakan if proc_detail else "",
                    "syarat_klinis": proc_detail.syarat_klinis_tindakan if proc_detail else ""
                }
                result["tindakan"].append(tindakan_item)
        
        # Get related regulations
        related_regulations = db.query(models.ClaimRegulationDetail).filter(
            models.ClaimRegulationDetail.claim_id == claim_id,
            models.ClaimRegulationDetail.diagnosis_id == diagnosis.id
        ).all()
        
        if related_regulations:
            result["regulasi"] = []
            for reg in related_regulations:
                regulasi_item = {
                    "judul": reg.judul_regulasi,
                    "dasar_hukum": reg.dasar_hukum or "",
                    "bab_pasal": reg.bab_pasal or "",
                    "isi": reg.isi or ""
                }
                result["regulasi"].append(regulasi_item)
        
        # Get IDRG data for this diagnosis
        idrg_data = db.query(models.ClaimIDRGDiagnosis).filter(
            models.ClaimIDRGDiagnosis.claim_id == claim_id,
            models.ClaimIDRGDiagnosis.is_deleted == False
        ).first()
        
        if idrg_data:
            result["idrg_prediction"] = {
                "group_idrg": idrg_data.group_idrg or "",
                "severity_index": idrg_data.severity_index or "",
                "checklist": json.loads(idrg_data.checklist) if idrg_data.checklist else {},
                "faktor_severity": json.loads(idrg_data.faktor_severity) if idrg_data.faktor_severity else {},
                "ungroupable_alert": idrg_data.ungroupable_alert or "",
                "simulasi_tarif": idrg_data.simulasi_tarif or "",
                "gap_analysis": idrg_data.gap_analysis or ""
            }
        
        result["read_only_mode"] = True
        result["message"] = f"✅ Stored data loaded successfully for '{diagnosis_name}'"
        
        print(f"[STORED_DIAGNOSIS_DETAIL] ✅ Successfully loaded stored data with {len(result.get('tindakan', []))} procedures and {len(result.get('regulasi', []))} regulations")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[STORED_DIAGNOSIS_DETAIL] ❌ Error loading stored data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load stored diagnosis detail: {str(e)}")


@router.get("/{claim_id}/stored-procedure-detail/{procedure_name}", name="get_stored_procedure_detail")
def get_stored_procedure_detail(
    claim_id: int,
    procedure_name: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator", "coder", "admin_rs", "superadmin"))
):
    """
    Read-only endpoint untuk verificator - mengambil detail tindakan yang sudah disimpan doctor.
    Data berasal dari database, bukan hit core_engine.
    """
    try:
        print(f"[STORED_PROCEDURE_DETAIL] Loading stored data for claim {claim_id}, procedure: {procedure_name}")
        
        # Find procedure in database
        procedure = db.query(models.ClaimProcedure).filter(
            models.ClaimProcedure.claim_id == claim_id,
            models.ClaimProcedure.procedure_text.ilike(f"%{procedure_name}%"),
            models.ClaimProcedure.is_deleted == False
        ).first()
        
        if not procedure:
            raise HTTPException(status_code=404, detail=f"Stored procedure '{procedure_name}' not found for claim {claim_id}")
        
        # Get procedure details
        proc_detail = db.query(models.ClaimProcedureDetail).filter(
            models.ClaimProcedureDetail.procedure_id == procedure.id,
            models.ClaimProcedureDetail.is_deleted == False
        ).first()
        
        # Build response structure similar to core_engine format
        result = {
            "status": "success",
            "mode": "stored_data",
            "claim_id": claim_id,
            "procedure_name": procedure_name,
            "procedure_detail": {
                "procedure_text": procedure.procedure_text,
                "procedure_type": procedure.procedure_type,
                "stage": procedure.stage,
                "requirement_flag": procedure.requirement_flag
            }
        }
        
        # Add detailed analysis if available
        if proc_detail:
            result["analysis"] = {
                "icd9_code": proc_detail.icd9_tindakan or "",
                "validitas": proc_detail.validitas_tindakan or "",
                "status_tindakan": proc_detail.status_tindakan or "",
                "ina_cbg": proc_detail.ina_cbg_tindakan or "",
                "faskes_tindakan": proc_detail.faskes_tindakan or "",
                "rawat_inap_tindakan": proc_detail.rawat_inap_tindakan or "",
                "syarat_klinis": proc_detail.syarat_klinis_tindakan or ""
            }
        
        # Get related regulations for this procedure
        related_regulations = db.query(models.ClaimRegulationDetail).filter(
            models.ClaimRegulationDetail.claim_id == claim_id,
            models.ClaimRegulationDetail.procedure_id == procedure.id
        ).all()
        
        if related_regulations:
            result["regulasi"] = []
            for reg in related_regulations:
                regulasi_item = {
                    "judul": reg.judul_regulasi,
                    "dasar_hukum": reg.dasar_hukum or "",
                    "bab_pasal": reg.bab_pasal or "",
                    "isi": reg.isi or ""
                }
                result["regulasi"].append(regulasi_item)
        
        result["read_only_mode"] = True
        result["message"] = f"✅ Stored procedure data loaded successfully for '{procedure_name}'"
        
        print(f"[STORED_PROCEDURE_DETAIL] ✅ Successfully loaded stored data with {len(result.get('regulasi', []))} regulations")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[STORED_PROCEDURE_DETAIL] ❌ Error loading stored data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load stored procedure detail: {str(e)}")


@router.get("/{claim_id}/stored-regulation-detail/{field_name}", name="get_stored_regulation_detail")
def get_stored_regulation_detail(
    claim_id: int,
    field_name: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator", "coder", "admin_rs", "superadmin"))
):
    """
    Read-only endpoint untuk verificator - mengambil detail regulasi yang sudah disimpan doctor.
    Data berasal dari database, bukan hit core_engine.
    """
    try:
        print(f"[STORED_REGULATION_DETAIL] Loading stored data for claim {claim_id}, field: {field_name}")
        
        # Find regulations in database related to this field/diagnosis/procedure
        regulations = db.query(models.ClaimRegulationDetail).filter(
            models.ClaimRegulationDetail.claim_id == claim_id
        ).all()
        
        # Filter by field name or related content
        relevant_regulations = []
        for reg in regulations:
            if (field_name.lower() in reg.judul_regulasi.lower() if reg.judul_regulasi else False) or \
               (field_name.lower() in reg.isi.lower() if reg.isi else False):
                relevant_regulations.append(reg)
        
        if not relevant_regulations:
            # If no specific match, return all regulations for this claim
            relevant_regulations = regulations
            
        if not relevant_regulations:
            raise HTTPException(status_code=404, detail=f"No stored regulations found for claim {claim_id} field '{field_name}'")
        
        # Build response structure
        result = {
            "status": "success",
            "mode": "stored_data",
            "claim_id": claim_id,
            "field_name": field_name,
            "regulations": []
        }
        
        # Group regulations by type
        for reg in relevant_regulations:
            regulasi_item = {
                "id": reg.id,
                "judul": reg.judul_regulasi or "",
                "dasar_hukum": reg.dasar_hukum or "",
                "bab_pasal": reg.bab_pasal or "",
                "isi": reg.isi or "",
                "created_at": reg.created_at.isoformat() if reg.created_at else "",
                "related_to": "diagnosis" if reg.diagnosis_id else ("procedure" if reg.procedure_id else "general")
            }
            result["regulations"].append(regulasi_item)
        
        # Sort by creation date (newest first)
        result["regulations"].sort(key=lambda x: x["created_at"], reverse=True)
        
        result["read_only_mode"] = True
        result["total_count"] = len(result["regulations"])
        result["message"] = f"✅ Found {len(result['regulations'])} stored regulations for '{field_name}'"
        
        print(f"[STORED_REGULATION_DETAIL] ✅ Successfully loaded {len(result['regulations'])} regulations")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[STORED_REGULATION_DETAIL] ❌ Error loading stored data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load stored regulation detail: {str(e)}")


@router.get("/{claim_id}/stored-data-summary", name="get_stored_data_summary")
def get_stored_data_summary(
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator", "coder", "admin_rs", "superadmin"))
):
    """
    Read-only endpoint untuk verificator - mengambil ringkasan semua data yang sudah disimpan doctor.
    Berguna untuk overview sebelum membuka modal detail.
    """
    try:
        print(f"[STORED_DATA_SUMMARY] Loading stored data summary for claim {claim_id}")
        
        result = {
            "status": "success",
            "mode": "stored_data_summary",
            "claim_id": claim_id,
            "summary": {}
        }
        
        # Get all diagnoses with basic info
        diagnoses = db.query(models.ClaimDiagnosis).filter(
            models.ClaimDiagnosis.claim_id == claim_id,
            models.ClaimDiagnosis.is_deleted == False
        ).all()
        
        result["summary"]["diagnoses"] = []
        for diag in diagnoses:
            diag_summary = {
                "id": diag.id,
                "name": diag.diagnosis_text,
                "type": diag.diagnosis_type,
                "icd10_code": diag.icd10_code or "",
                "has_details": bool(diag.justifikasi or diag.syarat_klinis or diag.bukti_klinis),
                "clickable": True  # Can open modal
            }
            result["summary"]["diagnoses"].append(diag_summary)
        
        # Get all procedures with basic info
        procedures = db.query(models.ClaimProcedure).filter(
            models.ClaimProcedure.claim_id == claim_id,
            models.ClaimProcedure.is_deleted == False
        ).all()
        
        result["summary"]["procedures"] = []
        for proc in procedures:
            # Check if has details
            has_details = db.query(models.ClaimProcedureDetail).filter(
                models.ClaimProcedureDetail.procedure_id == proc.id,
                models.ClaimProcedureDetail.is_deleted == False
            ).first() is not None
            
            proc_summary = {
                "id": proc.id,
                "name": proc.procedure_text,
                "type": proc.procedure_type,
                "stage": proc.stage,
                "has_details": has_details,
                "clickable": True  # Can open modal
            }
            result["summary"]["procedures"].append(proc_summary)
        
        # Get regulations count
        regulations_count = db.query(models.ClaimRegulationDetail).filter(
            models.ClaimRegulationDetail.claim_id == claim_id
        ).count()
        
        result["summary"]["regulations"] = {
            "total_count": regulations_count,
            "available": regulations_count > 0
        }
        
        # Get IDRG data
        idrg_diagnosis = db.query(models.ClaimIDRGDiagnosis).filter(
            models.ClaimIDRGDiagnosis.claim_id == claim_id,
            models.ClaimIDRGDiagnosis.is_deleted == False
        ).all()
        
        result["summary"]["idrg"] = {
            "diagnosis_count": len(idrg_diagnosis),
            "available": len(idrg_diagnosis) > 0,
            "groups": [idrg.group_idrg for idrg in idrg_diagnosis if idrg.group_idrg]
        }
        
        # Overall statistics
        result["summary"]["statistics"] = {
            "total_diagnoses": len(diagnoses),
            "total_procedures": len(procedures),
            "modal_procedures": len([p for p in procedures if p.procedure_type in ["modal_diagnosis", "modal_procedure"]]),
            "total_regulations": regulations_count,
            "idrg_records": len(idrg_diagnosis),
            "data_richness_score": min(100, (len(diagnoses) * 10 + len(procedures) * 8 + regulations_count * 5 + len(idrg_diagnosis) * 15))
        }
        
        result["read_only_mode"] = True
        result["message"] = f"✅ Summary loaded: {len(diagnoses)} diagnoses, {len(procedures)} procedures, {regulations_count} regulations"
        
        print(f"[STORED_DATA_SUMMARY] ✅ Successfully loaded summary with richness score: {result['summary']['statistics']['data_richness_score']}")
        
        return result
        
    except Exception as e:
        print(f"[STORED_DATA_SUMMARY] ❌ Error loading stored data summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load stored data summary: {str(e)}")

