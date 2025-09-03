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
from datetime import datetime, date
from openpyxl import Workbook, load_workbook
from typing import Optional
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from jose import jwt, JWTError
from .form_configs import form_configs
from . import models, crud, config
from .database import SessionLocal, engine, Base
from .auth import verify_jwt, get_db, require_roles_session, issue_csrf_token, require_csrf_dep
import requests, io, json, secrets, base64, hashlib, httpx


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
    flash(request, "Login successful!", "success")
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
        func.date(models.Claim.claim_date) == datetime.today().date()
    ).count()
    total_claims = db.query(models.Claim).count()

    # klaim terbaru
    claims = (
        db.query(models.Claim)
        .options(joinedload(models.Claim.patient))
        .order_by(models.Claim.id.desc())
        .limit(10)
        .all()
    )

    # klaim draft & final
    draft_claims = db.query(models.Claim).filter(models.Claim.is_final == False).count()
    final_claims = db.query(models.Claim).filter(models.Claim.is_final == True).count()
    draft_claims_list = []
    if current_user.role == "verifikator":
        draft_claims_list = (
            db.query(models.Claim)
            .filter(models.Claim.is_final == False)
            .options(joinedload(models.Claim.patient))
            .order_by(models.Claim.id.desc())
            .all()
        )
    final_claims_list = (
        db.query(models.Claim)
        .filter(models.Claim.is_final == True)
        .options(joinedload(models.Claim.patient))
        .order_by(models.Claim.id.desc())
        .all()
    )

    # role check
    if current_user.role in ["doctor", "coder", "verifikator"]:
        pasien_list = db.query(models.Patient).all()
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


@app.get("/patients/add",name="add_patient", response_class=HTMLResponse)
def add_form(request: Request, user=Depends(require_roles_session("doctor"))):
    csrf_token = issue_csrf_token(request)
    return templates.TemplateResponse("patient_form.html", {"request": request, "mode": "add", "patient": None, "csrf_token": csrf_token, "user": user, "current_user": user, "fields": form_configs["patient"]})


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
                "no_hp": no_hp,
                "no_ktp": no_ktp,
                "no_bpjs": no_bpjs,
                "no_rm": no_rm
            },
            "user": user,
            "current_user": user,
            "error_msg": error_msg
        })

@app.get("/patients/edit/{patient_id}", name="edit_patient")
def edit_form(patient_id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor"))):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
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
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
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
            "nama": nama,
            "tanggal_lahir": tanggal_lahir or None,
            "alamat": alamat or None,
            "jenis_kelamin": jenis_kelamin or None,
            "email": email or None,
            "no_hp": no_hp or None
        })
        flash(request, success_msg, "success")
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
    flash(request, "Pasien berhasil dihapus!", "success")
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

# Rekomendasi AI untuk Klaim

