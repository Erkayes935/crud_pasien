"""
Module: backend.main

This is the FastAPI application entrypoint. It defines route handlers that
render Jinja2 templates, handle Auth0 login/callback, and provide CRUD
endpoints for Patient records. The module also implements import/export
helpers (JSON import, Excel export) using openpyxl and streams responses to
clients. Database tables are created at startup via SQLAlchemy's
`Base.metadata.create_all` (requires DB privileges).

Keep this file focused on HTTP routing and view rendering. Business logic
and DB operations live in `crud.py` and models are in `models.py`.
"""

from fastapi import FastAPI, Depends, Request, Form, UploadFile, File, HTTPException, Query, APIRouter
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_ 
from sqlalchemy.orm import Session, joinedload
from urllib.parse import urlencode
from datetime import datetime, date
from openpyxl import Workbook, load_workbook
from typing import Optional
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from jose import jwt, JWTError
from . import models, crud, config
from .database import SessionLocal, engine, Base
from .auth import verify_jwt, get_db, require_roles_session, issue_csrf_token, require_csrf_dep
import requests, io, json, secrets, base64, hashlib, httpx

# Init DB & App
Base.metadata.create_all(bind=engine)
app = FastAPI()
templates = Jinja2Templates(directory="frontend/templates")
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET, same_site="lax", https_only=False)
ISSUER = lambda: f"https://{config.AUTH0_DOMAIN}/"
ALGS = ["RS256"]

def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def _fetch_jwks():
    resp = requests.get(
        f"https://{config.AUTH0_DOMAIN}/.well-known/jwks.json",
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()

# -------------------------
# AUTH ROUTES
# -------------------------
@app.get("/welcome")
def welcome(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})

@app.get("/login")
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/auth/login")
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    token_url = f"https://{config.AUTH0_DOMAIN}/oauth/token"
    data = {
        "grant_type": "http://auth0.com/oauth/grant-type/password-realm",
        "username": email,
        "password": password,
        "audience": config.AUDIENCE,
        "scope": "openid profile email",
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "realm": "Username-Password-Authentication"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(token_url, data=data)

    if res.status_code != 200:
        raise HTTPException(status_code=401, detail=f"Login failed: {res.text}")

    tokens = res.json()
    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(status_code=401, detail="No id_token returned")

    payload = verify_jwt(id_token, expected_aud=config.CLIENT_ID)

    sub = payload["sub"]
    email = payload.get("email") or email

    user = db.query(models.User).filter_by(auth0_sub=sub).first()
    if not user:
        user = models.User(auth0_sub=sub, email=email, role="doctor")
        db.add(user); db.commit(); db.refresh(user)

    request.session["user_id"] = user.id
    request.session["sub"] = sub
    request.session["email"] = email
    request.session["roles"] = [user.role]

    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/logout")
def logout():
    params = {
        "client_id": config.CLIENT_ID,
        "returnTo": "http://localhost:8000/welcome"
    }
    url = f"https://{config.AUTH0_DOMAIN}/v2/logout?" + urlencode(params)
    response = RedirectResponse(url)
    response.delete_cookie("id_token")
    return response


# -------------------------
# PATIENT CRUD ROUTES
# -------------------------

@app.get("/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator")),
):
    # hitung umum
    total_pasien = db.query(models.Patient).count()
    pasien_hari_ini = db.query(models.Claim).filter(
        func.date(models.Claim.tanggal_kunjungan) == datetime.today().date()
    ).count()
    total_claims = db.query(models.Claim).count()
    claims = (
        db.query(models.Claim)
        .order_by(models.Claim.id.desc())   # urutkan dari yang terbaru
        .limit(10)                           # ambil hanya 10 klaim
        .all()
    )
    draft_claims = db.query(models.Claim).filter(models.Claim.status == "draft").count()
    verified_claims = db.query(models.Claim).filter(models.Claim.status == "verified").count()
    submitted_claims = db.query(models.Claim).filter(models.Claim.status == "submitted").count()

    # role check
    if current_user.role in ["doctor", "coder", "verifikator"]:
        pasien_list = db.query(models.Patient).all()
    else:
        pasien_list = []   # superadmin/admin_rs tidak melihat pasien

    # total users hanya untuk superadmin/admin_rs
    total_users = db.query(models.User).count() if current_user.role in ["superadmin","admin_rs"] else None

    csrf_token = issue_csrf_token(request)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "current_user": current_user,
        "total_pasien": total_pasien,
        "pasien_hari_ini": pasien_hari_ini,
        "total_claims": total_claims,
        "claims": claims,
        "draft_claims": draft_claims,
        "verified_claims": verified_claims,
        "submitted_claims": submitted_claims,
        "total_users": total_users,
        "pasien_list": pasien_list,
        "csrf_token": csrf_token
    })

