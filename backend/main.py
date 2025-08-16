from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from . import models, crud

Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="frontend/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def list_patients(request: Request, db: Session = Depends(get_db)):
    patients = crud.get_patients(db)
    return templates.TemplateResponse("list.html", {"request": request, "patients": patients})

@app.post("/add")
def add_patient(nama: str = Form(...), tanggal_lahir: str = Form(...),
                tanggal_kunjungan: str = Form(...), diagnosis: str = Form(""),
                tindakan: str = Form(""), dokter: str = Form(""),
                db: Session = Depends(get_db)):
    crud.create_patient(db, {
        "nama": nama,
        "tanggal_lahir": tanggal_lahir,
        "tanggal_kunjungan": tanggal_kunjungan,
        "diagnosis": diagnosis,
        "tindakan": tindakan,
        "dokter": dokter
    })
    return RedirectResponse("/", status_code=303)

@app.get("/add")
def add_form(request: Request):
    return templates.TemplateResponse("add.html", {"request": request})

@app.get("/edit/{patient_id}")
def edit_form(patient_id: int, request: Request, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    return templates.TemplateResponse("edit.html", {"request": request, "patient": patient})

@app.post("/edit/{patient_id}")
def update_patient(patient_id: int,
                   nama: str = Form(...), tanggal_lahir: str = Form(...),
                   tanggal_kunjungan: str = Form(...), diagnosis: str = Form(""),
                   tindakan: str = Form(""), dokter: str = Form(""),
                   db: Session = Depends(get_db)):
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
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    crud.delete_patient(db, patient_id)
    return RedirectResponse("/", status_code=303)