def make_group(prefix, icd_prefix):
    """3 penyakit utama + 2 turunan per penyakit"""
    def make_modal(icd):
        return {
            "aspek_klinis": {
                "justifikasi": "GFR 15-29",
                "bukti": "Belum ada bukti",
                "syarat": "Belum ditentukan"
            },
            "icd10": {
                "struktur_kode": icd,
                "kode_ganda": "Tidak",
                "z_code": "-",
                "kode_bpjs_khusus": "-"
            },
            "tindakan": [
                {"nama": "Operasi Apendektomi"},
                {"nama": "CT Scan Abdomen"},
                {"nama": "Pemeriksaan Laboratorium"},
                {"nama": "USG Abdomen"},
                {"nama": "MRI Kepala"},
                {"nama": "Pemasangan Infus"},
                {"nama": "Pemberian Oksigen"},
                {"nama": "Terapi Nebulizer"},
                {"nama": "Transfusi Darah"},
            ],
            "rawat_inap": {
                "indikasi": "Tidak ada indikasi khusus",
                "lama_rawat": "3 hari",
                "perpanjangan": "Tidak"
            },
            "faskes": {"kesesuaian_rs": "Tipe C"},
            "rujukan": {"syarat": "Tidak ada", "kelayakan": "Layak"}
        }

    return [
        {"kategori": f"{prefix} 1", "klinis": f"{prefix} deskripsi 1",
         "icd": f"{icd_prefix}1", "tindakan": "Observasi", "score": 90,
         "child": False, "modal_detail": make_modal(f"{icd_prefix}1")},
        {"kategori": f"→ {prefix} 1a", "klinis": f"{prefix} child a",
         "icd": f"{icd_prefix}1a", "tindakan": "Rawat Inap", "score": 80,
         "child": True, "modal_detail": make_modal(f"{icd_prefix}1a")},
        {"kategori": f"→ {prefix} 1b", "klinis": f"{prefix} child b",
         "icd": f"{icd_prefix}1b", "tindakan": "ICU", "score": 70,
         "child": True, "modal_detail": make_modal(f"{icd_prefix}1b")},

        {"kategori": f"{prefix} 2", "klinis": f"{prefix} deskripsi 2",
         "icd": f"{icd_prefix}2", "tindakan": "Antibiotik IV", "score": 88,
         "child": False, "modal_detail": make_modal(f"{icd_prefix}2")},
        {"kategori": f"→ {prefix} 2a", "klinis": f"{prefix} child a",
         "icd": f"{icd_prefix}2a", "tindakan": "Observasi", "score": 78,
         "child": True, "modal_detail": make_modal(f"{icd_prefix}2a")},
        {"kategori": f"→ {prefix} 2b", "klinis": f"{prefix} child b",
         "icd": f"{icd_prefix}2b", "tindakan": "Rawat Inap", "score": 68,
         "child": True, "modal_detail": make_modal(f"{icd_prefix}2b")},

        {"kategori": f"{prefix} 3", "klinis": f"{prefix} deskripsi 3",
         "icd": f"{icd_prefix}3", "tindakan": "Ventilasi Mekanik", "score": 85,
         "child": False, "modal_detail": make_modal(f"{icd_prefix}3")},
        {"kategori": f"→ {prefix} 3a", "klinis": f"{prefix} child a",
         "icd": f"{icd_prefix}3a", "tindakan": "Oksigen Nasal", "score": 75,
         "child": True, "modal_detail": make_modal(f"{icd_prefix}3a")},
        {"kategori": f"→ {prefix} 3b", "klinis": f"{prefix} child b",
         "icd": f"{icd_prefix}3b", "tindakan": "Intubasi", "score": 65,
         "child": True, "modal_detail": make_modal(f"{icd_prefix}3b")},
    ]



def make_dummy(tab):
    return {
        "diagnosis": make_group("Diagnosis", f"{tab.upper()}DX"),
        "komorbid": make_group("Komorbid", f"{tab.upper()}KM"),
        "komplikasi": make_group("Komplikasi", f"{tab.upper()}KP"),
        "tindakan": [
            {"kategori": "Operasi Apendektomi", "klinis": "Prosedur usus buntu", "icd": "", "tindakan": "47.0", "score": 88, "child": False},
            {"kategori": "CT Scan Abdomen", "klinis": "Imaging perut", "icd": "", "tindakan": "88.01", "score": 77, "child": False},
            {"kategori": "Lab Darah Lengkap", "klinis": "Pemeriksaan darah", "icd": "", "tindakan": "90.0", "score": 72, "child": False},
        ],
        "simulasi": {
            "utama": None,
            "sekunder": [],
            "tindakanUtama": None,
            "tindakanSekunder": [],
            "tarifDraft": f"Rp 15.000.000"
        },
        "summary": {
            "klinis": [
                {"status": "valid", "message": "Diagnosis sesuai klinis", "confidence": 0.9, "target": ["Diagnosis Utama", "Observasi"]},
                {"status": "warning", "message": "Komorbid perlu cek", "confidence": 0.7, "target": ["Hipertensi", "Rawat Inap"]},
                {"status": "invalid", "message": "Komplikasi tidak sesuai", "confidence": 0.5, "target": ["Syok Dengue", "Ventilasi Mekanik"]},
            ],
            "regulasi": [
                {"status": "valid", "message": "Sesuai PNPK", "confidence": 0.85, "target": ["Diagnosis", "PNPK"]},
                {"status": "warning", "message": "Butuh cek Fornas", "confidence": 0.65, "target": ["Komorbid", "Fornas"]},
                {"status": "invalid", "message": "Tidak sesuai Permenkes", "confidence": 0.4, "target": ["Komplikasi", "Permenkes"]},
            ],
            "tarif": [
                {"status":"valid", "message":"Rp 5.000.000", "confidence":0.9, "target":["Operasi Apendektomi"]},
                {"status":"warning", "message":"Rp 2.500.000", "confidence":0.6, "target":["CT Scan Abdomen"]},
                {"status":"invalid", "message":"Rp 1.000.000", "confidence":0.3, "target":["Lab Darah Lengkap"]}
            ]

        }
    }


@app.post("/ai/recommendation")
def ai_recommendation(payload: dict = Body(...)):
    return {
        "admission": make_dummy("admission"),
        "daily": make_dummy("daily"),
        "discharge": make_dummy("discharge"),
    }