@app.get("/")
def root_redirect(user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))):
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/patients")
def list_patients(request: Request, flow: str = None, search: str | None = Query(None), mode: str | None = Query(None), db: Session = Depends(get_db), user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))):
    query = db.query(models.Patient)

    # filter jika ada search
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                func.lower(func.trim(models.Patient.nama)).like(pattern.lower()),
                func.lower(func.trim(models.Patient.no_ktp)).like(pattern.lower()),
                func.lower(func.trim(models.Patient.no_rm)).like(pattern.lower()),
                func.lower(func.trim(models.Patient.no_bpjs)).like(pattern.lower())
            )
        )

    patients = query.order_by(models.Patient.id.desc()).all()
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("patient_list.html", {
        "request": request,
        "patients": patients,
        "user": user,
        "mode": mode,
        "flow": flow,
        "current_user": user,
        "csrf_token": csrf_token
    })


@app.get("/patients/add",name="add_patient")
def add_form(request: Request, user=Depends(require_roles_session("doctor"))):
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("patient_form.html", {"request": request, "mode": "add", "patient": None, "csrf_token": csrf_token, "user": user, "current_user": user})


@app.post("/patients/add",name="add_patient")
def add_patient(
    request: Request,
    flow: Optional[str] = None,
    no_ktp: Optional[str] = Form(...),
    no_bpjs: Optional[str] = Form(...),
    no_rm: Optional[str] = Form(...),
    nama: str = Form(...),
    tanggal_lahir: Optional[str] = Form(None),
    jenis_kelamin: Optional[str] = Form(None),
    alamat: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    no_hp: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep)
):
    try:
        crud.create_patient(db, {
            "no_ktp": no_ktp or None,
            "no_bpjs": no_bpjs or None,
            "no_rm": no_rm or None,
            "nama": nama,
            "tanggal_lahir": tanggal_lahir or None,
            "jenis_kelamin": jenis_kelamin or None,
            "alamat": alamat or None,
            "email": email or None,
            "no_hp": no_hp or None
        })
        success_msg = "Pasien berhasil ditambahkan!"
        return RedirectResponse(url="/patients", status_code=303)
    except Exception as e:
        error_msg = f"Gagal menambahkan pasien: {str(e)}"
        return templates.TemplateResponse("patient_form.html", {
            "request": request,
            "mode": "add",
            "patient": {
                "nama": nama,
                "tanggal_lahir": tanggal_lahir,
                "jenis_kelamin": jenis_kelamin,
                "alamat": alamat,
                "email": email,
                "no_hp": no_hp,
                "no_ktp": no_ktp,
                "no_bpjs": no_bpjs,
                "no_rm": no_rm
            },
            "user": user,
            "current_user": user,
            "error_msg": error_msg
        })

