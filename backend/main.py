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

from fastapi import FastAPI, Depends, Request, Form, UploadFile, File, HTTPException, Query, APIRouter, Body
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_ 
from sqlalchemy.orm import Session, joinedload
from urllib.parse import urlencode
from datetime import datetime, date, timedelta
from openpyxl import Workbook, load_workbook
from typing import Optional
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from jose import jwt, JWTError
from copy import deepcopy
from .form_configs import form_configs
from . import models, crud, config
from .database import SessionLocal, engine, Base
from .auth import verify_jwt, get_db, require_roles_session, issue_csrf_token, require_csrf_dep
import requests, io, json, secrets, base64, hashlib, httpx, random


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def _fetch_jwks():
    resp = requests.get(
        f"https://{config.AUTH0_DOMAIN}/.well-known/jwks.json",
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()

def flash(request: Request, message: str, category: str = "success"):
    if "flashes" not in request.session:
        request.session["flashes"] = []
    request.session["flashes"].append({"message": message, "category": category})

def get_flashed_messages(request: Request):
    flashes = request.session.get("flashes", [])
    request.session["flashes"] = []  # clear setelah dibaca
    return flashes

# Init DB & App
Base.metadata.create_all(bind=engine)
app = FastAPI()
app.mount("/static", StaticFiles(directory="backend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")
templates.env.globals["get_flashed_messages"] = get_flashed_messages
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET, same_site="lax", https_only=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # untuk dev: izinkan semua
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
ISSUER = lambda: f"https://{config.AUTH0_DOMAIN}/"
ALGS = ["RS256"]

# -------------------------
# AUTH ROUTES
# -------------------------
@app.get("/welcome")
def welcome(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})

@app.get("/login")
def login():
    params = {
        "client_id": config.CLIENT_ID,
        "response_type": "code",
        "redirect_uri": config.REDIRECT_URI,
        "scope": "openid profile email",
        "audience": config.AUDIENCE,  # boleh hapus kalau gak pakai audience
    }
    url = f"https://{config.AUTH0_DOMAIN}/authorize?{urlencode(params)}"
    return RedirectResponse(url)


# ---------------------
# /callback → Auth0 balikin "code", kita tukar jadi token
# ---------------------
@app.get("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error": "Missing code"}, status_code=400)

    token_url = f"https://{config.AUTH0_DOMAIN}/oauth/token"
    headers = {"content-type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "code": code,
        "redirect_uri": config.REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=data, headers=headers)
        if token_res.status_code != 200:
            return JSONResponse(token_res.json(), status_code=token_res.status_code)

        token_json = token_res.json()
        access_token = token_json.get("access_token")
        if not access_token:
            return JSONResponse({"error": "No access_token in response", "detail": token_json}, status_code=400)

        # Ambil data user dari Auth0
        userinfo_res = await client.get(
            f"https://{config.AUTH0_DOMAIN}/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_res.status_code != 200:
            return JSONResponse(userinfo_res.json(), status_code=userinfo_res.status_code)

        userinfo = userinfo_res.json()

    # Cari user di DB berdasarkan auth0_sub
    user = db.query(models.User).filter_by(auth0_sub=userinfo["sub"]).first()

    if not user:
        # Buat user baru kalau belum ada
        user = models.User(
            auth0_sub=userinfo["sub"],
            email=userinfo.get("email"),
            name=userinfo.get("name"),
            role="doctor",  # default role → bisa kamu ubah sesuai kebutuhan
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Simpan user_id (integer lokal) ke session
    request.session["user_id"] = user.id
    request.session["email"] = user.email
    request.session["name"] = user.name
    request.session["role"] = user.role

    return RedirectResponse(url="/dashboard", status_code=303)

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
    users_dashboard = []
    if current_user.role == "superadmin":
        users_dashboard = db.query(models.User).filter(models.User.role == "admin_rs", models.User.is_deleted == False).order_by(models.User.id.desc()).limit(10).all()
    
    # Admin RS hanya boleh lihat user RS yang sama, selain dirinya
    elif current_user.role == "admin_rs":
        users_dashboard = (
            db.query(models.User)
              .filter(
                  models.User.hospital_id == current_user.hospital_id,
                  models.User.role.in_(["doctor", "coder", "verifikator", "costing", "validator", "manajemen"]),
                  models.User.is_deleted == False
              )
              .order_by(models.User.id.desc())
              .limit(10)
              .all()
        )
    else:
        users_dashboard = []  # fallback (nggak boleh lihat)
    # hitung umum
    total_pasien = db.query(models.Patient).count()
    pasien_hari_ini = db.query(models.Claim).filter(
        func.date(models.Claim.claim_date) == datetime.today().date()
    ).count()
    total_claims = db.query(models.Claim).filter(models.Claim.is_deleted == False).count()

    # klaim terbaru
    claims = (
        db.query(models.Claim)
        .options(joinedload(models.Claim.patient))
        .filter(models.Claim.is_deleted == False)
        .order_by(models.Claim.id.desc())
        .limit(10)
        .all()
    )

    # klaim draft & final
    draft_claims = db.query(models.Claim).filter(models.Claim.is_final == False, models.Claim.is_deleted == False).count()
    final_claims = db.query(models.Claim).filter(models.Claim.is_final == True, models.Claim.is_deleted == False).count()
    draft_claims_list = []
    if current_user.role == "verifikator":
        draft_claims_list = (
            db.query(models.Claim)
            .options(joinedload(models.Claim.patient))
            .filter(models.Claim.is_final == False, models.Claim.is_deleted == False)
            .order_by(models.Claim.id.desc())
            .all()
        )
    final_claims_list = (
        db.query(models.Claim)
        .options(joinedload(models.Claim.patient))
        .filter(models.Claim.is_final == True, models.Claim.is_deleted == False)
        .order_by(models.Claim.id.desc())
        .all()
    )

    # role check
    if current_user.role in ["doctor", "coder", "verifikator"]:
        pasien_list = db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
    else:
        pasien_list = []

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
        "final_claims": final_claims,
        "draft_claims_list": draft_claims_list,
        "final_claims_list": final_claims_list,
        "total_users": total_users,
        "pasien_list": pasien_list,
        "users": users_dashboard,
        "csrf_token": csrf_token
    })


@app.get("/")
def root_redirect(request: Request, user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))):
    flash(request, "Redirecting to dashboard...", "info")
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

    patients = query.filter(models.Patient.is_deleted == False).order_by(models.Patient.id.desc()).options(joinedload(models.Patient.hospital)).all()
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("patient_list.html", {
        "request": request,
        "patients": patients,
        "user": user,
        "search": search,
        "mode": mode,
        "flow": flow,
        "current_user": user,
        "csrf_token": csrf_token
    })


@app.get("/patients/add",name="add_patient", response_class=HTMLResponse)
def add_form(request: Request, user=Depends(require_roles_session("doctor")), db: Session = Depends(get_db)):
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("patient_form.html", {"request": request, "mode": "add", "patient": None, "csrf_token": csrf_token, "user": user, "current_user": user, "fields": form_configs["patient"], "patients": None})


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
            "hospital_id": user.hospital_id,
            "nama": nama,
            "tanggal_lahir": tanggal_lahir or None,
            "jenis_kelamin": jenis_kelamin or None,
            "alamat": alamat or None,
            "email": email or None,
            "no_hp": no_hp or None,
            "created_at": datetime.now()-timedelta(days=7),
            "updated_at": datetime.now(),
            "is_deleted": False,
            "is_dummy": True
        })
        flash(request, "Pasien berhasil ditambahkan!", "success")
        return RedirectResponse(url="/patients", status_code=303)
    except Exception as e:
        error_msg = f"Gagal menambahkan pasien: {str(e)}"
        flash(request, error_msg, "danger")
        return templates.TemplateResponse("patient_form.html", {
            "request": request,
            "fields": form_configs["patient"],
            "mode": "add",
            "patient": {
                "nama": nama,
                "tanggal_lahir": tanggal_lahir,
                "jenis_kelamin": jenis_kelamin,
                "alamat": alamat,
                "email": email,
                "hospital_id": user.hospital_id,
                "no_hp": no_hp,
                "no_ktp": no_ktp,
                "no_bpjs": no_bpjs,
                "no_rm": no_rm,
                "created_at": datetime.now()-timedelta(days=7),
                "updated_at": datetime.now(),
                "is_deleted": False,
                "is_dummy": True
            },
            "user": user,
            "current_user": user,
            "error_msg": error_msg
        })

@app.get("/patients/edit/{patient_id}", name="edit_patient")
def edit_form(patient_id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor"))):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id, models.Patient.is_deleted == False).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("patient_form.html", {
        "request": request,
        "fields": form_configs["patient"],  # static
        "mode": "edit",
        "record": patient,
        "csrf_token": csrf_token,
        "user": user,
        "current_user": user
    })

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
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id, models.Patient.is_deleted == False).first()
    if not patient:
        error_msg = "Pasien tidak ditemukan"
        return templates.TemplateResponse("patient_form.html", {
            "request": request,
            "fields": form_configs["patient"],
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
            "hospital_id": user.hospital_id,
            "nama": nama,
            "tanggal_lahir": tanggal_lahir or None,
            "alamat": alamat or None,
            "jenis_kelamin": jenis_kelamin or None,
            "email": email or None,
            "no_hp": no_hp or None,
            "updated_at": datetime.now()
        })
        flash(request, "Pasien berhasil diperbarui!", "success")
        return RedirectResponse(url="/patients", status_code=303)
    except Exception as e:
        error_msg = f"Gagal memperbarui pasien: {str(e)}"
        flash(request, error_msg, "danger")
        return templates.TemplateResponse("patient_form.html", {
            "request": request,
            "fields": form_configs["patient"],
            "mode": "edit",
            "patient": {
                "id": patient_id,
                "no_ktp": no_ktp,
                "no_bpjs": no_bpjs,
                "no_rm": no_rm,
                "hospital_id": user.hospital_id,
                "nama": nama,
                "tanggal_lahir": tanggal_lahir,
                "jenis_kelamin": jenis_kelamin,
                "alamat": alamat,
                "email": email,
                "no_hp": no_hp,
                "updated_at": datetime.now()
            },
            "user": user,
            "current_user": user,
            "error_msg": error_msg
        })


@app.post("/patients/delete/{patient_id}")
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    request: Request = None,
    _=Depends(require_csrf_dep)  # ✅ token dicek
):
    patient = db.query(models.Patient).get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # soft delete, bukan delete beneran
    patient.is_deleted = True
    db.commit()

    flash(request, "Pasien berhasil dihapus!", "success")
    return RedirectResponse("/patients", status_code=303)



@app.get("/export")
def export_patients(db: Session = Depends(get_db), user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))):
    patients = db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
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

# Rekomendasi AI untuk Klaim