# End Rekomendasi AI untuk Klaim

@app.post("/claims/{claim_id}/finalize")
def finalize_claim(
    claim_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator"))
):
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim.is_final = True
    claim.status = "submitted"

    # simpan summary AI ke tabel summary
    summary = ClaimAIRecommendationsSummary(
        claim_id=claim_id,
        klinis=payload.get("summary", {}).get("klinis"),
        regulasi=payload.get("summary", {}).get("regulasi"),
        tarif=payload.get("summary", {}).get("tarif")
    )
    db.add(summary)
    db.commit()
    flash("Claim finalized successfully", "success")
    return RedirectResponse(url="/dashboard", status_code=303)

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
        "Nama Dokter",
        "Diagnosis Awal",
        "Kode ICD",
        "Tindakan",
        "Obat",
        "Status",
        "Hasil",
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


@app.post("/claims/add", name="add_claim")
def add_claim(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor")),
    patient_id: Optional[int] = Form(None),
    visit_id: Optional[int] = Form(None),
    hospital_id: Optional[int] = Form(None),
    doctor_id: Optional[int] = Form(None),
    doctor_name: Optional[str] = Form(None),
    claim_date: Optional[datetime] = Form(datetime.utcnow()),
    is_final: Optional[bool] = Form(False),
    # Rekam medis
    riwayat_penyakit: Optional[str] = Form(None),
    riwayat_pengobatan: Optional[str] = Form(None),
    riwayat_operasi: Optional[str] = Form(None),
    alergi: Optional[str] = Form(None),
    keluhan: Optional[str] = Form(None),
    gejala_lain: Optional[str] = Form(None),
    td: Optional[str] = Form(None),
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
):
    # 1. Buat rekam medis baru
    mr = models.MedicalRecord(
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
        td=td,
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
    )
    db.add(mr)
    db.commit()
    db.refresh(mr)

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
        status="draft" 
    )
    db.add(claim)
    db.commit()

    flash(request, "✅ Klaim berhasil diubah!", "success")
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
        doctors = db.query(models.User).filter(models.User.role == "doctor").all()
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

@app.post("/claims/{claim_id}/update-draft")
def update_claim_draft(
    claim_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor"))  # hanya dokter yang bisa save draft
):
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # simpan hasil simulasi/summary ke kolom JSON (pastikan model Claim ada field simulasi_draft & summary_draft tipe JSON)
    claim.simulasi_draft = payload.get("simulasi")
    claim.summary_draft = payload.get("summary")
    claim.is_final = False
    claim.status = "draft"

    db.commit()
    db.refresh(claim)

    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/claims/{id}/edit")