@app.get("/patients/edit/{patient_id}",name="edit_patient")
def edit_form(patient_id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor"))):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("patient_form.html", {"request": request, "mode": "edit", "patient": patient, "csrf_token": csrf_token, "user": user, "current_user": user})


@app.post("/patients/edit/{patient_id}",name="update_patient")
def update_patient(
    patient_id: int,
    request: Request,
    flow: Optional[str] = None,
    no_ktp: Optional[str] = Form(...),
    no_bpjs: Optional[str] = Form(...),
    no_rm: Optional[str] = Form(...),
    nama: str = Form(...),
    tanggal_lahir: Optional[str] = Form(None),
    jenis_kelamin: Optional[str] = Form(None),
    alamat: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    no_hp: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep)
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        error_msg = "Pasien tidak ditemukan"
        return templates.TemplateResponse("patient_form.html", {
            "request": request,
            "mode": "edit",
            "patient": None,
            "user": user,
            "current_user": user,
            "error_msg": error_msg
        })
    try:
        crud.update_patient(db, patient_id, {
            "no_ktp": no_ktp or None,
            "no_bpjs": no_bpjs or None,
            "no_rm": no_rm or None,
            "nama": nama,
            "tanggal_lahir": tanggal_lahir or None,
            "alamat": alamat or None,
            "jenis_kelamin": jenis_kelamin or None,
            "email": email or None,
            "no_hp": no_hp or None
        })
        success_msg = "Data pasien berhasil diperbarui!"
        return RedirectResponse(url="/patients", status_code=303)
    except Exception as e:
        error_msg = f"Gagal memperbarui pasien: {str(e)}"
        return templates.TemplateResponse("patient_form.html", {
            "request": request,
            "mode": "edit",
            "patient": {
                "id": patient_id,
                "no_ktp": no_ktp,
                "no_bpjs": no_bpjs,
                "no_rm": no_rm,
                "nama": nama,
                "tanggal_lahir": tanggal_lahir,
                "jenis_kelamin": jenis_kelamin,
                "alamat": alamat,
                "email": email,
                "no_hp": no_hp
            },
            "user": user,
            "current_user": user,
            "error_msg": error_msg
        })


@app.get("/patients/delete/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor"))):
    crud.delete_patient(db, patient_id)
    csrf_token = issue_csrf_token(request)
    return RedirectResponse("/patients", status_code=303)


@app.get("/export")
def export_patients(db: Session = Depends(get_db), user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))):
    patients = db.query(models.Patient).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Patients"
    ws.append(["Nama", "Tanggal Lahir", "Nomor HP", "Alamat", "Email", "No KTP", "No BPJS", "No Rekam Medis"])
    for p in patients:
        ws.append([p.nama, p.tanggal_lahir, p.no_hp, p.alamat, p.email, p.no_ktp, p.no_bpjs, p.no_rekam_medis])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=patients.xlsx"}
    )


@app.post("/import")
def import_patients(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are allowed")
    data = json.load(file.read())
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    for item in data:
        crud.create_patient(db, {
            "nama": item.get("nama"),
            "tanggal_lahir": item.get("tanggal_lahir"),
            "diagnosis": item.get("diagnosis", ""),
            "tindakan": item.get("tindakan", ""),
            "dokter": item.get("dokter", "")
        })
    csrf_token = issue_csrf_token(request)
    return {"status": "success", "count": len(data), "csrf_token": csrf_token}


# -------------------------
# CLAIM ROUTES
# -------------------------
@app.get("/claims")
def list_claims(
    request: Request,
    status: str | None = Query(None),
    tanggal_kunjungan: str | None = Query(None),
    patient_name: str | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))
):
    query = db.query(models.Claim)
    # filter jika ada status

    if status:
        query = query.filter(models.Claim.status.ilike(status))  # case-insensitive

    if tanggal_kunjungan:
        query = query.filter(models.Claim.tanggal_kunjungan == tanggal_kunjungan)

    if patient_name:
        query = query.join(models.Patient).filter(
        models.Patient.nama.ilike(f"%{patient_name}%")
    )

    claims = query.order_by(models.Claim.id.desc()).all()
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "claim_list.html",
        {"request": request, 
        "claims": claims, 
        "user": user, 
        "csrf_token": csrf_token, 
        "current_user": user,
        "status": status,
        "tanggal_kunjungan": tanggal_kunjungan,
        "patient_name": patient_name
    }
)

