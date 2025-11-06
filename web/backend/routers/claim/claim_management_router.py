"""
routers/claim/claim_management_router.py
Fokus: halaman manajemen klaim & workflow dokter/coder/verifikator.
Refactor dari claim_router lama (HTML view, bukan API JSON).
"""

from fastapi import APIRouter, Request, Form, Query, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from starlette.responses import RedirectResponse
from backend.database import get_db
from backend.auth import require_roles_session, require_csrf_dep, issue_csrf_token
from backend import models, form_configs
from backend.services.claim import core, ai
from backend.crud import claim as claim_crud
from backend.services.claim_stage_helper import determine_stages_from_visits
from backend.services.claim.simulation import load_sim_and_summary, load_existing_mappings, apply_mappings_to_simulasi
from backend.utils.templates import templates 
from backend.utils.flash import flash
from datetime import datetime
import json

router = APIRouter(tags=["Claim Management"])


# ==================================================
# 🏥 MANAGERIAL: EPISODE & KLAIM (ADMIN/MANAJEMEN)
# ==================================================
@router.get("/manage")
def manage_claims_page(
    request: Request,
    patient_id: int = Query(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs", "superadmin", "doctor", "manajemen")),
):
    """Halaman manajemen klaim pasien (dengan orphaned claims)."""
    patient = db.query(models.Patient).filter_by(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")

    groups = (
        db.query(models.ClaimGroup)
        .filter(models.ClaimGroup.patient_id == patient_id)
        .options(
            joinedload(models.ClaimGroup.claims)
            .joinedload(models.Claim.visit)
            .joinedload(models.Visit.hospital),
            joinedload(models.ClaimGroup.claims).joinedload(models.Claim.visit_links),
        )
        .order_by(models.ClaimGroup.created_at.desc())
        .all()
    )

    orphaned_claims = db.query(models.Claim).filter(
        models.Claim.patient_id == patient_id,
        models.Claim.group_id == None,
        models.Claim.is_deleted == False,
    ).all()

    total_claims = sum(len(g.claims) for g in groups) + len(orphaned_claims)

    all_visits = (
        db.query(models.Visit)
        .filter(models.Visit.patient_id == patient_id)
        .options(joinedload(models.Visit.hospital))
        .order_by(models.Visit.tanggal_kunjungan.desc())
        .all()
    )

    claimed_visit_ids = set()
    for group in groups:
        for claim in group.claims:
            if claim.visit_id:
                claimed_visit_ids.add(claim.visit_id)
            for link in claim.visit_links:
                try:
                    claimed_visit_ids.add(int(link.external_visit_id))
                except (ValueError, TypeError):
                    continue
    for claim in orphaned_claims:
        if claim.visit_id:
            claimed_visit_ids.add(claim.visit_id)
        for link in claim.visit_links:
            try:
                claimed_visit_ids.add(int(link.external_visit_id))
            except (ValueError, TypeError):
                continue

    available_visits = [v for v in all_visits if v.id not in claimed_visit_ids]

    return templates.TemplateResponse(
        "claim_manage.html",
        {
            "request": request,
            "patient": patient,
            "groups": groups,
            "orphaned_claims": orphaned_claims,
            "total_claims": total_claims,
            "visits": available_visits,
            "user": user,
            "current_user": user,
            "csrf_token": issue_csrf_token(request),
        },
    )


# ==================================================
# 🧩 GROUP (EPISODE KLAIM)
# ==================================================
@router.get("/select-group")
def select_group_page(
    request: Request,
    patient_id: int = Query(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    groups = db.query(models.ClaimGroup).filter_by(patient_id=patient_id).all()
    return templates.TemplateResponse(
        "claim_group_select.html",
        {
            "request": request,
            "groups": groups,
            "patient_id": patient_id,
            "csrf_token": issue_csrf_token(request),
            "user": user,
            "current_user": user,
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
    """Pilih visit untuk klaim baru di episode tertentu."""
    all_visits = (
        db.query(models.Visit)
        .filter(models.Visit.patient_id == patient_id)
        .order_by(models.Visit.tanggal_kunjungan.desc())
        .all()
    )

    existing_claims = db.query(models.Claim).filter(
        models.Claim.patient_id == patient_id,
        models.Claim.is_deleted == False,
    ).all()

    claimed_visit_ids = set()
    for claim in existing_claims:
        if claim.visit_id:
            claimed_visit_ids.add(claim.visit_id)
        for link in claim.visit_links:
            try:
                claimed_visit_ids.add(int(link.external_visit_id))
            except (ValueError, TypeError):
                continue

    available_visits = [v for v in all_visits if v.id not in claimed_visit_ids]
    group = db.query(models.ClaimGroup).get(group_id)

    return templates.TemplateResponse(
        "claim_visit_select.html",
        {
            "request": request,
            "group": group,
            "visits": available_visits,
            "csrf_token": issue_csrf_token(request),
            "patient_id": patient_id,
            "flow": "claim",
            "current_user": user,
            "user": user,
        },
    )


@router.get("/group/{group_id}")
def group_detail_page(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    group = db.query(models.ClaimGroup).get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group tidak ditemukan")

    claims = (
        db.query(models.Claim)
        .filter(models.Claim.group_id == group_id)
        .order_by(models.Claim.created_at.desc())
        .all()
    )

    total = len(claims)
    selesai = len([c for c in claims if c.workflow_status == "finalized"])

    return templates.TemplateResponse(
        "claim_group_detail.html",
        {
            "request": request,
            "group": group,
            "claims": claims,
            "total_klaim": total,
            "selesai": selesai,
            "belum": total - selesai,
            "user": user,
            "current_user": user,
            "csrf_token": issue_csrf_token(request),
        },
    )


# ==================================================
# ➕ ADD / CREATE
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
    kode_group = f"E{int(datetime.now().timestamp())}"
    group = models.ClaimGroup(
        kode_group=kode_group,
        nama_group=nama_group_baru or f"Episode {kode_group}",
        patient_id=patient_id,
        hospital_id=hospital_id,
        created_by=user.name,
    )
    db.add(group)
    db.commit()
    flash(request, f"✅ Group '{group.nama_group}' berhasil dibuat", "success")
    return RedirectResponse(f"/claims/select-group?patient_id={patient_id}", status_code=303)


@router.post("/add")
def add_claim(
    request: Request,
    visit_id: int = Form(...),
    group_id: int | None = Form(None),
    nama_group_baru: str | None = Form(None),
    patient_id: int | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    """Tambah klaim baru (buat group baru jika belum ada)."""
    hospital_id = getattr(user.hospital, "id", None)
    if group_id:
        group = db.query(models.ClaimGroup).get(group_id)
    elif nama_group_baru and patient_id:
        kode_group = f"E{int(datetime.now().timestamp())}"
        group = models.ClaimGroup(
            kode_group=kode_group,
            nama_group=nama_group_baru,
            patient_id=patient_id,
            hospital_id=hospital_id,
            created_by=user.name,
        )
        db.add(group)
        db.commit()
    else:
        flash(request, "⚠️ Harus memilih atau membuat Group terlebih dahulu", "error")
        return RedirectResponse("/claims/select-group", status_code=303)

    claim = core.add_claim_service(db, visit_id, user, hospital_id)
    claim.group_id = group.id
    claim.workflow_status = "draft"
    db.commit()

    flash(request, f"✅ Klaim berhasil ditambahkan ke Group {group.kode_group}", "success")
    return RedirectResponse(f"/claims/{claim.id}", status_code=303)

@router.post("/add-multi", name="add_claim_multi")
def add_claim_multi(
    request: Request,
    patient_id: int = Form(...),
    visit_ids: list[str] = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    """
    Buat klaim baru dengan beberapa kunjungan (multi-visit grouping).
    ⚙️ Masih dipakai oleh beberapa RS untuk kasus bridging atau episode rawat gabungan.
    """
    print(f"🩺 [ADD_CLAIM_MULTI] patient_id={patient_id} | visits={visit_ids}")
    hospital_id = getattr(user.hospital, "id", None)

    if not visit_ids:
        raise HTTPException(status_code=400, detail="Minimal 1 kunjungan harus dipilih")

    # Visit pertama sebagai visit utama
    main_visit_id = int(visit_ids[0])
    claim = core.add_claim_service(db, main_visit_id, user, hospital_id)
    if not claim:
        raise HTTPException(status_code=400, detail="Visit utama tidak valid.")

    # Set workflow status awal
    claim.workflow_status = "draft"

    # Tambahkan kunjungan tambahan (secondary visits)
    for vid in visit_ids[1:]:
        link = models.ClaimVisitLink(
            claim_id=claim.id,
            external_visit_id=str(vid),
            hospital_id=hospital_id,
        )
        db.add(link)

    db.commit()
    db.refresh(claim)

    flash(request, f"✅ Klaim multi-kunjungan berhasil dibuat ({len(visit_ids)} visits)", "success")
    print(f"✅ [ADD_CLAIM_MULTI] Claim {claim.id} dengan {len(visit_ids)} visit tersimpan")

    return RedirectResponse(url=f"/claims/{claim.id}", status_code=303)

# ======================================================
# 📄 CLAIM DETAIL VIEW (HTML)
# ======================================================
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

    coder_results = db.query(models.ClaimSimulation).filter(
        models.ClaimSimulation.claim_id == claim_id,
        models.ClaimSimulation.coder_verified == True
    ).all()

    approved_mappings = {}
    user_roles = user.role_names if hasattr(user, "role_names") else [user.role] if user.role else []

    if "verifikator" in user_roles:
        from backend.services.claim import simulation as sim_service
        approved_mappings = sim_service.get_simulations_for_verificator(db, claim_id)

    return templates.TemplateResponse(
        "claim_detail.html",
        {
            "request": request,
            "claim": claim,
            "user": user,
            "csrf_token": issue_csrf_token(request),
            "current_user": user,
            "coder_results": coder_results,
            "approved_mappings": approved_mappings,
        },
    )

# ==================================================
# ✏️ EDIT & DRAFT UPDATE
# ==================================================
@router.get("/{claim_id}/edit")
def edit_claim_form(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator", "coder", "doctor")),
):
    """Form edit klaim (multi-role aware)"""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    csrf_token = issue_csrf_token(request)
    roles = user.role_names or []
    has_doctor, has_coder, has_verifikator = (
        "doctor" in roles,
        "coder" in roles,
        "verifikator" in roles,
    )
    total_roles = sum([has_doctor, has_coder, has_verifikator])

    # 🔹 Tentukan template berdasarkan role
    if total_roles > 1:
        template_name = "claim_combine.html"
    elif has_verifikator:
        template_name = "claim_right.html"
    elif has_coder:
        template_name = "edit_coder.html"
    else:
        template_name = "claim_left.html"

    # ================================================
    # 🔹 Ambil data simulasi dasar & mapping
    # ================================================
    sim, summ = load_sim_and_summary(db, claim_id)
    existing_mappings = load_existing_mappings(db, claim_id)
    if existing_mappings and sim and "simulasi" in sim:
        sim["simulasi"] = apply_mappings_to_simulasi(sim["simulasi"], existing_mappings)

    # ================================================
    # 🔹 Hasil verifikasi coder (untuk verifikator/multi-role)
    # ================================================
    from backend.services.claim import simulation as sim_service
    coder_results = None
    if has_verifikator or total_roles > 1:
        coder_results = db.query(models.ClaimSimulation).filter(
            models.ClaimSimulation.claim_id == claim_id,
            models.ClaimSimulation.coder_verified == True,
        ).all()

    # ================================================
    # 🔹 Tentukan stages
    # ================================================
    visits = (
        [db.query(models.Visit).get(claim.visit_id)]
        if claim.visit_id
        else db.query(models.Visit)
        .filter(models.Visit.patient_id == claim.patient_id)
        .order_by(models.Visit.tanggal_kunjungan.desc())
        .limit(1)
        .all()
    )
    stages = determine_stages_from_visits(visits)

    # ================================================
    # 🔹 Kalau role CODER → ambil data penuh dari simulation.py
    # ================================================
    if has_coder and not has_doctor and not has_verifikator:
        from backend.services.claim.simulation import get_simulations_for_coder
        stage_groups = get_simulations_for_coder(db, claim_id)
    else:
        # fallback lama
        if isinstance(stages, list):
            stage_groups = {s: {"diagnosis": [], "procedure": []} for s in stages}
        else:
            stage_groups = stages or {}

    # ================================================
    # 🔹 Bangun context
    # ================================================
    context = {
        "request": request,
        "record": claim,
        "claim": claim,
        "sim": sim,
        "summ": summ,
        "stages": stage_groups,
        "csrf_token": csrf_token,
        "user": user,
        "current_user": user,
        "roles": roles,
        "coder_results": coder_results,
        "claim_medical_record_fields": form_configs.form_configs["claim_medical_record"],
    }

    # ================================================
    # 🔹 Load data rekam medis (jika ada)
    # ================================================
    existing_medical_data = {}
    if claim.medical_record_id:
        medical_record = db.query(models.MedicalRecord).get(claim.medical_record_id)
        if medical_record:
            for field in form_configs.form_configs["claim_medical_record"]:
                fname = field.get("name")
                if fname and hasattr(medical_record, fname):
                    existing_medical_data[fname] = getattr(medical_record, fname)
    context["existing_medical_data"] = existing_medical_data

    # ================================================
    return templates.TemplateResponse(template_name, context)



@router.post("/{claim_id}/update-draft")
async def update_claim_draft(
    request: Request,
    claim_id: int,
    payload: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    """Update draft klaim oleh dokter."""
    try:
        payload_dict = json.loads(payload)
        ai_recs = payload_dict.get("ai_recommendations")
        stage = payload_dict.get("stage", "admission")

        if ai_recs:
            ai.clear_ai_results(db, claim_id)
            ai.store_ai_recommendations(db, claim_id, ai_recs, "predict", stage)

        claim = db.query(models.Claim).get(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")

        original_group = claim.group_id
        core.update_claim_draft_service(db, claim_id, user, payload_dict)
        db.refresh(claim)

        if claim.group_id != original_group:
            claim.group_id = original_group
        if claim.workflow_status in [None, "", "draft"]:
            claim.workflow_status = "doctor_submitted"
            claim.doctor_submitted_by = user.name
            claim.doctor_submitted_at = datetime.now()

        db.commit()
        return {"status": "success", "message": "Draft klaim berhasil diperbarui"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save draft: {str(e)}")


# ==================================================
# 🔄 WORKFLOW (SUBMIT / FINALIZE)
# ==================================================
@router.post("/{claim_id}/submit-to-coder")
def submit_to_coder(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),
):
    """Submit klaim ke coder."""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    count = db.query(models.ClaimSimulation).filter_by(claim_id=claim_id).count()
    if count == 0:
        flash(request, "⚠️ Minimal harus ada 1 diagnosis sebelum submit ke coder", "error")
        return RedirectResponse(f"/claims/{claim_id}/edit", status_code=303)

    claim.workflow_status = "doctor_submitted"
    claim.doctor_submitted_at = datetime.now()
    claim.doctor_submitted_by = user.name
    db.commit()

    flash(request, "✅ Klaim berhasil disubmit ke Coder", "success")
    return RedirectResponse("/claims", status_code=303)


@router.post("/{claim_id}/finalize")
async def finalize_claim(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator")),
    _=Depends(require_csrf_dep),
):
    """Finalize klaim oleh verifikator (bisa bypass jika multi-role)."""
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    roles = user.role_names or []
    bypass = "doctor" in roles and "verifikator" in roles

    if not bypass and claim.workflow_status != "coder_verified":
        flash(request, "⚠️ Klaim harus diverifikasi coder dulu", "error")
        return RedirectResponse(f"/claims/{claim_id}", status_code=303)

    form_data = await request.form()
    form_dict = dict(form_data)

    try:
        core.finalize_claim_service(db, claim_id, user, form_dict)
        claim.workflow_status = "finalized"
        claim.finalized_at = datetime.now()
        claim.finalized_by = user.name
        db.commit()
        flash(request, "✅ Klaim berhasil difinalisasi", "success")
    except Exception as e:
        db.rollback()
        flash(request, f"❌ Gagal finalize klaim: {str(e)}", "error")

    return RedirectResponse("/dashboard", status_code=303)


# ==================================================
# 🗑️ DELETE
# ==================================================
@router.post("/{claim_id}/delete")
def delete_claim(
    claim_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "verifikator", "admin_rs", "superadmin")),
    _=Depends(require_csrf_dep),
):
    claim = db.query(models.Claim).get(claim_id)
    if claim and "doctor" in user.role_names and claim.created_by != user.name:
        flash(request, "⚠️ Anda hanya bisa hapus klaim yang Anda buat", "error")
        return RedirectResponse("/claims", status_code=303)

    claim_crud.delete_claim(db, claim_id)
    flash(request, "✅ Klaim berhasil dihapus", "success")
    return RedirectResponse("/claims", status_code=303)