def edit_claim_form(request: Request, id: int, db: Session = Depends(get_db), user=Depends(require_roles_session("verifikator","coder","doctor"))):
    claim = db.query(models.Claim).get(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    patients = db.query(models.Patient).all()
    visits = db.query(models.Visit).all()
    hospitals = db.query(models.Hospital).all()
    csrf_token = issue_csrf_token(request)

    fields = form_configs["claim_medical_record"].copy()
    # inject select options
    for f in fields:
        if f["name"] == "patient_id":
            f["options"] = [(p.id, p.nama) for p in patients]
        if f["name"] == "visit_id":
            f["options"] = [(v.id, f"{v.id} - {v.tanggal_kunjungan}") for v in visits]
        if f["name"] == "hospital_id":
            f["options"] = [(h.id, h.nama) for h in hospitals]

    return templates.TemplateResponse("claim_form.html", {
        "request": request,
        "mode": "edit",
        "record": claim,
        "csrf_token": csrf_token,
        "current_user": user,
        "user": user,
        "role": user.role if isinstance(user.role, str) else user.role[0],
        "isDoctor": user.role == "doctor" or ("doctor" in user.role),
        "isVerifikator": user.role == "verifikator" or ("verifikator" in user.role),
        "fields": fields,  # dynamic
        "saved_simulasi": claim.simulasi_draft or {
            "admission": {"utama":"", "sekunder":[], "tindakanUtama":"", "tindakanSekunder":[], "tarifDraft":""},
            "daily": {"utama":"", "sekunder":[], "tindakanUtama":"", "tindakanSekunder":[], "tarifDraft":""},
            "discharge": {"utama":"", "sekunder":[], "tindakanUtama":"", "tindakanSekunder":[], "tarifDraft":""}
        },
        "saved_summary": claim.summary_draft or {
            "admission": {"klinis":{}, "regulasi":{}, "tarif":{}},
            "daily": {"klinis":{}, "regulasi":{}, "tarif":{}},
            "discharge": {"klinis":{}, "regulasi":{}, "tarif":{}}
        }
    })



@app.post("/claims/{id}/edit", name="update_claim")
def update_claim(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator","coder","doctor")),
    claim_date: datetime = Form(datetime.utcnow()),
    is_final: bool = Form(False),
    diagnosis_awal: str = Form(None),
    diagnosis_akhir: str = Form(None),
    tindakan: str = Form(None),
    obat: str = Form(None),
    notes_doctor: str = Form(None),
):
    claim = db.query(Claim).filter(Claim.id == id).first()
    if not claim:
        flash(request, "❌ Klaim tidak ditemukan", "error")
        return RedirectResponse(url="/claims", status_code=303)

    # Update klaim
    claim.claim_date = claim_date
    claim.is_final = is_final

    # Update rekam medis terkait
    if claim.medical_record:
        claim.medical_record.is_final = is_final
        claim.medical_record.diagnosis_awal = diagnosis_awal
        claim.medical_record.diagnosis_akhir = diagnosis_akhir
        claim.medical_record.tindakan = tindakan
        claim.medical_record.obat = obat
        claim.medical_record.notes_doctor = notes_doctor

    db.commit()
    flash(request, "✅ Klaim berhasil diperbarui!", "success")
    return RedirectResponse(url="/dashboard", status_code=303)

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
    flash(request, "Klaim berhasil dihapus!", "success")
    return RedirectResponse(url="/claims", status_code=303)

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
        users = db.query(models.User).filter(models.User.role == "admin_rs").order_by(models.User.id.desc()).all()
    
    # Admin RS hanya boleh lihat user RS yang sama, selain dirinya
    elif current_user.role == "admin_rs":
        users = (
            db.query(models.User)
              .filter(
                  models.User.hospital_id == current_user.hospital_id,
                  models.User.role.in_(["doctor", "coder", "verifikator", "costing", "validator", "manajemen"])
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
                hospitals = db.query(models.Hospital).all()
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
                hospitals = db.query(models.Hospital).all()
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
        {"request": request, "visits": visits, "patient": patient, "flow": flow, "user": user, "current_user": user, "csrf_token": issue_csrf_token(request)}
    )

@app.get("/visits/add")
def add_visit_form(request: Request, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor", "admin_rs"))):
    patients = db.query(models.Patient).all()
    hospitals = db.query(models.Hospital).all()
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

    return templates.TemplateResponse("visit_form.html", {
        "request": request,
        "mode": "add",
        "user": user,
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
    flash(request, "Kunjungan berhasil ditambahkan!", "success")
    return RedirectResponse(url="/visits", status_code=303)

@app.get("/visits/edit/{visit_id}", name='edit_visit')
def edit_visit_form(request: Request, visit_id: int, db: Session = Depends(get_db), user=Depends(require_roles_session("doctor", "admin_rs"))):
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    patients = db.query(models.Patient).all()
    hospitals = db.query(models.Hospital).all()
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
    flash(request, "Kunjungan berhasil diperbarui!", "success")
    return RedirectResponse(url="/visits", status_code=303)

@app.get("/visits/delete/{visit_id}", name="delete_visit")
def delete_visit(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "admin_rs"))
):
    visit = db.query(models.Visit).get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    db.delete(visit)
    db.commit()
    flash(request, "Kunjungan berhasil dihapus!", "success")
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

@app.get("/hospitals/{hospital_id}/delete", name='delete_hospital')
def delete_hospital(
    request: Request,
    hospital_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("superadmin","admin_rs"))
):
    hospital = db.query(models.Hospital).get(hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    db.delete(hospital)
    db.commit()
    flash(request, "Hospital berhasil dihapus!", "success")
    return RedirectResponse(url="/hospitals", status_code=303)

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
    if not medical_record:
        raise HTTPException(status_code=404, detail="Medical record not found")
    patients = db.query(models.Patient).all()
    csrf_token = issue_csrf_token(request)

    fields = form_configs["medical_record"].copy()
    for f in fields:
        if f["name"] == "patient_id":
            f["options"] = [(p.id, p.nama) for p in patients]
            f["type"] = "select"

    return templates.TemplateResponse("medical_record_form.html", {
        "request": request,
        "mode": "edit",
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

    # Simpan snapshot lama ke log
    snapshot = {col.name: getattr(record, col.name) for col in record.__table__.columns}

    log = MedicalRecordLog(
        medical_record_id=record.id,
        version=new_version,
        data_snapshot=snapshot,
        updated_by=user_id
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
    flash(request, "Medical record berhasil dihapus!", "success")
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