@app.get("/claims/export", name="export_claims")
def export_claims(
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","coder","verifikator","admin_rs","superadmin"))
):
    query = db.query(models.Claim).join(models.Patient)
    if status:
        query = query.filter(models.Claim.status == status)
    if start_date:
        query = query.filter(models.Claim.tanggal_kunjungan >= start_date)
    if end_date:
        query = query.filter(models.Claim.tanggal_kunjungan <= end_date)
    claims = query.all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Claims"
    ws.append([
        "ID Klaim",
        "Nama Pasien",
        "Tanggal Kunjungan",
        "Jenis Kunjungan",
        "Dokter",
        "Diagnosis Awal",
        "Kode ICD",
        "Tindakan",
        "Obat",
        "Status",
        "Hasil",
        "Created By",
        "Created At"
    ])
    for c in claims:
        ws.append([
            c.patient.id if c.patient else '-',
            c.patient.nama if c.patient else '-',
            c.tanggal_kunjungan.isoformat() if c.tanggal_kunjungan else '',
            c.doctor_name or '',
            c.diagnosis_awal or '',
            c.kode_icd or '',
            c.tindakan or '',
            c.obat or '',
            c.status or '',
            c.hasil or '',
            c.creator.email or '',
            c.created_at.isoformat() if c.created_at else '',
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

@app.get("/claims/{claim_id}")
def claim_detail(request: Request, claim_id: int, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))):
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return templates.TemplateResponse(
        "claim_detail.html",
        {"request": request, "claim": claim, "user": user, "current_user": user}
    )


@app.post("/claims/add")
def add_claim(
    csrf_token: Optional[str] = Form(None),
    patient_id: Optional[int] = Form(None),
    visit_id: Optional[int] = Form(None),
    hospital_id: Optional[int] = Form(None),
    tanggal_kunjungan: str = Form(...),
    doctor_id: Optional[str] = Form(None),
    doctor_name: Optional[str] = Form(None),
    diagnosis_awal: Optional[str] = Form(None),
    kode_icd: Optional[str] = Form(None),
    tindakan: Optional[str] = Form(None),
    obat: Optional[str] = Form(None),
    status: Optional[str] = Form("draft"),
    hasil: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","coder")),
    _=Depends(require_csrf_dep)
):
    claim = models.Claim(
        patient_id=patient_id or None,
        visit_id=visit_id or None,
        hospital_id=hospital_id or None,
        tanggal_kunjungan=tanggal_kunjungan,
        doctor_id=doctor_id or None,
        doctor_name=doctor_name or None,
        diagnosis_awal=diagnosis_awal or None,
        kode_icd=kode_icd or None,
        tindakan=tindakan or None,
        obat=obat or None,
        status=status or "draft",
        hasil=hasil or None,
        created_by=user.id
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/claims/add/start")
def add_claim_start():
    """Redirect dari dashboard ke daftar pasien (mode klaim)"""
    return RedirectResponse("/patients?mode=claim")

@app.get("/claims/add/form/{visit_id}")
def claim_form(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_roles_session("doctor")),
    patient_id: int = None
):
    visit = db.query(models.Visit).get(visit_id) if visit_id != 0 else None

    patient = None
    if visit:  # kalau ada visit, ambil dari relasi
        patient = visit.patient
    elif patient_id:  # kalau wizard tanpa visit
        patient = db.query(models.Patient).get(patient_id)

    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "claim_form.html",
        {
            "request": request,
            "visit": visit,
            "patient": patient,
            "mode": "add",
            "claim": None,
            "current_user": user,
            "csrf_token": csrf_token,
        }
    )