def make_group(prefix, icd_prefix):
    """3 penyakit utama + 2 turunan per penyakit"""
    return [
        {"kategori": f"{prefix} 1", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": False},
        {"kategori": f"→ {prefix} 1a", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 1b", "klinis": "-",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 1c", "klinis": "-",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},

        {"kategori": f"{prefix} 2", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": False},
        {"kategori": f"→ {prefix} 2a", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 2b", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 2c", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},

        {"kategori": f"{prefix} 3", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": False},
        {"kategori": f"→ {prefix} 3a", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 3b", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 3c", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
    ]

def make_modal(icd: str, db: Session, claim_id: int, stage: str):
    sim = db.query(models.ClaimSimulation).filter_by(claim_id=claim_id).first()
    if not sim:
        sim = models.ClaimSimulation(
            claim_id=claim_id,
            stage=stage,
            is_dummy=True,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(sim)
        db.flush()  # dapat sim.id
    """
    Hybrid make_modal:
    - Kalau claim_id belum punya procedure -> isi dummy sekali
    - Kalau sudah ada -> ambil langsung dari DB
    """
    # ===== 1. Cek apakah sudah ada procedure untuk claim ini =====
    existing_procs = db.query(models.ClaimProcedure) \
    .options(joinedload(models.ClaimProcedure.procedure_details)) \
    .filter(models.ClaimProcedure.claim_id == claim_id) \
    .all()

    if not existing_procs:
        # ===== 2. Insert dummy hanya sekali =====
        dummy_procs = [
            {
                "nama": "Operasi Apendektomi",
                "detail_dummy": [
                    {
                        "icd9": "47.09",
                        "validitas": "valid",
                        "status": "utama",
                        "ina_cbg": "C-04-12",
                        "faskes": "RS Tipe C",
                        "rawat_inap": "≥ 2 hari",
                        "syarat_klinis": "Diagnosis apendisitis akut"
                    }
                ]
            },
            {
                "nama": "CT Scan Abdomen",
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "CT Scan Paha",
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Pemeriksaan Laboratorium", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "USG Abdomen", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "MRI Kepala", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Pemasangan Infus", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Pemberian Oksigen", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Terapi Nebulizer",
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Transfusi Darah",
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Terapi Infus", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            }
        ]

        for d in dummy_procs:
            proc = models.ClaimProcedure(
                claim_id=claim_id,
                procedure_text=d["nama"],
                procedure_type="utama",      # default, bisa diubah
                requirement_flag=False,
                created_at=datetime.now()-timedelta(days=1),
                updated_at=datetime.now(),
                is_dummy=True,
                is_deleted=False
            )
            db.add(proc)
            db.flush()  # biar langsung dapat proc.id

            for det in d["detail_dummy"]:
                det_model = models.ClaimProcedureDetail(
                    procedure_id=proc.id,
                    claim_simulation_id=sim.id,   # jangan lupa isi biar NOT NULL
                    icd9_tindakan=det.get("icd9"),
                    validitas_tindakan=det.get("validitas"),
                    status_tindakan=det.get("status"),
                    ina_cbg_tindakan=det.get("ina_cbg"),
                    faskes_tindakan=det.get("faskes"),
                    rawat_inap_tindakan=det.get("rawat_inap"),
                    syarat_klinis_tindakan=det.get("syarat_klinis"),
                    is_dummy=True,
                    is_deleted=False
                )
                db.add(det_model)

        db.commit()
        existing_procs = db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).all()

    # ===== 3. Ambil semua procedure yang ada di DB =====
    tindakan = []
    for p in existing_procs:
        tindakan.append({
            "id": p.id,
            "nama": p.procedure_text,
            "deskripsi": p.description,
            "detail": [
                {
                    "icd9": d.icd9_tindakan,
                    "deskripsi": f"{d.icd9_tindakan or ''} | {d.status_tindakan or ''} | {d.ina_cbg_tindakan or ''}",
                    "validitas": d.validitas_tindakan,
                    "status": d.status_tindakan,
                    "ina_cbg": d.ina_cbg_tindakan,
                    "faskes": d.faskes_tindakan,
                    "rawat_inap": d.rawat_inap_tindakan,
                    "syarat_klinis": d.syarat_klinis_tindakan,
                }
                for d in p.procedure_details if not d.is_deleted
            ]
        })

    return tindakan


def make_dummy(tab):
    return {
        "diagnosis": make_group("Diagnosis", f"{tab.upper()}DX"),
        "komorbid": make_group("Komorbid", f"{tab.upper()}KM"),
        "komplikasi": make_group("Komplikasi", f"{tab.upper()}KP"),
        "modal": {
            "klinis": {
            "justifikasi": "GFR 15-29, BMI 30-40",
            "bukti_klinis": "Belum ada bukti klinis",
            "syarat_klinis": "Belum ada syarat klinis",
            },
            "icd10": {
                "kode_icd": "E11.24",
                "struktur_icd10": "D42.5",
                "kode_ganda": "A4.10",
                "z_code": "Z18",
                "kode_bpjs_khusus": "K1",
            },
            "tindakan": [],  # 🔹 Sekarang dari DB (dummy sekali aja)
            "rawat_inap": {
                "indikasi": "Tidak ada indikasi khusus",
                "lama_rawat": "3 hari",
                "perpanjangan": "Tidak"
            },
            "faskes": {"kesesuaian_rs": "Tipe C"},
            "rujukan": {"syarat": "Tidak ada", "kelayakan": "Layak"}
        },
        "simulasi": {
            "utama": None,
            "sekunder": [],
            "tindakanUtama": None,
            "tindakanSekunder": [],
        },
        "evaluasi": {
            "kombinasi_diagnosis": {
                "validitas": "valid",
                "validitas_detail": "Sepsis + DM valid (komorbid umum)",
                "severity": "Medium (Sepsis + DM)",
                "kode_ina_cbg": "D-04-12",
                "estimasi_tarif": "Rp 7.500.000",
                "syarat_klinis": "HbA1c + kultur darah",
                "evaluasi_faskes": "Minimal RS Tipe B",
                "rawat_inap": "Minimal 3 hari rawat"
            },
            "kombinasi_tindakan": [
                {
                    "tindakan": "Antibiotik IV",
                    "validitas": "valid",
                    "validitas_detail": "Antibiotik IV",
                    "status": "optional",
                    "tarif_impact": "Rp 7.500.000",
                    "faskes": "RS Tipe B",
                    "rawat_inap": "≥ 3 hari",
                    "syarat_klinis": "Infus IV tercatat ganda - tidak pengaruh"
                },
                {
                    "validitas": "valid",
                    "validitas_detail": "Ventilasi Mekanik",
                    "tindakan": "Ventilasi Mekanik",
                    "status": "wajib",
                    "tarif_impact": "Rp 12.500.000",
                    "faskes": "RS Tipe C",
                    "rawat_inap": "≥ 5 hari",
                    "syarat_klinis": "PCI + CABG bersamaan - tidak lazim"
                }
            ],
            "alternatif": [
                {
                    "kombinasi": "Sepsis + ARDS",
                    "kode_ina_cbg": "D-04-13",
                    "tarif": "Rp 12.500.000",
                    "syarat_klinis": "Ventilasi Mekanik + catatan ICU",
                    "faskes": "RS Tipe B",
                    "rawat_inap": "≥ 3 hari + ICU ≥ 2 hari",
                    "tindakan_wajib": "Ventilasi Mekanik"
                },
                {
                    "kombinasi": "Sepsis + DM + ARDS",
                    "kode_ina_cbg": "D-04-13",
                    "tarif": "Rp 13.500.000",
                    "syarat_klinis": "Ventilasi Mekanik + catatan ICU",
                    "faskes": "RS Tipe B / C",
                    "rawat_inap": "≥ 3 hari + ICU ≥ 2 hari",
                    "tindakan_wajib": "Ventilasi Mekanik"
                }
            ]
        }
    }

def store_ai_recommendations(db: Session, claim_id: int, dummy_data: dict, stage: str):
    """
    Simpan hasil generate AI ke 2 tabel utama:
    - ClaimDiagnosis        → kategori diagnosis (tanpa detail dulu)
    - ClaimAIRecommendation → untuk tampilan rekomendasi awal
    Catatan: ClaimProcedure & ClaimProcedureDetail dummy sudah diisi via make_modal()
    """
    # 🔹 Pastikan ada ClaimSimulation
    sim = db.query(models.ClaimSimulation).filter_by(claim_id=claim_id, stage=stage).first()
    if not sim:
        sim = models.ClaimSimulation(
            claim_id=claim_id,
            stage=stage,
            is_dummy=True,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(sim)
        db.flush()

    # 1️⃣ Diagnosis / Komorbid / Komplikasi
    for category in ["diagnosis", "komorbid", "komplikasi"]:
        for item in dummy_data.get(category, []):
            diag = models.ClaimDiagnosis(
                claim_id=claim_id,
                diagnosis_type=category,
                diagnosis_text=item.get("kategori"),
                is_dummy=True,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(diag)
            db.flush()

            rec = models.ClaimAIRecommendation(
                claim_id=claim_id,
                stage=stage,
                category=category,
                confidence_score=item.get("score"),
                diagnosis_id=diag.id,
                child=item.get("child", False),
                is_dummy=True,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(rec)

    # 2️⃣ Tindakan → ambil yang sudah ada di DB, jangan insert ulang
    print("💾 Simpan claim:", claim_id, "stage:", stage)
    existing_procs = db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).all()
    for p in existing_procs:
        print("PROC:", p.id, p.procedure_text)
    for d in p.procedure_details:
        print("DETAIL:", d.icd9_tindakan, d.ina_cbg_tindakan)

    db.commit()

def store_ai_modal_details(db: Session, diag_id: int, modal_data: dict):
    
    diag = db.query(models.ClaimDiagnosis).filter_by(id=diag_id, is_deleted=False).first()
    if diag and modal_data:
        diag.icd10_code = (modal_data.get("icd10") or {}).get("kode_icd")
        diag.struktur_icd10 = (modal_data.get("icd10") or {}).get("struktur_icd10")
        diag.kode_ganda = (modal_data.get("icd10") or {}).get("kode_ganda")
        diag.z_code = (modal_data.get("icd10") or {}).get("z_code")
        diag.kode_bpjs_khusus = (modal_data.get("icd10") or {}).get("kode_bpjs_khusus")
        diag.justifikasi = (modal_data.get("klinis") or {}).get("justifikasi")
        diag.bukti_klinis = (modal_data.get("klinis") or {}).get("bukti_klinis")
        diag.syarat_klinis = (modal_data.get("klinis") or {}).get("syarat_klinis")
        diag.indikasi = (modal_data.get("rawat_inap") or {}).get("indikasi")
        diag.lama_rawat = (modal_data.get("rawat_inap") or {}).get("lama_rawat")
        diag.perpanjangan = (modal_data.get("rawat_inap") or {}).get("perpanjangan")
        diag.kesesuaian_rs = (modal_data.get("faskes") or {}).get("kesesuaian_rs")
        diag.syarat = (modal_data.get("rujukan") or {}).get("syarat")
        diag.kelayakan = (modal_data.get("rujukan") or {}).get("kelayakan")
        diag.updated_at = datetime.utcnow()
        db.add(diag)
        db.commit()




@app.post("/ai/recommendation")
def ai_recommendation(payload: dict = Body(None), db: Session = Depends(get_db)):
    claim_id = int(payload["claim_id"]) if payload and payload.get("claim_id") else None

    admission = make_dummy("admission")
    daily = [make_dummy("daily1"), make_dummy("daily2")]
    discharge = make_dummy("discharge")

    if claim_id:
    # 1️⃣ Hapus dulu detail procedure
        db.query(models.ClaimProcedureDetail).filter(
            models.ClaimProcedureDetail.procedure_id.in_(
                db.query(models.ClaimProcedure.id).filter_by(claim_id=claim_id)
            )
        ).delete(synchronize_session=False)

        # 2️⃣ Hapus AIRecommendation (supaya foreign key ke procedure aman)
        db.query(models.ClaimAIRecommendation).filter_by(claim_id=claim_id).delete()

        # 3️⃣ Baru hapus ClaimProcedure
        db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).delete()

        # 4️⃣ Terakhir hapus diagnosis & simulation
        db.query(models.ClaimDiagnosis).filter_by(claim_id=claim_id).delete()
        db.query(models.ClaimSimulation).filter_by(claim_id=claim_id).delete()

        db.commit()

        print(f"🧹 Bersihkan data lama untuk claim_id={claim_id}")

        # 🔹 Seed dummy → make_modal isi ClaimProcedure
        admission["tindakan"] = make_modal("A41", db, claim_id, "admission")
        print(f"✅ make_modal admission hasil: {admission['tindakan']}")
        store_ai_recommendations(db, claim_id, admission, "admission")

        for idx, day in enumerate(daily):
            day["tindakan"] = make_modal("A41", db, claim_id, f"daily{idx+1}")
            print(f"✅ make_modal daily{idx+1} hasil: {day['tindakan']}")
            store_ai_recommendations(db, claim_id, day, f"daily{idx+1}")

        discharge["tindakan"] = make_modal("A41", db, claim_id, "discharge")
        print(f"✅ make_modal discharge hasil: {discharge['tindakan']}")
        store_ai_recommendations(db, claim_id, discharge, "discharge")

    # 🔹 Ambil ClaimAIRecommendation
    recs = (
        db.query(models.ClaimAIRecommendation)
        .options(
            joinedload(models.ClaimAIRecommendation.diagnosis)
        )
        .filter_by(claim_id=claim_id)
        .all()
    )

    data = []
    for rec in recs:
        # Debug log untuk setiap record
        print(f"📌 rec.id={rec.id}, stage={rec.stage}, cat={rec.category}, "
              f"diag_id={rec.diagnosis_id}")

        kategori = "-"
        if rec.diagnosis:
            kategori = rec.diagnosis.diagnosis_text

        klinis = "-"
        if rec.diagnosis:
            klinis = ", ".join(
                filter(None, [
                    getattr(rec.diagnosis, "justifikasi", None),
                    getattr(rec.diagnosis, "bukti_klinis", None),
                    getattr(rec.diagnosis, "syarat_klinis", None),
                ])
            ) or "-"

        item = {
            "id": rec.id,
            "stage": rec.stage,
            "category": rec.category,
            "score": rec.confidence_score,
            "diagnosis_id": rec.diagnosis_id,
            "child": rec.child,
            "kategori": kategori,
            "klinis": klinis,
            "icd10_code": getattr(rec.diagnosis, "icd10_code", "-") if rec.diagnosis else "-",
            "description": "-",
        }
        data.append(item)

    return {"status": "ok", "data": data}

@app.get("/ai/recommendation/detail")
def ai_recommendation_detail_get(
    claim_id: int,
    rec_type: str,
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Ambil detail rekomendasi untuk isi modal:
    - diagnosis/komorbid/komplikasi → resolve lewat ClaimAIRecommendation → ClaimDiagnosis
    - procedure → ClaimAIRecommendation → ClaimProcedure + ClaimProcedureDetail
    """

    if rec_type in ["diagnosis", "komorbid", "komplikasi"]:
        rec = db.query(models.ClaimAIRecommendation).filter_by(
            id=item_id, claim_id=claim_id, category=rec_type
        ).first()

        if not rec or not rec.diagnosis_id:
            return {"status": "error", "msg": "Recommendation/Diagnosis not found"}

        diag = db.query(models.ClaimDiagnosis).filter_by(id=rec.diagnosis_id, claim_id=claim_id).first()
        tindakan = db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).all()
        tindakan_list = [{"id": p.id, "tindakan": p.procedure_text} for p in tindakan]
        modal_data = make_dummy("A41.9")["modal"]

        if not diag.icd10_code:
            diag.icd10_code = modal_data["icd10"]["kode_icd"]

        if not diag.struktur_icd10:
            diag.struktur_icd10 = modal_data["icd10"]["struktur_icd10"]

        if not diag.kode_ganda:
            diag.kode_ganda = modal_data["icd10"]["kode_ganda"]

        if not diag.z_code:
            diag.z_code = modal_data["icd10"]["z_code"]

        if not diag.kode_bpjs_khusus:
            diag.kode_bpjs_khusus = modal_data["icd10"]["kode_bpjs_khusus"]
        
        if not diag.justifikasi:
            diag.justifikasi = modal_data["klinis"]["justifikasi"]

        if not diag.bukti_klinis:
            diag.bukti_klinis = modal_data["klinis"]["bukti_klinis"]

        if not diag.syarat_klinis:
            diag.syarat_klinis = modal_data["klinis"]["syarat_klinis"]

        if not diag.indikasi:
            diag.indikasi = modal_data["rawat_inap"]["indikasi"]

        if not diag.lama_rawat:
            diag.lama_rawat = modal_data["rawat_inap"]["lama_rawat"]

        if not diag.perpanjangan:
            diag.perpanjangan = modal_data["rawat_inap"]["perpanjangan"]

        if not diag.kesesuaian_rs:
            diag.kesesuaian_rs = modal_data["faskes"]["kesesuaian_rs"]

        if not diag.syarat:
            diag.syarat = modal_data["rujukan"]["syarat"]

        if not diag.kelayakan:
            diag.kelayakan = modal_data["rujukan"]["kelayakan"]

        diag.updated_at = datetime.utcnow()
        db.add(diag)
        db.commit()

        return {"status": "ok", "data": {
            "id": diag.id,
            "kategori": diag.diagnosis_text,
            "klinis": {
                "justifikasi": diag.justifikasi,
                "bukti_klinis": diag.bukti_klinis,
                "syarat_klinis": diag.syarat_klinis
            },
            "icd10": {
                "kode_icd": diag.icd10_code,
                "struktur_icd10": diag.struktur_icd10,
                "kode_ganda": diag.kode_ganda,
                "z_code": diag.z_code,
                "kode_bpjs_khusus": diag.kode_bpjs_khusus
            },
            "tindakan": tindakan_list,
            "rawat_inap": {
                "indikasi": diag.indikasi,
                "lama_rawat": diag.lama_rawat,
                "perpanjangan": diag.perpanjangan,
            },
            "faskes": {
                "kesesuaian_rs": diag.kesesuaian_rs,
            },
            "rujukan": {
                "syarat": diag.syarat,
                "kelayakan": diag.kelayakan,
            }
        }}

        return {"status": "error", "msg": "Diagnosis not found"}

    elif rec_type == "procedure":
        proc = db.query(models.ClaimProcedure)\
            .options(joinedload(models.ClaimProcedure.procedure_details))\
            .filter_by(id=item_id, claim_id=claim_id).first()

        if not proc:
            return {"status": "error", "msg": "Procedure not found"}

        details = [
            {
                "icd9": d.icd9_tindakan,
                "deskripsi": " | ".join(filter(None, [
                    d.icd9_tindakan,
                    d.ina_cbg_tindakan,
                    d.status_tindakan
                ])),
                "validitas": d.validitas_tindakan,
                "status": d.status_tindakan,
                "ina_cbg": d.ina_cbg_tindakan,
                "faskes": d.faskes_tindakan,
                "rawat_inap": d.rawat_inap_tindakan,
                "syarat_klinis": d.syarat_klinis_tindakan,
            }
            for d in proc.procedure_details if not d.is_deleted
        ]
        description = "; ".join([d["deskripsi"] for d in details]) if details else "-"
        return {"status": "ok", "data": {
            "id": proc.id,
            "procedure_text": proc.procedure_text,
            "description": description,
            "tindakan": details
        }}

    return {"error": f"Tipe {rec_type} tidak dikenali"}



def store_ai_evaluations(db: Session, claim_id: int, evaluasi: dict):
    """Simpan hasil evaluasi kombinasi ke tabel sesuai model"""
    db.query(models.ClaimDiagnosisEvaluation).filter_by(claim_id=claim_id).delete()
    db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=claim_id).delete()
    db.query(models.ClaimCombinationAlternative).filter_by(claim_id=claim_id).delete()
    db.commit()
    # --- Helper untuk parse validitas ke enum ---
    def parse_validitas(raw: str):
        if not raw:
            return None
        raw_lower = raw.lower()

        if "invalid" in raw_lower:
            return "invalid"
        if "warning" in raw_lower or "medium" in raw_lower:
            return "warning"
        if "valid" in raw_lower:
            return "valid"
        return None



    # === Kombinasi Diagnosis ===
    diag_eval = models.ClaimDiagnosisEvaluation(
        claim_id=claim_id,
        diagnosis_id=evaluasi["kombinasi_diagnosis"].get("diagnosis_id"),
        validitas=parse_validitas(evaluasi["kombinasi_diagnosis"].get("validitas")),
        validitas_detail=evaluasi["kombinasi_diagnosis"].get("validitas_detail"),
        severity=evaluasi["kombinasi_diagnosis"].get("severity"),
        kode_ina_cbg=evaluasi["kombinasi_diagnosis"].get("kode_ina_cbg"),
        estimasi_tarif=(
            None if not evaluasi["kombinasi_diagnosis"].get("estimasi_tarif")
            else float(
                str(evaluasi["kombinasi_diagnosis"]["estimasi_tarif"])
                .replace("Rp", "")
                .replace(".", "")
                .replace("jt", "000000")
                .strip()
            )
        ),
        syarat_klinis=evaluasi["kombinasi_diagnosis"].get("syarat_klinis"),
        evaluasi_faskes=evaluasi["kombinasi_diagnosis"].get("evaluasi_faskes"),
        rawat_inap=evaluasi["kombinasi_diagnosis"].get("rawat_inap"),
        is_dummy=True,
        is_deleted=False,
        created_at=datetime.utcnow(),
    )
    db.add(diag_eval)

    # === Kombinasi Tindakan ===
    for td in evaluasi.get("kombinasi_tindakan", []):
        proc_eval = models.ClaimProcedureEvaluation(
            claim_id=claim_id,
            procedure_id=None,
            validitas=parse_validitas(td.get("validitas")),
            validitas_detail=td.get("validitas_detail"),
            status_tindakan=td.get("status"),
            tarif_impact=(
                None if not td.get("tarif_impact")
                else float(str(td["tarif_impact"]).replace("Rp", "").replace(".", "").replace("jt", "000000").strip())
            ),
            faskes=td.get("faskes"),
            rawat_inap=td.get("rawat_inap"),
            syarat_klinis=td.get("syarat_klinis"),
            is_dummy=True,
            is_deleted=False,
            created_at=datetime.utcnow(),
        )
        db.add(proc_eval)

    # === Alternatif Kombinasi ===
    severity_default = evaluasi["kombinasi_diagnosis"].get("severity")
    for alt in evaluasi["alternatif"][:2]:
        comb = models.ClaimCombinationAlternative(
            claim_id=claim_id,
            kombinasi_nama=alt.get("kombinasi"),
            severity=severity_default,
            kode_ina_cbg=alt.get("kode_ina_cbg"),
            estimasi_tarif=(
                None if not alt.get("tarif")
                else float(str(alt["tarif"]).replace("Rp", "").replace(".", "").replace("jt", "000000").strip())
            ),
            syarat_klinis=alt.get("syarat_klinis"),
            faskes=alt.get("faskes"),
            rawat_inap=alt.get("rawat_inap"),
            tindakan_wajib=alt.get("tindakan_wajib"),
            notes=None,
            is_dummy=True,
            is_deleted=False,
            created_at=datetime.utcnow(),
        )
        db.add(comb)

    db.commit()



# End Rekomendasi AI untuk Klaim

# -------------------------
# Simulasi AI untuk Klaim
# -------------------------

def parse_number(val):
    if not val:
        return None
    if isinstance(val, (int, float)):
        return val
    # Hapus "Rp", koma, titik
    cleaned = str(val).replace("Rp", "").replace(",", "").replace(".", "").strip()
    try:
        return int(cleaned)
    except ValueError:
        return None

def save_simulation_and_summary(db: Session, claim_id: int, sim_data: dict, summ_data: dict):
    """Simpan ulang simulasi (utama/sekunder) + evaluasi kombinasi ke tabel pecahan"""

    # 🔹 Bersihkan dulu
    db.query(models.ClaimSimulation).filter(models.ClaimSimulation.claim_id == claim_id).delete()
    db.query(models.ClaimDiagnosisEvaluation).filter(models.ClaimDiagnosisEvaluation.claim_id == claim_id).delete()
    db.query(models.ClaimProcedureEvaluation).filter(models.ClaimProcedureEvaluation.claim_id == claim_id).delete()
    db.query(models.ClaimCombinationAlternative).filter(models.ClaimCombinationAlternative.claim_id == claim_id).delete()

    # 🔹 Simpan ulang ClaimSimulation
    for stage, arr in (sim_data or {}).items():
        if not isinstance(arr, dict):
            continue

        # --- Diagnosis utama ---
        utama_diag_id = None
        if arr.get("utama"):
            utama_item = arr["utama"] if isinstance(arr["utama"], dict) else None
            if utama_item:
                utama_diag_id = utama_item.get("diagnosis_id")
                if not utama_diag_id and (utama_item.get("name") or utama_item.get("diagnosis_text")):
                    utama_diag = db.query(models.ClaimDiagnosis).filter_by(
                        claim_id=claim_id,
                        diagnosis_text=utama_item.get("name") or utama_item.get("diagnosis_text")
                    ).first()
                    utama_diag_id = utama_diag.id if utama_diag else None

        # --- Diagnosis sekunder ---
        sek_diag_id = None
        if arr.get("sekunder"):
            sek_item = arr["sekunder"][0] if isinstance(arr["sekunder"], list) and arr["sekunder"] else None
            if sek_item:
                sek_diag_id = sek_item.get("diagnosis_id")
                if not sek_diag_id and (sek_item.get("name") or sek_item.get("diagnosis_text")):
                    sek_diag = db.query(models.ClaimDiagnosis).filter_by(
                        claim_id=claim_id,
                        diagnosis_text=sek_item.get("name") or sek_item.get("diagnosis_text")
                    ).first()
                    sek_diag_id = sek_diag.id if sek_diag else None

        # --- Tindakan utama ---
        utama_tindakan_id = None
        if arr.get("tindakanUtama"):
            utama_proc_id = arr["tindakanUtama"].get("tindakan_utama_id")
            if not utama_proc_id and arr["tindakanUtama"].get("name"):
                utama_proc = db.query(models.ClaimProcedure).filter_by(
                    claim_id=claim_id,
                    procedure_text=arr["tindakanUtama"]["name"]
                ).first()
                utama_proc_id = utama_proc.id if utama_proc else None
            utama_tindakan_id = utama_proc_id

        # --- Tindakan sekunder ---
        sekunder_tindakan_id = None
        if arr.get("tindakanSekunder"):
            sek_item = arr["tindakanSekunder"][0] if isinstance(arr["tindakanSekunder"], list) and arr["tindakanSekunder"] else None
            if sek_item:
                proc_id = sek_item.get("tindakan_sekunder_id")
                if not proc_id and sek_item.get("name"):
                    proc = db.query(models.ClaimProcedure).filter_by(
                        claim_id=claim_id,
                        procedure_text=sek_item["name"]
                    ).first()
                    proc_id = proc.id if proc else None
                sekunder_tindakan_id = proc_id

        # --- Simpan satu row saja ---
        db.add(models.ClaimSimulation(
            claim_id=claim_id,
            stage=stage,
            diagnosis_utama_id=utama_diag_id,
            diagnosis_sekunder_id=sek_diag_id,
            tindakan_utama_id=utama_tindakan_id,
            tindakan_sekunder_id=sekunder_tindakan_id,
            is_dummy=False,
            is_deleted=False,
            created_at=datetime.utcnow() - timedelta(days=1),
            updated_at=datetime.utcnow()
        ))


    # 🔹 Simpan Evaluasi
    if summ_data:
        # Kombinasi Diagnosis
        diag_eval = models.ClaimDiagnosisEvaluation(
            claim_id=claim_id,
            validitas=summ_data.get("kombinasi_diagnosis", {}).get("validitas"),
            severity=summ_data.get("kombinasi_diagnosis", {}).get("severity"),
            validitas_detail=summ_data.get("kombinasi_diagnosis", {}).get("validitas_detail"),
            kode_ina_cbg=summ_data.get("kombinasi_diagnosis", {}).get("kode_ina_cbg"),
            estimasi_tarif = parse_number(
                summ_data.get("kombinasi_diagnosis", {}).get("estimasi_tarif")
            ),
            syarat_klinis=summ_data.get("kombinasi_diagnosis", {}).get("syarat_klinis"),
            evaluasi_faskes=summ_data.get("kombinasi_diagnosis", {}).get("evaluasi_faskes"),
            rawat_inap=summ_data.get("kombinasi_diagnosis", {}).get("rawat_inap"),
            created_at=datetime.utcnow() - timedelta(days=1),
            is_deleted=False,
            is_dummy=True
        )
        db.add(diag_eval)

        # Kombinasi Tindakan
        for v in summ_data.get("procedure", []):
            proc_id = v.get("procedure_id")
            if not proc_id and v.get("tindakan"):
                proc = db.query(models.ClaimProcedure).filter_by(
                    claim_id=claim_id,
                    procedure_text=v["tindakan"]
                ).first()
                proc_id = proc.id if proc else None

            proc_eval = models.ClaimProcedureEvaluation(
                claim_id=claim_id,
                procedure_id=proc_id,
                validitas=v.get("validitas"),
                validitas_detail=v.get("validitas_detail"),
                status_tindakan=v.get("status_tindakan"),
                tarif_impact = parse_number(v.get("tarif_impact")),
                faskes=v.get("faskes"),
                rawat_inap=v.get("rawat_inap"),
                syarat_klinis=v.get("syarat_klinis"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
                is_dummy=True
            )
            db.add(proc_eval)

        # Alternatif
        for alt in summ_data.get("alternatif", []):
            comb = models.ClaimCombinationAlternative(
                claim_id=claim_id,
                kombinasi_nama=alt.get("kombinasi_nama"),
                severity=alt.get("severity"),
                kode_ina_cbg=alt.get("kode_ina_cbg"),
                estimasi_tarif = parse_number(
                    alt.get("estimasi_tarif")
                ),
                syarat_klinis=alt.get("syarat_klinis"),
                faskes=alt.get("faskes"),
                rawat_inap=alt.get("rawat_inap"),
                tindakan_wajib=alt.get("tindakan_wajib"),
                created_at=datetime.utcnow(),
                is_deleted=False,
                is_dummy=True
            )
            db.add(comb)

    db.commit()



@app.post("/ai/summary/{claim_id}")
def ai_summary(
    claim_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Terima mapping dari FE (simulasi utama/sekunder).
    Lalu generate evaluasi & simpan ke tabel evaluasi.
    """
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Ambil simulasi dari payload (buat log / future rule engine)
    simulasi = payload.get("simulasi", {})

    # Buat dummy evaluasi (nanti ganti real AI/engine)
    evaluasi = make_dummy("summary")["evaluasi"]
    store_ai_evaluations(db, claim_id, evaluasi)

    # Ambil hasil yang baru disimpan
    diag = db.query(models.ClaimDiagnosisEvaluation)\
             .filter_by(claim_id=claim_id).first()
    procs = db.query(models.ClaimProcedureEvaluation)\
              .filter_by(claim_id=claim_id).all()
    alts = db.query(models.ClaimCombinationAlternative)\
             .filter_by(claim_id=claim_id).limit(2).all()

    return {
        "diagnosis": {
            "validitas": diag.validitas if diag else "-",
            "validitas_detail": diag.validitas_detail if diag else "-",
            "severity": diag.severity if diag else "-",
            "kode_ina_cbg": diag.kode_ina_cbg if diag else "-",
            "estimasi_tarif": diag.estimasi_tarif if diag else "-",
            "syarat": diag.syarat_klinis if diag else "-",
            "evaluasi_faskes": diag.evaluasi_faskes if diag else "-",
            "rawat_inap": diag.rawat_inap if diag else "-"
        },
        "procedure": [
            {
                "validitas": p.validitas or "-",
                "validitas_detail": p.validitas_detail or "-",
                "tindakan": p.validitas_detail or p.status_tindakan or "-",
                "status_tindakan": p.status_tindakan or "-",
                "tarif_impact": f"Rp {int(p.tarif_impact):,}" if p.tarif_impact else "-",
                "faskes": p.faskes or "-",
                "rawat_inap": p.rawat_inap or "-",
                "syarat_klinis": p.syarat_klinis or "-"
            }
            for p in procs
        ],
        "alternatif": [
            {
                "nama": a.kombinasi_nama,
                "severity_detail": diag.severity if not a.severity else a.severity,
                "ina_cbg": a.kode_ina_cbg,
                "tarif": a.estimasi_tarif,
                "syarat": a.syarat_klinis,
                "faskes": a.faskes,
                "rawat_inap": a.rawat_inap,
                "tindakan_wajib": a.tindakan_wajib
            }
            for a in alts
        ],
        "alternatif_count": len(alts)
    }



# ------------------------
# END Claim AI Summary
# ------------------------

@app.get("/claims/{claim_id}/recommendations")
def get_claim_recommendations(
    claim_id: int,
    db: Session = Depends(get_db)
):
    recs = db.query(models.ClaimAIRecommendation).filter_by(
        claim_id=claim_id,
        is_deleted=False
    ).all()

    return {
        "status": "ok",
        "data": [
            {
                "id": rec.id,
                "stage": rec.stage,
                "category": rec.category,
                "score": rec.confidence_score,
                "child": rec.child
            }
            for rec in recs
        ]
    }

@app.get("/claims/{claim_id}/simulations")
def get_simulations(claim_id: int, db: Session = Depends(get_db)):
    sims = db.query(models.ClaimSimulation).options(
        joinedload(models.ClaimSimulation.diagnosis_utama),
        joinedload(models.ClaimSimulation.diagnosis_sekunder),
        joinedload(models.ClaimSimulation.tindakan_utama),
        joinedload(models.ClaimSimulation.tindakan_sekunder)
    ).filter_by(claim_id=claim_id).all()

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
        ]
    }



# ------------------------
# Claim Finalize
# ------------------------

@app.post("/claims/{claim_id}/finalize", name="finalize_claim")
def finalize_claim(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator")),
    _=Depends(require_csrf_dep),

    simulasi: str = Form(None),
    summary: str = Form(None),

    # form rekam medis
    riwayat_penyakit: str = Form(None),
    riwayat_pengobatan: str = Form(None),
    riwayat_operasi: str = Form(None),
    alergi: str = Form(None),
    keluhan: str = Form(None),
    gejala_lain: str = Form(None),
    tekanan_darah: str = Form(None),
    nadi: str = Form(None),
    pernapasan: str = Form(None),
    suhu: str = Form(None),
    spo2: str = Form(None),
    berat_badan: str = Form(None),
    tinggi_badan: str = Form(None),
    hemoglobin: str = Form(None),
    leukosit: str = Form(None),
    trombosit: str = Form(None),
    gula_darah: str = Form(None),
    creatinin: str = Form(None),
    rontgen_thorax: str = Form(None),
    ct_scan: str = Form(None),
    usg: str = Form(None),
    diagnosis_awal: str = Form(None),
    komorbid: str = Form(None),
    komplikasi: str = Form(None),
    diagnosis_akhir: str = Form(None),
    tindakan: str = Form(None),
    obat: str = Form(None),
    validasi_fornas: str = Form(None),
    notes_doctor: str = Form(None),
):
    print("📥 Finalize klaim form masuk!")

    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # parse simulasi & summary
    sim_data, summ_data = {}, {}
    if simulasi:
        try:
            sim_data = json.loads(simulasi)
        except Exception as e:
            print("❌ Gagal parse simulasi:", e)
    if summary:
        try:
            summ_data = json.loads(summary)
        except Exception as e:
            print("❌ Gagal parse summary:", e)

    # --- update ClaimDiagnosis & ClaimProcedure dari sim_data
    try:
        for stage, stage_data in sim_data.items():
            # diagnosis utama
            if "utama" in stage_data and stage_data["utama"]:
                diag = db.query(models.ClaimDiagnosis)\
                         .filter_by(claim_id=claim.id, diagnosis_text=stage_data["utama"]["name"])\
                         .first()
                if diag:
                    diag.icd10_code = stage_data["utama"].get("icd") or diag.icd10_code
                    diag.justifikasi = stage_data["utama"].get("label") or diag.justifikasi
                    diag.bukti_klinis = stage_data["utama"].get("bukti_klinis")
                    diag.syarat_klinis = stage_data["utama"].get("syarat_klinis")
                    diag.kode_ganda = stage_data["utama"].get("kode_ganda")
                    diag.z_code = stage_data["utama"].get("z_code")
                    diag.kode_bpjs_khusus = stage_data["utama"].get("kode_bpjs_khusus")
                    diag.faskes = stage_data["utama"].get("faskes")
                    diag.rawat_inap = stage_data["utama"].get("rawat_inap")
                    diag.rujukan = stage_data["utama"].get("rujukan")
                    diag.struktur_icd10 = stage_data["utama"].get("struktur_icd10")
                    diag.updated_at = datetime.utcnow()
                if not diag:
                    diag = models.ClaimDiagnosis(
                        claim_id=claim.id,
                        diagnosis_type="utama",
                        diagnosis_text=stage_data["utama"]["name"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True,
                    )
                    db.add(diag)
                    db.flush()

            # diagnosis sekunder
            for sec in stage_data.get("sekunder", []):
                diag = db.query(models.ClaimDiagnosis)\
                        .filter_by(claim_id=claim.id, diagnosis_text=sec["name"])\
                        .first()
                if diag:
                    diag.icd10_code = sec.get("icd") or diag.icd10_code
                    diag.justifikasi = sec.get("label") or diag.justifikasi
                    diag.bukti_klinis = sec.get("bukti_klinis") or diag.bukti_klinis
                    diag.syarat_klinis = sec.get("syarat_klinis") or diag.syarat_klinis
                    diag.kode_ganda = sec.get("kode_ganda") or diag.kode_ganda
                    diag.z_code = sec.get("z_code") or diag.z_code
                    diag.kode_bpjs_khusus = sec.get("kode_bpjs_khusus") or diag.kode_bpjs_khusus
                    diag.faskes = sec.get("faskes") or diag.faskes
                    diag.rawat_inap = sec.get("rawat_inap") or diag.rawat_inap
                    diag.rujukan = sec.get("rujukan") or diag.rujukan
                    diag.struktur_icd10 = sec.get("struktur_icd10") or diag.struktur_icd10
                    diag.updated_at = datetime.utcnow()
                if not diag:
                    diag = models.ClaimDiagnosis(
                        claim_id=claim.id,
                        diagnosis_type="sekunder",
                        diagnosis_text=stage_data["utama"]["name"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True,
                    )
                    db.add(diag)
                    db.flush()


            # Tindakan utama & sekunder
            if "tindakanUtama" in stage_data and stage_data["tindakanUtama"]:
                proc = db.query(models.ClaimProcedure)\
                        .filter_by(claim_id=claim.id, procedure_text=stage_data["tindakanUtama"]["name"])\
                        .first()
                if proc:
                    # Ambil detail pertama (karena relasi one-to-many)
                    detail = db.query(models.ClaimProcedureDetail)\
                            .filter_by(procedure_id=proc.id, is_deleted=False)\
                            .first()
                    if detail:
                        detail.icd9_tindakan = stage_data["tindakanUtama"].get("icd") or detail.icd9_tindakan
                        detail.icd9_deskripsi_tindakan = stage_data["tindakanUtama"].get("deskripsi") or detail.icd9_deskripsi_tindakan
                        detail.updated_at = datetime.utcnow()
                if not proc:
                    proc = models.ClaimProcedure(
                        claim_id=claim.id,
                        procedure_type="utama",
                        procedure_text=td["name"],
                        requirement_flag=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True
                    )
                    db.add(proc)
                    db.flush()

                    detail = models.ClaimProcedureDetail(
                        procedure_id=proc.id,
                        icd9_tindakan=td.get("icd"),
                        icd9_deskripsi_tindakan=td.get("deskripsi"),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False
                    )
                    db.add(detail)
                    db.flush()
        

            for td in stage_data.get("tindakanSekunder", []):
                proc = db.query(models.ClaimProcedure)\
                        .filter_by(claim_id=claim.id, procedure_text=td["name"])\
                        .first()
                if proc:
                    detail = db.query(models.ClaimProcedureDetail)\
                            .filter_by(procedure_id=proc.id, is_deleted=False)\
                            .first()
                    if detail:
                        detail.icd9_tindakan = td.get("icd") or detail.icd9_tindakan
                        detail.icd9_deskripsi_tindakan = td.get("deskripsi") or detail.icd9_deskripsi_tindakan
                        detail.updated_at = datetime.utcnow()
                if not proc:
                    proc = models.ClaimProcedure(
                        claim_id=claim.id,
                        procedure_type="sekunder",
                        procedure_text=td["name"],
                        requirement_flag=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True
                    )
                    db.add(proc)
                    db.flush()

                    detail = models.ClaimProcedureDetail(
                        procedure_id=proc.id,
                        icd9_tindakan=td.get("icd"),
                        icd9_deskripsi_tindakan=td.get("deskripsi"),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False
                    )
                    db.add(detail)
                    db.flush()
        db.flush()
    except Exception as e:
        print("❌ Gagal update ClaimDiagnosis & ClaimProcedure:", e)

    # 🔹 Simpan simulasi & summary via helper
    save_simulation_and_summary(db, claim.id, sim_data, summ_data)

    # 🔹 Update simulasi
    for stage, stage_data in sim_data.items():
        sims = db.query(models.ClaimSimulation).filter_by(claim_id=claim.id).all()
        for sim in sims:
            # Diagnosis utama
            if stage_data.get("utama"):
                utama_diag = db.query(models.ClaimDiagnosis)\
                    .filter_by(claim_id=claim.id, diagnosis_text=stage_data["utama"]["name"])\
                    .first()
                if not utama_diag:
                    utama_diag = models.ClaimDiagnosis(
                        claim_id=claim.id,
                        diagnosis_type="utama",
                        diagnosis_text=stage_data["utama"]["name"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True
                    )
                    db.add(utama_diag)
                    db.flush()
                sim.diagnosis_utama_id = utama_diag.id
                # Diagnosis sekunder
            if stage_data.get("sekunder"):
                ids = []
                for sec in stage_data["sekunder"]:
                    sec_diag = db.query(models.ClaimDiagnosis)\
                        .filter_by(claim_id=claim.id, diagnosis_text=sec["name"])\
                        .first()
                    if not sec_diag:
                        sec_diag = models.ClaimDiagnosis(
                            claim_id=claim.id,
                            diagnosis_type="sekunder",
                            diagnosis_text=sec["name"],
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                            is_deleted=False,
                            is_dummy=True
                            )
                        db.add(sec_diag)
                        db.flush()
                    ids.append(sec_diag.id)
                sim.diagnosis_sekunder_ids = ids
            sim.updated_at = datetime.utcnow()

        

    # 🔹 Update klaim → finalize
    claim.is_final = True
    claim.status = "final"
    claim.updated_at = datetime.utcnow()

    # 🔹 Update rekam medis (sama seperti versi draft)
    if claim.medical_record:
        mr = claim.medical_record
        for field, value in {
            "riwayat_penyakit": riwayat_penyakit,
            "riwayat_pengobatan": riwayat_pengobatan,
            "riwayat_operasi": riwayat_operasi,
            "alergi": alergi,
            "keluhan": keluhan,
            "gejala_lain": gejala_lain,
            "tekanan_darah": tekanan_darah,
            "nadi": nadi,
            "pernapasan": pernapasan,
            "suhu": suhu,
            "spo2": spo2,
            "berat_badan": berat_badan,
            "tinggi_badan": tinggi_badan,
            "hemoglobin": hemoglobin,
            "leukosit": leukosit,
            "trombosit": trombosit,
            "gula_darah": gula_darah,
            "creatinin": creatinin,
            "rontgen_thorax": rontgen_thorax,
            "ct_scan": ct_scan,
            "usg": usg,
            "diagnosis_awal": diagnosis_awal,
            "komorbid": komorbid,
            "komplikasi": komplikasi,
            "diagnosis_akhir": diagnosis_akhir,
            "tindakan": tindakan,
            "obat": obat,
            "validasi_fornas": validasi_fornas,
            "notes_doctor": notes_doctor,
        }.items():
            if value is not None:
                setattr(mr, field, value)
        mr.updated_at = datetime.utcnow()

        # rekam medis log
        latest_version = db.query(func.max(models.MedicalRecordLog.version)) \
                           .filter(models.MedicalRecordLog.medical_record_id == mr.id) \
                           .scalar() or 0
        db.add(models.MedicalRecordLog(
            medical_record_id=mr.id,
            action="FINALIZED",
            description="Rekam medis difinalisasi via klaim",
            updated_by=user.id,
            updated_at=datetime.utcnow(),
            version=latest_version + 1,
            data_snapshot=json.dumps(mr.to_dict() if hasattr(mr, "to_dict") else {}, ensure_ascii=False),
            is_deleted=False,
            is_dummy=False
        ))

    # klaim log
    db.add(models.ClaimLog(
        claim_id=claim.id,
        action="FINALIZED",
        description="Klaim difinalisasi",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=False
    ))

    db.commit()
    db.refresh(claim)
    flash(request, "Klaim difinalisasi", "success")
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/claims")
def list_claims(
    request: Request,
    status: str | None = Query(None),
    tanggal_kunjungan: str | None = Query(None),
    patient_name: str | None = Query(None),
    jenis_kunjungan: str | None = Query(None),
    claim_id: int | None = Query(None),
    visit_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))
):
    query = db.query(models.Claim).join(models.Visit, models.Claim.visit_id == models.Visit.id)

    if status:
        query = query.filter(models.Claim.status.ilike(status))

    if jenis_kunjungan:
        query = query.filter(models.Visit.jenis_kunjungan.ilike(jenis_kunjungan))

    if tanggal_kunjungan:
        query = query.filter(models.Visit.tanggal_kunjungan == tanggal_kunjungan)

    if patient_name:
        query = query.join(models.Patient).filter(
            models.Patient.nama.ilike(f"%{patient_name}%")
        )

    if claim_id:
        query = query.filter(models.Claim.id == claim_id)

    if visit_id:
        query = query.filter(models.Claim.visit_id == visit_id)

    claims = (
        query.filter(models.Claim.is_deleted == False)
             .order_by(models.Claim.id.desc())
             .all()
    )

    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "claim_list.html",
        {
            "request": request,
            "claims": claims,
            "user": user,
            "csrf_token": csrf_token,
            "current_user": user,
            "status": status,
            "tanggal_kunjungan": tanggal_kunjungan,
            "patient_name": patient_name,
            "jenis_kunjungan": jenis_kunjungan,
            "claim_id": claim_id,
            "visit_id": visit_id,
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
    claims = query.filter(models.Claim.is_deleted == False).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Claims"
    ws.append([
        "Tanggal Klaim",
        "Nama Pasien",
        "Status",
        "Nama Dokter",
        "Simulasi Draft",
        "Ringkasan Draft",
        "Final",
        "Simulasi Final",
        "Ringkasan Final",
        "Created At",
    ])
    for c in claims:
        ws.append([
            c.claim_date,
            c.patient.nama if c.patient else "N/A",
            c.status,
            c.doctor_name,
            json.dumps(c.simulasi_draft) if not c.is_final else "N/A",
            json.dumps(c.summary_draft) if not c.is_final else "N/A",
            "Ya" if c.is_final else "Tidak",
            json.dumps(c.simulasi_draft) if c.is_final else "N/A",
            json.dumps(c.summary_draft) if c.is_final else "N/A",
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

@app.get("/claims/{claim_id}")
def claim_detail(request: Request, claim_id: int, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor","admin_rs","superadmin","coder","verifikator"))):
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return templates.TemplateResponse(
        "claim_detail.html",
        {"request": request, "claim": claim, "user": user, "current_user": user, "csrf_token": issue_csrf_token(request)}
    )


@app.post("/claims/add", name="add_claim")
def add_claim(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    record_type: Optional[str] = Form("admission"),  # inpatient / outpatient
    # Klaim
    patient_id: Optional[int] = Form(None),
    visit_id: Optional[int] = Form(None),
    hospital_id: Optional[int] = Form(None),
    doctor_id: Optional[int] = Form(None),
    doctor_name: Optional[str] = Form(None),
    claim_date: Optional[datetime] = Form(None),
    is_final: Optional[bool] = Form(False),
    # Rekam medis
    riwayat_penyakit: Optional[str] = Form(None),
    riwayat_pengobatan: Optional[str] = Form(None),
    riwayat_operasi: Optional[str] = Form(None),
    alergi: Optional[str] = Form(None),
    keluhan: Optional[str] = Form(None),
    gejala_lain: Optional[str] = Form(None),
    tekanan_darah: Optional[str] = Form(None),
    nadi: Optional[str] = Form(None),
    pernapasan: Optional[str] = Form(None),
    suhu: Optional[str] = Form(None),
    spo2: Optional[str] = Form(None),
    berat_badan: Optional[str] = Form(None),
    tinggi_badan: Optional[str] = Form(None),
    hemoglobin: Optional[str] = Form(None),
    leukosit: Optional[str] = Form(None),
    trombosit: Optional[str] = Form(None),
    gula_darah: Optional[str] = Form(None),
    creatinin: Optional[str] = Form(None),
    rontgen_thorax: Optional[str] = Form(None),
    ct_scan: Optional[str] = Form(None),
    usg: Optional[str] = Form(None),
    diagnosis_awal: Optional[str] = Form(None),
    komorbid: Optional[str] = Form(None),
    komplikasi: Optional[str] = Form(None),
    diagnosis_akhir: Optional[str] = Form(None),
    tindakan: Optional[str] = Form(None),
    obat: Optional[str] = Form(None),
    validasi_fornas: Optional[str] = Form(None),
    notes_doctor: Optional[str] = Form(None),
    summary_draft: Optional[str] = Form(None),
    simulasi_draft: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    created_at: Optional[datetime] = Form(None),
    updated_at: Optional[datetime] = Form(None),
    is_deleted: Optional[bool] = Form(False),
    is_dummy: Optional[bool] = Form(False),
    _=Depends(require_csrf_dep)
):
    if claim_date is None:
        if visit_id:
            claim_date = None   # atau pakai tanggal visit kalau ada di DB
        else:
            claim_date = datetime.utcnow()
    # 1. Buat rekam medis baru
    mr = models.MedicalRecord(
        record_type=record_type,
        patient_id=patient_id,
        visit_id=visit_id,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        is_final=is_final,
        notes_date=datetime.utcnow(),
        riwayat_penyakit=riwayat_penyakit,
        riwayat_pengobatan=riwayat_pengobatan,
        riwayat_operasi=riwayat_operasi,
        alergi=alergi,
        keluhan=keluhan,
        gejala_lain=gejala_lain,
        tekanan_darah=tekanan_darah,
        nadi=nadi,
        pernapasan=pernapasan,
        suhu=suhu,
        spo2=spo2,
        berat_badan=berat_badan,
        tinggi_badan=tinggi_badan,
        hemoglobin=hemoglobin,
        leukosit=leukosit,
        trombosit=trombosit,
        gula_darah=gula_darah,
        creatinin=creatinin,
        rontgen_thorax=rontgen_thorax,
        ct_scan=ct_scan,
        usg=usg,
        diagnosis_awal=diagnosis_awal,
        komorbid=komorbid,
        komplikasi=komplikasi,
        diagnosis_akhir=diagnosis_akhir,
        tindakan=tindakan,
        obat=obat,
        validasi_fornas=validasi_fornas,
        notes_doctor=notes_doctor,
        created_at=datetime.utcnow()-timedelta(days=5),
        updated_at=datetime.utcnow(),
        is_deleted=is_deleted,
        is_dummy=is_dummy
    )
    db.add(mr)
    db.commit()
    db.refresh(mr)

    latest_version = db.query(func.max(models.MedicalRecordLog.version))\
                   .filter(models.MedicalRecordLog.medical_record_id == mr.id)\
                   .scalar() or 0

    log = models.MedicalRecordLog(
        medical_record_id=mr.id,
        action="CREATED",
        description=f"Rekam medis {mr.id} dibuat oleh {user.name}",
        version=latest_version + 1,
        data_snapshot=json.dumps(mr.to_dict(), ensure_ascii=False),
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        is_deleted=is_deleted,
        is_dummy=is_dummy
    )

    db.add(log)
    db.commit()

    # 2. Buat klaim baru link ke rekam medis
    claim = models.Claim(
        claim_date=claim_date,
        patient_id=patient_id,
        visit_id=visit_id,
        hospital_id=hospital_id,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        medical_record_id=mr.id,
        is_final=False,       # klaim baru otomatis Draft
        status="draft",
        created_at=datetime.utcnow()-timedelta(days=5),
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=is_dummy, 
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    log = models.ClaimLog(
        claim_id=claim.id,
        action="CREATED",
        description=f"Klaim {claim.id} dibuat oleh {user.name}",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=is_dummy
    )
    db.add(log)
    db.commit()

    flash(request, "✅ ID Klaim berhasil didapatkan!", "success")
    return RedirectResponse(url=f"/claims/{claim.id}/edit", status_code=303)


@app.get("/claims/add/start")
def add_claim_start(request: Request, user=Depends(require_roles_session("doctor"))):
    """Redirect dari dashboard ke daftar pasien (mode klaim)"""
    flash(request, "Redirecting to patient list...", "info")
    return RedirectResponse("/patients?mode=claim")

@app.get("/claims/add/form/{visit_id}", response_class=HTMLResponse, name="form_add_claim")
def claim_form(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor"))  # cuma dokter yg bisa klaim
):
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit tidak ditemukan")
    patient = visit.patient

    csrf_token = issue_csrf_token(request)

    # Ambil field netral dari config
    fields = form_configs["claim_medical_record"].copy()

    # Inject hospital (auto dari akun dokter)
    if user.hospital:
        fields.insert(0, {"name": "hospital_id", "type": "hidden", "value": user.hospital.id})
        fields.insert(1, {
            "name": "hospital_name", "label": "Rumah Sakit",
            "type": "readonly", "value": user.hospital.nama
        })

    # Inject patient & visit (selalu hidden karena datang dari wizard)
    fields.insert(0, {"name": "patient_id", "type": "hidden", "value": patient.id})
    fields.insert(1, {"name": "visit_id", "type": "hidden", "value": visit.id})

    # Inject dokter (auto dari akun login)
    if user.role == "doctor":
        fields.insert(2, {
            "name": "doctor_name",
            "label": "Dokter",
            "type": "readonly",
            "value": user.name
        })
        fields.insert(3, {
            "name": "doctor_id",
            "type": "hidden",
            "value": user.id
        })
    else:
        doctors = db.query(models.User).filter(models.User.role == "doctor").filter(models.User.is_deleted == False).all()
        fields.insert(2, {
            "name": "doctor_id",
            "label": "Dokter",
            "type": "select",
            "options": [{"value": d.id, "label": d.name} for d in doctors]
        })


    return templates.TemplateResponse(
        "claim_form.html",
        {
            "request": request,
            "visit": visit,
            "patient": patient,
            "mode": "add",
            "current_user": user,
            "user": user,
            "role": user.role if isinstance(user.role, str) else user.role[0],
            "isDoctor": user.role == "doctor" or ("doctor" in user.role),
            "isVerifikator": user.role == "verifikator" or ("verifikator" in user.role),
            "csrf_token": csrf_token,
            "claim_medical_record_fields": fields,
        },
    )

@app.post("/claims/{claim_id}/update-draft", name="save_draft")
def update_claim_draft(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    _=Depends(require_csrf_dep),

    # ambil dari Form
    simulasi: str = Form(None),
    summary: str = Form(None),

    riwayat_penyakit: str = Form(None),
    riwayat_pengobatan: str = Form(None),
    riwayat_operasi: str = Form(None),
    alergi: str = Form(None),
    keluhan: str = Form(None),
    gejala_lain: str = Form(None),
    tekanan_darah: str = Form(None),
    nadi: str = Form(None),
    pernapasan: str = Form(None),
    suhu: str = Form(None),
    spo2: str = Form(None),
    berat_badan: str = Form(None),
    tinggi_badan: str = Form(None),
    hemoglobin: str = Form(None),
    leukosit: str = Form(None),
    trombosit: str = Form(None),
    gula_darah: str = Form(None),
    creatinin: str = Form(None),
    rontgen_thorax: str = Form(None),
    ct_scan: str = Form(None),
    usg: str = Form(None),
    diagnosis_awal: str = Form(None),
    komorbid: str = Form(None),
    komplikasi: str = Form(None),
    diagnosis_akhir: str = Form(None),
    tindakan: str = Form(None),
    obat: str = Form(None),
    validasi_fornas: str = Form(None),
    notes_doctor: str = Form(None),
):
    print("📥 Draft klaim form masuk!")

    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # parsing simulasi & summary dari form
    sim_data, summ_data = {}, {}
    if simulasi:
        try:
            sim_data = json.loads(simulasi)
        except Exception as e:
            print("❌ Gagal parse simulasi:", e)
    if summary:
        try:
            summ_data = json.loads(summary)
        except Exception as e:
            print("❌ Gagal parse summary:", e)

    # 🔹 Update ClaimDiagnosis & ClaimProcedure dari sim_data
    try:
        for stage, stage_data in sim_data.items():
            # Diagnosis utama & sekunder
            if "utama" in stage_data and stage_data["utama"]:
                diag = db.query(models.ClaimDiagnosis)\
                         .filter_by(claim_id=claim.id, diagnosis_text=stage_data["utama"]["name"])\
                         .first()
                if diag:
                    diag.icd10_code = stage_data["utama"].get("icd") or diag.icd10_code
                    diag.justifikasi = stage_data["utama"].get("label") or diag.justifikasi
                    diag.bukti_klinis = stage_data["utama"].get("bukti_klinis")
                    diag.syarat_klinis = stage_data["utama"].get("syarat_klinis")
                    diag.kode_ganda = stage_data["utama"].get("kode_ganda")
                    diag.z_code = stage_data["utama"].get("z_code")
                    diag.kode_bpjs_khusus = stage_data["utama"].get("kode_bpjs_khusus")
                    diag.faskes = stage_data["utama"].get("faskes")
                    diag.rawat_inap = stage_data["utama"].get("rawat_inap")
                    diag.rujukan = stage_data["utama"].get("rujukan")
                    diag.struktur_icd10 = stage_data["utama"].get("struktur_icd10")
                    diag.updated_at = datetime.utcnow()
                if not diag:
                    diag = models.ClaimDiagnosis(
                        claim_id=claim.id,
                        diagnosis_type="utama",
                        diagnosis_text=stage_data["utama"]["name"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True,
                    )
                    db.add(diag)
                    db.flush()


            for sec in stage_data.get("sekunder", []):
                diag = db.query(models.ClaimDiagnosis)\
                         .filter_by(claim_id=claim.id, diagnosis_text=sec["name"])\
                         .first()
                if diag:
                    diag.icd10_code = stage_data["utama"].get("icd") or diag.icd10_code
                    diag.justifikasi = stage_data["utama"].get("label") or diag.justifikasi
                    diag.bukti_klinis = stage_data["utama"].get("bukti_klinis")
                    diag.syarat_klinis = stage_data["utama"].get("syarat_klinis")
                    diag.kode_ganda = stage_data["utama"].get("kode_ganda")
                    diag.z_code = stage_data["utama"].get("z_code")
                    diag.kode_bpjs_khusus = stage_data["utama"].get("kode_bpjs_khusus")
                    diag.faskes = stage_data["utama"].get("faskes")
                    diag.rawat_inap = stage_data["utama"].get("rawat_inap")
                    diag.rujukan = stage_data["utama"].get("rujukan")
                    diag.struktur_icd10 = stage_data["utama"].get("struktur_icd10")
                    diag.updated_at = datetime.utcnow()
                if not diag:
                    diag = models.ClaimDiagnosis(
                        claim_id=claim.id,
                        diagnosis_type="sekunder",
                        diagnosis_text=sec["name"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True,
                    )
                    db.add(diag)
                    db.flush()


            # Tindakan utama & sekunder
            if "tindakanUtama" in stage_data and stage_data["tindakanUtama"]:
                proc = db.query(models.ClaimProcedure)\
                        .filter_by(claim_id=claim.id, procedure_text=stage_data["tindakanUtama"]["name"])\
                        .first()
                if proc:
                    # Ambil detail pertama (karena relasi one-to-many)
                    detail = db.query(models.ClaimProcedureDetail)\
                            .filter_by(procedure_id=proc.id, is_deleted=False)\
                            .first()
                    if detail:
                        detail.icd9_tindakan = stage_data["tindakanUtama"].get("icd") or detail.icd9_tindakan
                        detail.icd9_deskripsi_tindakan = stage_data["tindakanUtama"].get("deskripsi") or detail.icd9_deskripsi_tindakan
                        detail.updated_at = datetime.utcnow()
                if not proc:
                    proc = models.ClaimProcedure(
                        claim_id=claim.id,
                        procedure_type="utama",
                        procedure_text=stage_data["tindakanUtama"]["name"],
                        requirement_flag=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True
                    )
                    db.add(proc)
                    db.flush()

                    detail = models.ClaimProcedureDetail(
                        procedure_id=proc.id,
                        claim_simulation_id=claim.simulation_id,
                        icd9_tindakan=stage_data["tindakanUtama"].get("icd") or "47.09",
                        icd9_deskripsi_tindakan=stage_data["tindakanUtama"].get("deskripsi"),
                        validitas_tindakan=stage_data["tindakanUtama"].get("validitas") or "valid",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True
                    )
                    db.add(detail)
                    db.flush()


            for td in stage_data.get("tindakanSekunder", []):
                proc = db.query(models.ClaimProcedure)\
                        .filter_by(claim_id=claim.id, procedure_text=td["name"])\
                        .first()
                if proc:
                    detail = db.query(models.ClaimProcedureDetail)\
                            .filter_by(procedure_id=proc.id, is_deleted=False)\
                            .first()
                    if detail:
                        detail.icd9_tindakan = td.get("icd") or detail.icd9_tindakan
                        detail.icd9_deskripsi_tindakan = td.get("deskripsi") or detail.icd9_deskripsi_tindakan
                        detail.updated_at = datetime.utcnow()
                if not proc:
                    proc = models.ClaimProcedure(
                        claim_id=claim.id,
                        procedure_type="sekunder",
                        procedure_text=td["name"],
                        requirement_flag=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True
                    )
                    db.add(proc)
                    db.flush()

                    detail = models.ClaimProcedureDetail(
                        procedure_id=proc.id,
                        icd9_tindakan=td.get("icd") or "47.09",
                        icd9_deskripsi_tindakan=td.get("deskripsi"),
                        validitas_tindakan=td.get("validitas") or "valid",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True
                    )
                    db.add(detail)
                    db.flush()

        db.flush()                
    except Exception as e:
        print("❌ Gagal update ClaimDiagnosis/ClaimProcedure:", e)

    # 🔹 Simpan simulasi & summary via helper
    save_simulation_and_summary(db, claim.id, sim_data, summ_data)

    # 🔹 Update ClaimSimulation
    for stage, stage_data in sim_data.items():
        sims = db.query(models.ClaimSimulation).filter_by(claim_id=claim.id).all()
        for sim in sims:
            # Diagnosis utama
            if stage_data.get("utama"):
                utama_diag = db.query(models.ClaimDiagnosis)\
                    .filter_by(claim_id=claim.id, diagnosis_text=stage_data["utama"]["name"])\
                    .first()
                if not utama_diag:
                    utama_diag = models.ClaimDiagnosis(
                        claim_id=claim.id,
                        diagnosis_type="utama",
                        diagnosis_text=stage_data["utama"]["name"],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True
                    )
                    db.add(utama_diag)
                    db.flush()
                sim.diagnosis_utama_id = utama_diag.id

            # Diagnosis sekunder
            if stage_data.get("sekunder"):
                ids = []
                for sec in stage_data["sekunder"]:
                    sec_diag = db.query(models.ClaimDiagnosis)\
                        .filter_by(claim_id=claim.id, diagnosis_text=sec["name"])\
                        .first()
                    if not sec_diag:
                        sec_diag = models.ClaimDiagnosis(
                            claim_id=claim.id,
                            diagnosis_type="sekunder",
                            diagnosis_text=sec["name"],
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                            is_deleted=False,
                            is_dummy=True
                        )
                        db.add(sec_diag)
                        db.flush()
                    ids.append(sec_diag.id)
                sim.diagnosis_sekunder_ids = ids

            sim.updated_at = datetime.utcnow()


    # 🔹 Update draft claim
    claim.is_final = False
    claim.status = "draft"
    claim.updated_at = datetime.utcnow()

    # 🔹 Update rekam medis
    if claim.medical_record:
        mr = claim.medical_record
        for field, value in {
            "riwayat_penyakit": riwayat_penyakit,
            "riwayat_pengobatan": riwayat_pengobatan,
            "riwayat_operasi": riwayat_operasi,
            "alergi": alergi,
            "keluhan": keluhan,
            "gejala_lain": gejala_lain,
            "tekanan_darah": tekanan_darah,
            "nadi": nadi,
            "pernapasan": pernapasan,
            "suhu": suhu,
            "spo2": spo2,
            "berat_badan": berat_badan,
            "tinggi_badan": tinggi_badan,
            "hemoglobin": hemoglobin,
            "leukosit": leukosit,
            "trombosit": trombosit,
            "gula_darah": gula_darah,
            "creatinin": creatinin,
            "rontgen_thorax": rontgen_thorax,
            "ct_scan": ct_scan,
            "usg": usg,
            "diagnosis_awal": diagnosis_awal,
            "komorbid": komorbid,
            "komplikasi": komplikasi,
            "diagnosis_akhir": diagnosis_akhir,
            "tindakan": tindakan,
            "obat": obat,
            "validasi_fornas": validasi_fornas,
            "notes_doctor": notes_doctor,
        }.items():
            if value is not None:
                setattr(mr, field, value)
        mr.updated_at = datetime.utcnow()

        # rekam medis log
        latest_version = db.query(func.max(models.MedicalRecordLog.version)) \
                           .filter(models.MedicalRecordLog.medical_record_id == mr.id) \
                           .scalar() or 0
        db.add(models.MedicalRecordLog(
            medical_record_id=mr.id,
            action="UPDATED",
            description="Rekam medis diperbarui via draft klaim",
            updated_by=user.id,
            updated_at=datetime.utcnow(),
            version=latest_version + 1,
            data_snapshot=json.dumps(mr.to_dict() if hasattr(mr, "to_dict") else {}, ensure_ascii=False),
            is_deleted=False,
            is_dummy=False
        ))

    # klaim log
    db.add(models.ClaimLog(
        claim_id=claim.id,
        action="UPDATED",
        description="Draft klaim diperbarui",
        updated_by=user.id,
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=False
    ))

    db.commit()
    db.refresh(claim)
    flash(request, "Draft klaim berhasil diperbarui", "success")
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/claims/{id}/edit")
def edit_claim_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator", "coder", "doctor"))
):
    claim = db.query(models.Claim).get(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    patients = db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
    visits = db.query(models.Visit).filter(models.Visit.is_deleted == False).all()
    hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
    csrf_token = issue_csrf_token(request)

    # 🔹 Ambil data simulasi & summary dari tabel pecahan
    sim: dict = {}
    summ: dict = {}

    sims = db.query(models.ClaimSimulation).filter_by(claim_id=id).all()
    for s in sims:
        if s.stage not in sim:
            sim[s.stage] = {
                "utama_diagnosis": None,
                "utama_tindakan": None,
                "sekunder_diagnosis": [],
                "sekunder_tindakan": []
            }

        # --- Diagnosis utama
        if s.diagnosis_utama_id:
            sim[s.stage]["utama_diagnosis"] = {
                "id": s.diagnosis_utama_id,
                "type": "diagnosis"
            }

        # --- Tindakan utama
        if s.tindakan_utama_id:
            sim[s.stage]["utama_tindakan"] = {
                "id": s.tindakan_utama_id,
                "type": "tindakan"
            }

        # --- Diagnosis sekunder
        if s.diagnosis_sekunder_id:
            sim[s.stage]["sekunder_diagnosis"].append({
                "id": s.diagnosis_sekunder_id,
                "type": "diagnosis"
            })

        # --- Tindakan sekunder
        if s.tindakan_sekunder_id:
            sim[s.stage]["sekunder_tindakan"].append({
                "id": s.tindakan_sekunder_id,
                "type": "tindakan"
            })

    # === Diagnosis Evaluations ===
    summ["diagnosis"] = [
        {
            "validitas": d.validitas,
            "severity": d.severity,
            "kode_ina_cbg": d.kode_ina_cbg,
            "estimasi_tarif": float(d.estimasi_tarif) if d.estimasi_tarif else None,
            "syarat_klinis": d.syarat_klinis,
            "evaluasi_faskes": d.evaluasi_faskes,
            "rawat_inap": d.rawat_inap,
        }
        for d in db.query(models.ClaimDiagnosisEvaluation).filter_by(claim_id=id).all()
    ]

    # === Procedure Evaluations ===
    summ["procedure"] = [
        {
            "procedure_id": p.procedure_id,
            "validitas": p.validitas,
            "status_tindakan": p.status_tindakan,
            "tarif_impact": float(p.tarif_impact) if p.tarif_impact else None,
            "faskes": p.faskes,
            "rawat_inap": p.rawat_inap,
            "syarat_klinis": p.syarat_klinis,
        }
        for p in db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=id).all()
    ]

    # === Combination Alternatives ===
    summ["alternatif"] = [
        {
            "kombinasi_nama": a.kombinasi_nama,
            "severity": a.severity,
            "kode_ina_cbg": a.kode_ina_cbg,
            "estimasi_tarif": float(a.estimasi_tarif) if a.estimasi_tarif else None,
            "syarat_klinis": a.syarat_klinis,
            "faskes": a.faskes,
            "rawat_inap": a.rawat_inap,
            "tindakan_wajib": a.tindakan_wajib,
            "notes": a.notes,
        }
        for a in db.query(models.ClaimCombinationAlternative).filter_by(claim_id=id).all()
    ]

    # 🔹 kalau role doctor → kosongkan sim/summary (biar dokter gak lihat evaluasi verifikator)
    if (isinstance(user.role, str) and user.role == "doctor") or \
       (isinstance(user.role, (list, tuple)) and "doctor" in user.role):
        sim = {}
        summ = {}

    # --- Siapkan fields (tetap sama eksisting) …
    fields = form_configs["claim_medical_record"].copy()
    for f in fields:
        if f["name"] == "patient_id":
            f["options"] = [(p.id, p.nama) for p in patients]
            if claim.patient_id:
                f["value"] = claim.patient_id
        if f["name"] == "visit_id":
            f["options"] = [(v.id, f"{v.id} - {v.tanggal_kunjungan}") for v in visits]
            if claim.visit_id:
                f["value"] = claim.visit_id
        if f["name"] == "hospital_id":
            f["options"] = [(h.id, h.nama) for h in hospitals]
            if claim.hospital_id:
                f["value"] = claim.hospital_id
        if claim.medical_record and f["name"] in claim.medical_record.__dict__:
            f["value"] = getattr(claim.medical_record, f["name"])

    return templates.TemplateResponse("claim_form.html", {
        "request": request,
        "mode": "edit",
        "record": claim,
        "csrf_token": csrf_token,
        "current_user": user,
        "user": user,
        "role": user.role if isinstance(user.role, str) else user.role[0],
        "isDoctor": (user.role == "doctor") if isinstance(user.role, str) else ("doctor" in user.role),
        "isVerifikator": (user.role == "verifikator") if isinstance(user.role, str) else ("verifikator" in user.role),
        "fields": fields,
        "sim": sim,
        "summ": summ,
        "claim_medical_record_fields": fields,
    })


@app.post("/claims/delete/{id}", name="delete_claim")
def delete_claim(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "verifikator")),
    _=Depends(require_csrf_dep)
):
    claim = db.query(models.Claim).get(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim.is_deleted = True
    db.commit()

    flash(request, "Klaim berhasil dihapus !", "success")
    return RedirectResponse("/claims", status_code=303)


# -------------------------
# USER MANAGEMENT ROUTES (NEW)
# -------------------------
@app.get("/users")
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs"))
):
    # Superadmin hanya boleh lihat user dengan role admin_rs
    if current_user.role == "superadmin":
        users = db.query(models.User).filter(models.User.role == "admin_rs", models.User.is_deleted == False).order_by(models.User.id.desc()).all()
    
    # Admin RS hanya boleh lihat user RS yang sama, selain dirinya
    elif current_user.role == "admin_rs":
        users = (
            db.query(models.User)
              .filter(
                  models.User.hospital_id == current_user.hospital_id,
                  models.User.role.in_(["doctor", "coder", "verifikator", "costing", "validator", "manajemen"]),
                  models.User.is_deleted == False,
              )
              .order_by(models.User.id.desc())
              .all()
        )
    else:
        users = []  # fallback (nggak boleh lihat)

    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse(
        "user_list.html",
        {
            "request": request,
            "users": users,
            "user": current_user,
            "current_user": current_user,
            "csrf_token": csrf_token,
        },
    )


@app.get("/users/add")
def add_user_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs"))
):
    csrf_token = issue_csrf_token(request)
    fields = form_configs["user"].copy()

    for f in fields:
        # 🔹 Role
        if f["name"] == "role":
            if current_user.role == "superadmin":
                f["type"] = "hidden"
                f["value"] = "admin_rs"
                f["display"] = "Admin RS"
            elif current_user.role == "admin_rs":
                f["type"] = "select"
                f["options"] = [
                    ("doctor", "Dokter"),
                    ("coder", "Coder"),
                    ("verifikator", "Verifikator"),
                    ("costing", "Costing"),
                    ("validator", "Validator"),
                    ("manajemen", "Manajemen")
                ]

        # 🔹 Hospital
        if f["name"] == "hospital_id":
            if current_user.role == "superadmin":
                hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
                f["type"] = "select"
                f["options"] = [(h.id, h.nama) for h in hospitals]

            elif current_user.role == "admin_rs":
                f["type"] = "readonly"
                f["value"] = current_user.hospital.nama if current_user.hospital else "-"
                f["hidden_value"] = current_user.hospital_id if current_user.hospital_id else None

    return templates.TemplateResponse("user_form.html", {
        "request": request,
        "mode": "add",
        "user": current_user,
        "current_user": current_user,
        "csrf_token": csrf_token,
        "fields": fields
    })


@app.post("/users/add", name="add_user")
def add_user(
    request: Request,
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    hospital_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep)
):
    if role not in ["admin_rs", "doctor", "coder", "verifikator", "costing", "validator", "manajemen"]:
        raise HTTPException(status_code=400, detail="Role tidak valid")

    # admin_rs bikin user → otomatis sama RS-nya
    if current_user.role == "admin_rs":
        hospital_id = current_user.hospital_id

    user = models.User(
        email=email,
        name=name,
        role=role,
        hospital_id=hospital_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    flash(request, "User berhasil ditambahkan!", "success")
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

    fields = form_configs["user"].copy()

    for f in fields:
        # 🔹 Role
        if f["name"] == "role":
            if current_user.role == "superadmin":
                f["options"] = [("admin_rs", "Admin RS")]
                f["type"] = "select"
            elif current_user.role == "admin_rs":
                f["options"] = [
                    ("doctor", "Dokter"),
                    ("coder", "Coder"),
                    ("verifikator", "Verifikator"),
                    ("costing", "Costing"),
                    ("validator", "Validator"),
                    ("manajemen", "Manajemen")
                ]
                f["type"] = "select"

        # 🔹 Hospital
        if f["name"] == "hospital_id":
            if current_user.role == "superadmin":
                hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
                f["type"] = "select"
                f["options"] = [(h.id, h.nama) for h in hospitals]

            elif current_user.role == "admin_rs":
                f["type"] = "readonly"
                f["value"] = current_user.hospital.nama if current_user.hospital else "-"
                f["hidden_value"] = current_user.hospital_id if current_user.hospital_id else None

    return templates.TemplateResponse("user_form.html", {
        "request": request,
        "mode": "edit",
        "record": target_user,
        "csrf_token": csrf_token,
        "current_user": current_user,
        "fields": fields
    })

    
@app.post("/users/{user_id}/edit", name='edit_user')
def edit_user(
    request: Request,
    user_id: int,
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    hospital_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs")),
    _=Depends(require_csrf_dep)
):
    if role not in ["admin_rs", "doctor", "coder", "verifikator", "costing", "validator", "manajemen"]:
        raise HTTPException(status_code=400, detail="Role tidak valid")
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.name = name
    user.email = email
    user.role = role
    if current_user.role == "superadmin" and hospital_id:
        user.hospital_id = hospital_id
    elif current_user.role == "admin_rs":
        user.hospital_id = current_user.hospital_id
    db.commit()
    db.refresh(user)
    flash(request, "User berhasil diperbarui!", "success")
    return RedirectResponse(url="/users", status_code=303)

@app.get("/users/{user_id}/delete", name="delete_user")
def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin", "admin_rs"))
):
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    flash(request, "User berhasil dihapus!", "success")
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
    visits = query.order_by(models.Visit.id.desc()).filter(models.Visit.is_deleted == False).all()
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
    visits = visits.order_by(models.Visit.id.desc()).filter(models.Visit.is_deleted == False).all()
    patient = db.query(models.Patient).get(patient_id)
    return templates.TemplateResponse(
        "visit_list.html",
        {"request": request, "visits": visits, "patient": patient, "flow": flow, "user": user, "current_user": user, "csrf_token": issue_csrf_token(request)}
    )

@app.get("/visits/add")
def add_visit_form(request: Request, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor", "admin_rs"))):
    patient_id = request.query_params.get("patient_id")
    patient = db.query(models.Patient).get(patient_id) if patient_id else None
    patients = db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
    hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
    csrf_token = issue_csrf_token(request)

    fields = form_configs["visit"].copy()
    for f in fields:
        if f["name"] == "hospital_name" and user.hospital:
            f["type"] = "readonly"
            f["value"] = user.hospital.nama
            f["hidden_name"] = "hospital_id"
            f["hidden_value"] = user.hospital_id

    # Doctor (selalu dokter yang login)
        if f["name"] == "doctor_name":
            f["type"] = "readonly"
            f["value"] = user.name
            f["hidden_name"] = "doctor_id"
            f["hidden_value"] = user.id
    # Patient (jika ada patient_id di query param)       
        if f["name"] == "patient_id":
            f["options"] = [(p.id, p.nama) for p in patients]
    return templates.TemplateResponse("visit_form.html", {
        "request": request,
        "mode": "add",
        "user": user,
        "visit": None,
        "flow": None,
        "hospitals": hospitals,
        "patient": patient,
        "patient_id": patient_id,
        "patients" : patients,
        "csrf_token": csrf_token,
        "current_user": user,
        "fields": fields   # dynamic
    })

@app.post("/visits/add", name="add_visit")
def add_visit(
    request: Request,
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
        patient_id=patient_id,
        hospital_id=current_user.hospital_id,
        eksternal_id=eksternal_id,
        sumber=sumber,
        poli=poli,
        doctor_id=current_user.id,
        doctor_name=current_user.name,   # snapshot nama saat itu
        tanggal_kunjungan=tanggal_kunjungan,
        jenis_kunjungan=jenis_kunjungan,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_deleted=False,
        is_dummy=True
    )

    db.add(visit)
    db.commit()
    db.refresh(visit)
    flash(request, "Kunjungan berhasil ditambahkan!", "success")
    return RedirectResponse(url="/visits", status_code=303)

@app.get("/visits/edit/{visit_id}", name='edit_visit')
def edit_visit_form(request: Request, visit_id: int, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor", "admin_rs"))):
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    patients = db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
    hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).all()
    csrf_token = issue_csrf_token(request)

    fields = form_configs["visit"].copy()
    for f in fields:
        if f["name"] == "patient_id":
            f["options"] = [(p.id, p.nama) for p in patients]
        if f["name"] == "hospital_id":
            f["options"] = [(h.id, h.nama) for h in hospitals]

    return templates.TemplateResponse("visit_form.html", {
        "request": request,
        "mode": "edit",
        "record": visit,
        "csrf_token": csrf_token,
        "current_user": user,
        "user": user,
        "flow": None,
        "hospitals": hospitals,
        "patients": patients,
        "fields": fields  # dynamic
    })

@app.post("/visits/edit/{visit_id}", name='edit_visit')
def edit_visit(
    request: Request,
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
    updated_at: Optional[datetime] = Form(None),
    is_deleted: Optional[bool] = Form(False),
    is_dummy: Optional[bool] = Form(True),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "admin_rs")),
    _=Depends(require_csrf_dep)
):
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    visit.patient_id = patient_id or None
    visit.hospital_id = current_user.hospital_id,
    visit.eksternal_id = eksternal_id or None
    visit.sumber = sumber or None
    visit.poli = poli or None
    visit.doctor_id = current_user.id
    visit.doctor_name = current_user.name
    visit.tanggal_kunjungan = tanggal_kunjungan or None
    visit.jenis_kunjungan = jenis_kunjungan or None
    visit.created_at = created_at or datetime.utcnow()
    visit.updated_at = datetime.utcnow()
    visit.is_deleted = False
    visit.is_dummy = True
    db.commit()
    db.refresh(visit)
    flash(request, "Kunjungan berhasil diperbarui!", "success")
    return RedirectResponse(url="/visits", status_code=303)

@app.post("/visits/delete/{visit_id}")
def delete_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    request: Request = None,
    _=Depends(require_csrf_dep)
):
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    visit.is_deleted = True
    db.commit()

    flash(request, "Visit berhasil dihapus !", "success")
    return RedirectResponse("/visits", status_code=303)


# -------------------------
# VISIT ROUTES (END)

# Hospital Routes

@app.get("/hospitals")
def list_hospitals(request: Request, db: Session = Depends(get_db), user=Depends(require_roles_session("superadmin","admin_rs"))):
    hospitals = db.query(models.Hospital).filter(models.Hospital.is_deleted == False).order_by(models.Hospital.id.desc()).all()
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
        {"request": request, "mode": "add", "user": user, "csrf_token": csrf_token, "current_user": user, "fields": form_configs["hospital"]}
    )


@app.post("/hospitals/add", name="add_hospital")
def add_hospital(
    request: Request,
    nama: Optional[str] = Form(None),
    kode_hospital: Optional[str] = Form(None),
    tipe_hospital: Optional[str] = Form(None),
    jenis_hospital: Optional[str] = Form(None),
    alamat: Optional[str] = Form(None),
    telepon: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    status_akreditasi: Optional[str] = Form(None),
    status_bridging: Optional[str] = Form(None),
    jumlah_tempat_tidur: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin","admin_rs")),
    _=Depends(require_csrf_dep)
):
    hospital = models.Hospital(
        kode_hospital=kode_hospital,
        tipe_hospital=tipe_hospital,
        jenis_hospital=jenis_hospital,
        nama=nama,
        alamat=alamat,
        telepon=telepon,
        email=email,
        status_akreditasi=status_akreditasi,
        status_bridging=status_bridging,
        jumlah_tempat_tidur=jumlah_tempat_tidur,
        admin_id=current_user.id
    )
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    flash(request, "Hospital berhasil ditambahkan!", "success")
    return RedirectResponse(url="/hospitals", status_code=303)

@app.get("/hospitals/{hospital_id}/edit", name='edit_hospital')
def edit_hospital_form(request: Request, hospital_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles_session("superadmin","admin_rs"))):
    hospital = db.query(models.Hospital).get(hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("hospital_form.html", {
        "request": request,
        "mode": "edit",
        "record": hospital,
        "csrf_token": csrf_token,
        "current_user": current_user,
        "user": current_user,
        "fields": form_configs["hospital"]  # static
    })


@app.post("/hospitals/{hospital_id}/edit", name='edit_hospital')
def edit_hospital(
    request: Request,
    hospital_id: int,
    nama: Optional[str] = Form(None),
    alamat: Optional[str] = Form(None),
    telepon: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    status_akreditasi: Optional[str] = Form(None),
    status_bridging: Optional[str] = Form(None),
    jumlah_tempat_tidur: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin","admin_rs")),
    _=Depends(require_csrf_dep)
):
    hospital = db.query(models.Hospital).get(hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    hospital.kode_hospital = kode_hospital
    hospital.tipe_hospital = tipe_hospital
    hospital.jenis_hospital = jenis_hospital
    hospital.nama = nama
    hospital.alamat = alamat
    hospital.telepon = telepon
    hospital.email = email
    hospital.status_akreditasi = status_akreditasi
    hospital.status_bridging = status_bridging
    hospital.jumlah_tempat_tidur = jumlah_tempat_tidur
    db.commit()
    db.refresh(hospital)
    flash(request, "Hospital berhasil diperbarui!", "success")
    return RedirectResponse(url="/hospitals", status_code=303)

@app.post("/hospitals/delete/{hospital_id}")
def delete_hospital(
    hospital_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs", "superadmin")),
    request: Request = None,
    _=Depends(require_csrf_dep)
):
    hospital = db.query(models.Hospital).get(hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    hospital.is_deleted = True
    db.commit()

    flash(request, "Rumah sakit berhasil dihapus !", "success")
    return RedirectResponse("/hospitals", status_code=303)


#---------------------
# End Hospital Routes
#---------------------

# Medical Record Routes

from datetime import date

@app.get("/medical-records", name="list_medical_records")
def list_medical_records(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    q: str | None = Query(None),       
    status: str | None = Query(None),  
    date_str: str | None = Query(None, alias="date"),  # ambil mentah sebagai string
    user=Depends(require_roles_session("doctor","admin_rs"))
):
    page_size = 10
    query = db.query(models.MedicalRecord).join(models.Patient)

    if q:
        query = query.filter(models.Patient.nama.ilike(f"%{q}%"))
    if status:
        if status == "final":
            query = query.filter(models.MedicalRecord.is_final.is_(True))
        elif status == "draft":
            query = query.filter(models.MedicalRecord.is_final.is_(False))
    if date_str:
        try:
            date_val = date.fromisoformat(date_str)
            query = query.filter(models.MedicalRecord.notes_date == date_val)
        except ValueError:
            pass  # kalau bukan format date valid, abaikan saja

    total = query.count()
    records = (
        query.order_by(models.MedicalRecord.id.desc())
             .filter(models.MedicalRecord.is_deleted == False)
             .offset((page-1)*page_size)
             .limit(page_size)
             .all()
    )
    total_pages = (total + page_size - 1) // page_size

    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("medical_record_list.html", {
        "request": request,
        "medical_records": records,
        "page": page,
        "total_pages": total_pages,
        "q": q,
        "status": status,
        "date": date_str,
        "csrf_token": csrf_token,
        "user": user,
        "current_user": user
    })

@app.get("/medical-records/{record_id}/edit", name="edit_medical_record")
def edit_medical_record_form(request: Request, record_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles_session("doctor", "admin_rs"))):
    medical_record = db.query(models.MedicalRecord).get(record_id)
    claims = db.query(models.Claim).filter(models.Claim.is_deleted == False).all()
    if not medical_record:
        raise HTTPException(status_code=404, detail="Medical record not found")
    patients = db.query(models.Patient).filter(models.Patient.is_deleted == False).all()
    csrf_token = issue_csrf_token(request)

    fields = form_configs["claim_medical_record"].copy()
    for f in fields:
        if f["name"] == "patient_id":
            f["options"] = [(p.id, p.nama) for p in patients]
            f["type"] = "select"

    return templates.TemplateResponse("claim_form.html", {
        "request": request,
        "mode": "edit",
        "record_id": record_id,
        "form_config": form_configs["claim_medical_record"],
        "user": current_user,
        "claims": claims,
        "patients": patients,
        "record": medical_record,
        "csrf_token": csrf_token,
        "current_user": current_user,
        "fields": fields  # dynamic
    })


@app.post("/medical-records/{record_id}/edit", name="update_medical_record")
def update_medical_record(
    request: Request,
    record_id: int,   # path param dulu
    update_data: dict = Body(...),
    user_id: int = Form(...),  # kalau dari form, atau Depends(get_current_user_id) kalau dari session
    db: Session = Depends(get_db),
    current_user = Depends(require_roles_session("doctor", "admin_rs"))
):
    # Validasi dan ambil data rekam medis
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        return None

    # Ambil versi terakhir
    last_version = (
        db.query(MedicalRecordLog.version)
        .filter(MedicalRecordLog.medical_record_id == record.id)
        .order_by(MedicalRecordLog.version.desc())
        .first()
    )
    new_version = (last_version[0] + 1) if last_version else 1

    log = models.MedicalRecordLog(
    medical_record_id=record.id,
    action="UPDATED",
    description="Rekam medis diperbarui",
    updated_by=user.id,
    updated_at=datetime.utcnow(),
    data_snapshot=json.dumps(record.to_dict(), ensure_ascii=False)
    )
    db.add(log)


    # Update data baru
    for key, value in update_data.items():
        setattr(record, key, value)

    db.commit()
    db.refresh(record)
    flash(request, "Rekam medis berhasil diperbarui!", "success")
    return templates.TemplateResponse(
        "medical_record_detail.html",
        {"request": request, "record": record, "logs": record.logs}
)


@app.post("/medical-records/{record_id}/delete", name="delete_medical_record")
def delete_medical_record(
    record_id: int,
    db: Session = Depends(get_db),
    request: Request = None,
    current_user=Depends(require_roles_session("doctor", "admin_rs")),
    _=Depends(require_csrf_dep)  # ✅ cek token
):
    medical_record = db.query(models.MedicalRecord).get(record_id)
    if not medical_record:
        raise HTTPException(status_code=404, detail="Medical record not found")

    # Soft delete, jangan hard delete
    medical_record.is_deleted = True
    db.commit()

    flash(request, "Medical record berhasil dihapus !", "success")
    return RedirectResponse(url="/medical_records", status_code=303)


@app.get("/medical-records/{record_id}/logs", name="medical_record_logs")
def medical_record_logs(record_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles_session("doctor"))):
    record = db.query(models.MedicalRecord).get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")

    logs = db.query(models.MedicalRecordLog)\
             .filter(models.MedicalRecordLog.medical_record_id == record_id, models.MedicalRecordLog.is_deleted == False)\
             .order_by(models.MedicalRecordLog.version.desc())\
             .all()

    return templates.TemplateResponse(
        "medical_record_detail.html",
        {"request": request, "record": record, "logs": logs, "user": current_user, "current_user": current_user}
    )


# End Medical Record Routes

