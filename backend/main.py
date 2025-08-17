from fastapi import FastAPI, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from urllib.parse import urlencode
from datetime import datetime
from openpyxl import Workbook, load_workbook
from .database import SessionLocal, engine, Base
from . import models, crud, config
from .auth import verify_jwt, get_current_user, require_role, get_db
import requests
import io
import json

# Init DB & App
Base.metadata.create_all(bind=engine)
app = FastAPI()
templates = Jinja2Templates(directory="frontend/templates")

# DB Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------
# AUTH ROUTES
# -------------------------
@app.get("/welcome")
def welcome(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})

@app.get("/login")
def login():
    params = {
        "response_type": "code",
        "client_id": config.CLIENT_ID,
        "redirect_uri": config.REDIRECT_URI,
        "scope": "openid profile email",
    }
    url = f"https://{config.AUTH0_DOMAIN}/authorize?" + urlencode(params)
    return RedirectResponse(url)

@app.get("/callback")
def callback(code: str):
    token_url = f"https://{config.AUTH0_DOMAIN}/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "code": code,
        "redirect_uri": config.REDIRECT_URI
    }
    headers = {"content-type": "application/x-www-form-urlencoded"}
    res = requests.post(token_url, data=data, headers=headers)
    tokens = res.json()

    if "id_token" not in tokens:
        return {"error": "Login gagal", "details": tokens}

    id_token = tokens["id_token"]

    payload = verify_jwt(id_token)
    sub = payload["sub"]
    email = payload.get("email") or f"{payload['sub']}@example.com"

    db = next(get_db())
    user = db.query(models.User).filter_by(auth0_sub=sub).first()
    if not user:
        user = models.User(auth0_sub=sub, email=email, role="doctor")  # default role
        db.add(user)
        db.commit()

    response = RedirectResponse(url="/")
    response.set_cookie("id_token", id_token, httponly=True)

    return response

@app.get("/logout")
def logout():
    params = {
        "client_id": config.CLIENT_ID,
        "returnTo": "http://localhost:8000/welcome"
    }
    url = f"https://{config.AUTH0_DOMAIN}/v2/logout?" + urlencode(params)
    response = RedirectResponse(url)
    response.delete_cookie("access_token")
    return response


# -------------------------
# PATIENT CRUD ROUTES
# -------------------------
@app.get("/")
def list_patients(request: Request, filter_tanggal: str = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(models.Patient)

    if filter_tanggal:
        try:
            tanggal = datetime.strptime(filter_tanggal, "%Y-%m-%d").date()
            query = query.filter(func.date(models.Patient.tanggal_kunjungan) == tanggal)
        except ValueError:
            pass  # tanggal invalid, ignore filter

    patients = query.all()

    total_pasien = db.query(models.Patient).count()
    pasien_hari_ini = db.query(models.Patient).filter(func.date(models.Patient.tanggal_kunjungan) == datetime.today().date()).count()

    return templates.TemplateResponse("list.html", {
        "request": request,
        "patients": patients,
        "user": user,
        "total_pasien": total_pasien,
        "pasien_hari_ini": pasien_hari_ini,
        "filter_tanggal": filter_tanggal
    })

@app.get("/add")
@require_role("doctor")
def add_form(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("add.html", {"request": request})

@app.post("/add")
@require_role("doctor")
def add_patient(nama: str = Form(...), tanggal_lahir: str = Form(...),
                tanggal_kunjungan: str = Form(...), diagnosis: str = Form(""),
                tindakan: str = Form(""), dokter: str = Form(""),
                db: Session = Depends(get_db), user=Depends(get_current_user)):
    crud.create_patient(db, {
        "nama": nama,
        "tanggal_lahir": tanggal_lahir,
        "tanggal_kunjungan": tanggal_kunjungan,
        "diagnosis": diagnosis,
        "tindakan": tindakan,
        "dokter": dokter
    })
    return RedirectResponse("/", status_code=303)

@app.get("/edit/{patient_id}")
@require_role("doctor")
def edit_form(patient_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    return templates.TemplateResponse("edit.html", {"request": request, "patient": patient})

@app.post("/edit/{patient_id}")
@require_role("doctor")
def update_patient(patient_id: int,
                   nama: str = Form(...), tanggal_lahir: str = Form(...),
                   tanggal_kunjungan: str = Form(...), diagnosis: str = Form(""),
                   tindakan: str = Form(""), dokter: str = Form(""),
                   db: Session = Depends(get_db), user=Depends(get_current_user)):
    crud.update_patient(db, patient_id, {
        "nama": nama,
        "tanggal_lahir": tanggal_lahir,
        "tanggal_kunjungan": tanggal_kunjungan,
        "diagnosis": diagnosis,
        "tindakan": tindakan,
        "dokter": dokter
    })
    return RedirectResponse("/", status_code=303)

@app.get("/delete/{patient_id}")
@require_role("doctor")
def delete_patient(patient_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    crud.delete_patient(db, patient_id)
    return RedirectResponse("/", status_code=303)

@app.get("/export")
def export_patients(db: Session = Depends(get_db)):
    patients = db.query(models.Patient).all()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Patients"
    ws.append(["Nama", "Tanggal Kunjungan", "Diagnosis", "Tindakan", "Dokter"])
    
    for p in patients:
        ws.append([p.nama, p.tanggal_kunjungan, p.diagnosis, p.tindakan, p.dokter])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=patients.xlsx"}
    )


@app.post("/import")
def import_patients(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type != "application/json":
        raise HTTPException(status_code=400, detail="Hanya file JSON yang diizinkan")
    
    data = json.load(file.file)  # baca JSON
    
    for item in data:
        crud.create_patient(db, {
            "nama": item.get("nama"),
            "tanggal_kunjungan": item.get("tanggal_kunjungan"),
            "diagnosis": item.get("diagnosis", ""),
            "tindakan": item.get("tindakan", ""),
            "dokter": item.get("dokter", "")
        })
    
    return {"status": "success", "count": len(data)}