@app.get("/claims/{id}/edit")
def edit_claim_form(request: Request, id: int, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor","coder"))):
    claim = db.query(models.Claim).get(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    patients = db.query(models.Patient).all()
    visits = db.query(models.Visit).all()
    hospitals = db.query(models.Hospital).all()
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "claim_form.html",
        {"request": request, "mode": "edit", "claim": claim, "patients": patients, "visits": visits, "hospitals": hospitals, "csrf_token": csrf_token, "current_user": user}
    )


@app.post("/claims/{id}/edit", name="update_claim")
def update_claim(
    id: int,
    patient_id: int = Form(...),
    visit_id: Optional[int] = Form(None),
    hospital_id: Optional[int] = Form(None),
    tanggal_kunjungan: str = Form(...),
    doctor_id: Optional[int] = Form(None),
    doctor_name: Optional[str] = Form(None),
    diagnosis_awal: Optional[str] = Form(None),
    kode_icd: Optional[str] = Form(None),
    tindakan: Optional[str] = Form(None),
    obat: Optional[str] = Form(None),
    status: Optional[str] = Form("draft"),
    hasil: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","coder")),
    _=Depends(require_csrf_dep)
):
    claim = db.query(models.Claim).get(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    claim.patient_id = patient_id
    claim.visit_id = visit_id or None
    claim.hospital_id = hospital_id or None
    claim.tanggal_kunjungan = tanggal_kunjungan
    claim.doctor_id = doctor_id or None
    claim.doctor_name = doctor_name or None
    claim.diagnosis_awal = diagnosis_awal or None
    claim.kode_icd = kode_icd or None
    claim.tindakan = tindakan or None
    claim.obat = obat or None
    claim.status = status or None
    claim.hasil = hasil or None
    db.commit()
    db.refresh(claim)
    return RedirectResponse(url="/claims", status_code=303)

@app.get("/claims/{id}/delete")
def delete_claim(
    id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","coder"))
):
    claim = db.query(models.Claim).get(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    db.delete(claim)
    db.commit()
    return RedirectResponse(url="/claims", status_code=303)


# -------------------------
# USER MANAGEMENT ROUTES (NEW)
# -------------------------
@app.get("/users")
def list_users(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles_session("superadmin", "admin_rs"))):
    users = db.query(models.User).order_by(models.User.id.desc()).all()
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "user_list.html",
        {"request": request, "users": users, "user": current_user, "current_user": current_user, "csrf_token": csrf_token}
    )

@app.get("/users/add")
def add_user_form(request: Request, current_user=Depends(require_roles_session("superadmin", "admin_rs"))):
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "user_form.html",
        {"request": request, "mode": "add", "user": current_user, "current_user": current_user, "csrf_token": csrf_token}
    )


@app.post("/users/add", name="add_user")
def add_user(
    email: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep)
):
    if role not in ["admin_rs", "doctor", "coder", "verifikator", "costing", "validator", "manajemen"]:
        raise HTTPException(status_code=400, detail="Role tidak valid")
    user = models.User(email=email, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return RedirectResponse(url="/users", status_code=303)

@app.get("/users/{user_id}/edit", name="edit_user")
def edit_user_form(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs"))
):
    target_user = db.query(models.User).get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "user_form.html",
        {
            "request": request,
            "mode": "edit",
            "target_user": target_user,   # user yang mau diedit
            "current_user": current_user, # user login
            "user": current_user,         # supaya base.html bisa render navbar
            "csrf_token": csrf_token
        }
    )

@app.post("/users/{user_id}/edit", name='edit_user')
def edit_user(
    user_id: int,
    email: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep)
):
    if role not in ["admin_rs", "doctor", "coder", "verifikator", "costing", "validator", "manajemen"]:
        raise HTTPException(status_code=400, detail="Role tidak valid")
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.email = email
    user.role = role
    db.commit()
    db.refresh(user)
    return RedirectResponse(url="/users", status_code=303)

@app.get("/users/{user_id}/delete", name="delete_user")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs"))
):
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return RedirectResponse(url="/users", status_code=303)

# -------------------------
# VISIT ROUTES (END)
# -------------------------

@app.get("/visits")
def list_visits(request: Request, search: str | None = Query(None), db: Session = Depends(get_db), user=Depends(require_roles_session("doctor", "admin_rs"))):
    query = db.query(models.Visit)
    if search:
        query = query.filter(
            models.Visit.dokter.ilike(f"%{search}%") |
            models.Visit.poli.ilike(f"%{search}%")
        )
    visits = query.order_by(models.Visit.id.desc()).all()
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "visit_list.html",
        {"request": request, "visits": visits, "user": user, "csrf_token": csrf_token, "current_user": user, "flow": None, "patient": None}
    )

@app.get("/patients/{patient_id}/visits")
def list_visit(
    request: Request, 
    patient_id: int, 
    db: Session = Depends(get_db), 
    search: str | None = Query(None),
    user=Depends(require_roles_session("doctor", "admin_rs")),
    flow: str = None   # <- ambil query param "flow"
):
    visits = db.query(models.Visit).filter(models.Visit.patient_id == patient_id)
    if search:
        visits = visits.filter(
            models.Visit.dokter.ilike(f"%{search}%") |
            models.Visit.poli.ilike(f"%{search}%")
        )
    visits = visits.order_by(models.Visit.id.desc()).all()
    patient = db.query(models.Patient).get(patient_id)
    return templates.TemplateResponse(
        "visit_list.html",
        {"request": request, "visits": visits, "patient": patient, "flow": flow}
    )

@app.get("/visits/add")
def add_visit_form(request: Request, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor", "admin_rs"))):
    patients = db.query(models.Patient).all()
    hospitals = db.query(models.Hospital).all()
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "visit_form.html",
        {"request": request, "mode": "add", "user": user, "patients": patients, "hospitals": hospitals, "csrf_token": csrf_token, "current_user": user}
    )

@app.post("/visits/add", name="add_visit")
def add_visit(
    patient_id: Optional[int] = Form(None),
    hospital_id: Optional[int] = Form(None),
    eksternal_id: Optional[str] = Form(None),
    sumber: Optional[str] = Form(None),
    poli: Optional[str] = Form(None),
    doctor_id: Optional[int] = Form(None),
    doctor_name: Optional[str] = Form(None),
    tanggal_kunjungan: Optional[date] = Form(None),
    jenis_kunjungan: Optional[str] = Form(None),
    created_at: Optional[datetime] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "admin_rs")),
    _=Depends(require_csrf_dep)
):
    visit = models.Visit(
        patient_id=patient_id or None,
        hospital_id=hospital_id or None,
        eksternal_id=eksternal_id or None,
        sumber=sumber or None,
        poli=poli or None,
        doctor_id=doctor_id or None,
        doctor_name=doctor_name or None,
        tanggal_kunjungan=tanggal_kunjungan or None,
        jenis_kunjungan=jenis_kunjungan or None,
        created_at=created_at or datetime.utcnow(),
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return RedirectResponse(url="/visits", status_code=303)

@app.get("/visits/{visit_id}/edit",name='edit_visit')
def edit_visit_form(request: Request, visit_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles_session("doctor", "admin_rs"))):
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    patients = db.query(models.Patient).all()
    hospitals = db.query(models.Hospital).all()
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "visit_form.html",
        {"request": request, "mode": "edit", "visit": visit, "patients": patients, "hospitals": hospitals, "csrf_token": csrf_token, "current_user": current_user}
    )

@app.post("/visits/{visit_id}/edit", name='edit_visit')
def edit_visit(
    visit_id: int,
    patient_id: Optional[int] = Form(None),
    hospital_id: Optional[int] = Form(None),
    eksternal_id: Optional[str] = Form(None),
    sumber: Optional[str] = Form(None),
    poli: Optional[str] = Form(None),
    doctor_id: Optional[int] = Form(None),
    doctor_name: Optional[str] = Form(None),
    tanggal_kunjungan: Optional[date] = Form(None),
    jenis_kunjungan: Optional[str] = Form(None),
    created_at: Optional[datetime] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "admin_rs")),
    _=Depends(require_csrf_dep)
):
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    visit.patient_id = patient_id or None
    visit.hospital_id = hospital_id or None
    visit.eksternal_id = eksternal_id or None
    visit.sumber = sumber or None
    visit.poli = poli or None
    visit.doctor_id = doctor_id or None
    visit.doctor_name = doctor_name or None
    visit.tanggal_kunjungan = tanggal_kunjungan or None
    visit.jenis_kunjungan = jenis_kunjungan or None
    visit.created_at = created_at or datetime.utcnow()
    db.commit()
    db.refresh(visit)
    return RedirectResponse(url="/visits", status_code=303)

@app.get("/visits/{visit_id}/delete", name="delete_visit")
def delete_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "admin_rs"))
):
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    db.delete(visit)
    db.commit()
    return RedirectResponse(url="/visits", status_code=303)

# -------------------------
# VISIT ROUTES (END)

# Hospital Routes

@app.get("/hospitals")
def list_hospitals(request: Request, db: Session = Depends(get_db), user=Depends(require_roles_session("superadmin","admin_rs"))):
    hospitals = db.query(models.Hospital).order_by(models.Hospital.id.desc()).all()
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "hospital_list.html",
        {"request": request, "hospitals": hospitals, "user": user, "csrf_token": csrf_token, "current_user": user}
    )


@app.get("/hospitals/add")
def add_hospital_form(request: Request, user=Depends(require_roles_session("superadmin","admin_rs"))):
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "hospital_form.html",
        {"request": request, "mode": "add", "user": user, "csrf_token": csrf_token, "current_user": user}
    )


@app.post("/hospitals/add", name="add_hospital")
def add_hospital(
    nama: str = Form(...),
    alamat: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin","admin_rs")),
    _=Depends(require_csrf_dep)
):
    hospital = models.Hospital(
        nama=nama,
        alamat=alamat,
        admin_id=current_user.id
    )
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return RedirectResponse(url="/hospitals", status_code=303)

@app.get("/hospitals/{hospital_id}/edit",name='edit_hospital')
def edit_hospital_form(request: Request, hospital_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles_session("superadmin","admin_rs"))):
    hospital = db.query(models.Hospital).get(hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "hospital_form.html",
        {"request": request, "mode": "edit", "hospital": hospital, "csrf_token": csrf_token, "current_user": current_user, "user": current_user}
    )

@app.post("/hospitals/{hospital_id}/edit", name='edit_hospital')
def edit_hospital(
    hospital_id: int,
    nama: str = Form(...),
    alamat: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin","admin_rs")),
    _=Depends(require_csrf_dep)
):
    hospital = db.query(models.Hospital).get(hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    hospital.nama = nama
    hospital.alamat = alamat
    db.commit()
    db.refresh(hospital)
    return RedirectResponse(url="/hospitals", status_code=303)

@app.get("/hospitals/{hospital_id}/delete", name='delete_hospital')
def delete_hospital(
    hospital_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin","admin_rs"))
):
    hospital = db.query(models.Hospital).get(hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    db.delete(hospital)
    db.commit()
    return RedirectResponse(url="/hospitals", status_code=303)

#---------------------
# End Hospital Routes
#---------------------

# Medical Record Routes

@app.get("/medical-records")
def list_medical_records(request: Request, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor", "admin_rs"))):
    medical_records = db.query(models.MedicalRecord).order_by(models.MedicalRecord.id.desc()).all()
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "medical_record_list.html",
        {"request": request, "medical_records": medical_records, "user": user, "csrf_token": csrf_token, "current_user": user}
    )


@app.get("/medical-records/add")
def add_medical_record_form(request: Request, user=Depends(require_roles_session("doctor", "admin_rs"))):
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "medical_record_form.html",
        {"request": request, "mode": "add", "user": user, "csrf_token": csrf_token, "current_user": user}
    )


@app.post("/medical-records/add", name="add_medical_record")
def add_medical_record(
    patient_name: Optional[str] = Form(...),
    visit_date: Optional[str] = Form(...),
    doctor_name: Optional[str] = Form(...),
    medical_history: Optional[str] = Form(...),
    tindakan: Optional[str] = Form(...),
    obat: Optional[str] = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "admin_rs")),
    _=Depends(require_csrf_dep)
):
    medical_record = models.MedicalRecord(
        patient_name=patient_name or None,
        visit_date=visit_date or None,
        doctor_name=doctor_name or None,
        medical_history=medical_history or None,
        tindakan=tindakan or None,
        obat=obat or None,
        created_by=current_user.id
    )
    db.add(medical_record)
    db.commit()
    db.refresh(medical_record)
    return RedirectResponse(url="/medical_records", status_code=303)

@app.get("/medical-records/{record_id}/edit", name="edit_medical_record")
def edit_medical_record_form(request: Request, record_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles_session("doctor", "admin_rs"))):
    medical_record = db.query(models.MedicalRecord).get(record_id)
    if not medical_record:
        raise HTTPException(status_code=404, detail="Medical record not found")
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "medical_record_form.html",
        {"request": request, "mode": "edit", "medical_record": medical_record, "csrf_token": csrf_token, "current_user": current_user, "user": current_user}
    )

@app.post("/medical-records/{record_id}/edit", name="edit_medical_record")
def edit_medical_record(
    record_id: int,
    medical_history: str = Form(...),
    tindakan: str = Form(...),
    obat: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor","admin_rs")),
    _=Depends(require_csrf_dep)
):
    record = db.query(models.MedicalRecord).get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")

    # 1. ambil isi lama dan simpan ke logs
    snapshot = {
        "medical_history": record.medical_history,
        "tindakan": record.tindakan,
        "obat": record.obat,
        "updated_at": record.created_at.isoformat() if record.created_at else None
    }
    last_version = db.query(models.MedicalRecordLog)\
                     .filter(models.MedicalRecordLog.medical_record_id == record.id)\
                     .order_by(models.MedicalRecordLog.version.desc())\
                     .first()
    next_version = (last_version.version + 1) if last_version else 1

    log = models.MedicalRecordLog(
        medical_record_id=record.id,
        version=next_version,
        data_snapshot=snapshot,
        updated_by=current_user.id
    )
    db.add(log)

    # 2. update record utama
    record.medical_history = medical_history
    record.tindakan = tindakan
    record.obat = obat

    db.commit()
    db.refresh(record)
    return RedirectResponse(url=f"/medical-records/{record.id}", status_code=303)


@app.get("/medical-records/{record_id}/delete", name="delete_medical_record")
def delete_medical_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "admin_rs"))
):
    medical_record = db.query(models.MedicalRecord).get(record_id)
    if not medical_record:
        raise HTTPException(status_code=404, detail="Medical record not found")
    db.delete(medical_record)
    db.commit()
    return RedirectResponse(url="/medical_records", status_code=303)

@app.get("/medical-records/{record_id}/logs", name="medical_record_logs")
def medical_record_logs(record_id: int, request: Request, db: Session = Depends(get_db)):
    record = db.query(models.MedicalRecord).get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")

    logs = db.query(models.MedicalRecordLog)\
             .filter(models.MedicalRecordLog.medical_record_id == record_id)\
             .order_by(models.MedicalRecordLog.version.desc())\
             .all()

    return templates.TemplateResponse(
        "medical_record_detail.html",
        {"request": request, "record": record, "logs": logs}
    )


# End Medical Record Routes