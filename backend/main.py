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
from . import models, config
from .crud import patient as patient_crud
from .crud import user as user_crud
from .crud import medical_record as mr_crud
from .crud import hospital as hospital_crud
from .crud import claim as claim_crud
from .crud import visit as visit_crud
from .database import SessionLocal, engine, Base
from .utils import auth_utils
from .utils.flash import flash, get_flashed_messages
from .utils.templates import templates
from .routers import dashboard_router, auth_router, patient_router, user_router, hospital_router, medical_record_router, claim_router, visit_router
from .auth import verify_jwt, get_db, require_roles_session, issue_csrf_token, require_csrf_dep
import requests, io, json, secrets, base64, hashlib, httpx, random

# Init DB & App
Base.metadata.create_all(bind=engine)

# Init FastAPI
app = FastAPI(title="AI-Claim")
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Init Middleware
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET, same_site="lax", https_only=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # untuk dev: izinkan semua
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init Routers
app.include_router(dashboard_router.router, tags=["dashboard"])
app.include_router(auth_router.router, tags=["auth"])
app.include_router(patient_router.router, tags=["patients"])
app.include_router(user_router.router, tags=["users"])
app.include_router(hospital_router.router, tags=["hospitals"])
app.include_router(medical_record_router.router, tags=["medical_records"])
app.include_router(visit_router.router, tags=["visits"])

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
        print(f"🆕 Buat ClaimSimulation untuk stage={stage}, id={sim.id}")

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
            print(f"➕ Tambah ClaimDiagnosis id={diag.id}, type={category}, text='{diag.diagnosis_text}'")

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
            print(f"   ↳ Tambah ClaimAIRecommendation id={rec.id} untuk diag_id={diag.id}")

            # 🔹 Seed regulasi dummy per diagnosis
            existing_regs = db.query(models.ClaimRegulationDetail).filter_by(
                claim_id=diag.claim_id,
                diagnosis_id=diag.id,
                is_deleted=False
            ).all()

            print(f"   🔍 Cek regulasi diagnosis_id={diag.id}, existing={len(existing_regs)}")

            if not existing_regs:
                reg = models.ClaimRegulationDetail(
                    claim_id=diag.claim_id,
                    diagnosis_id=diag.id,
                    procedure_id=None,
                    judul_regulasi="PNPK Sepsis 2020",
                    dasar_hukum="PNPK",
                    bab_pasal="Bab II Pasal 3",
                    isi="Diagnosis sepsis harus berdasarkan kriteria klinis",
                    is_deleted=False,
                    is_dummy=True,
                    created_at=datetime.utcnow()-timedelta(days=1),
                    updated_at=datetime.utcnow()
                )
                db.add(reg)
                print(f"   ✅ Regulasi dummy DIAGNOSIS disimpan untuk diag_id={diag.id}")
            else:
                print(f"   ℹ️ Regulasi diagnosis_id={diag.id} sudah ada")

    # 2️⃣ Regulasi dummy untuk Procedure
    procedures = db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).all()
    print(f"🔎 Jumlah procedure untuk claim_id={claim_id}: {len(procedures)}")
    for proc in procedures:
        print(f"   → Cek procedure_id={proc.id}, nama={proc.procedure_text}")
        existing_proc_regs = db.query(models.ClaimRegulationDetail).filter_by(
            claim_id=claim_id,
            procedure_id=proc.id,
            is_deleted=False
        ).all()
        print(f"      🔍 Existing regs for procedure_id={proc.id}: {len(existing_proc_regs)}")

        if not existing_proc_regs:
            reg = models.ClaimRegulationDetail(
                claim_id=claim_id,
                diagnosis_id=None,
                procedure_id=proc.id,
                judul_regulasi="PNPK Sepsis 2020",
                dasar_hukum="PNPK",
                bab_pasal="Bab II Pasal 3",
                isi=f"Regulasi terkait tindakan {proc.procedure_text}",
                is_deleted=False,
                is_dummy=True,
                created_at=datetime.utcnow()-timedelta(days=1),
                updated_at=datetime.utcnow()
            )
            db.add(reg)
            print(f"      ✅ Regulasi dummy PROCEDURE disimpan untuk proc_id={proc.id}")
        else:
            print(f"      ℹ️ Regulasi untuk procedure_id={proc.id} sudah ada")

    db.commit()
    print("💾 Commit selesai untuk claim_id:", claim_id, "stage:", stage)

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

        # 3️⃣ Baru hapus regulation
        db.query(models.ClaimRegulationDetail).filter_by(claim_id=claim_id).delete()

        # 4️⃣ Baru hapus ClaimProcedure
        db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).delete()


        # 5️⃣ Terakhir hapus diagnosis & simulation
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
        regs = db.query(models.ClaimRegulationDetail)\
        .filter_by(claim_id=claim_id, diagnosis_id=item_id, is_deleted=False)\
        .all()
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

@app.get("/claims/{claim_id}/regulations")
def get_regulations(
    claim_id: int,
    diagnosis_id: int = None,
    procedure_id: int = None,
    diagnosis_evaluation_id: int = None,
    procedure_evaluation_id: int = None,
    db: Session = Depends(get_db)
):
    print(f"📥 get_regulations dipanggil! claim_id={claim_id}, "
          f"diagnosis_id={diagnosis_id}, procedure_id={procedure_id}, "
          f"diagnosis_eval_id={diagnosis_evaluation_id}, "
          f"procedure_eval_id={procedure_evaluation_id}")

    query = db.query(models.ClaimRegulationDetail).filter_by(
        claim_id=claim_id,
        is_deleted=False
    )

    if diagnosis_id:
        query = query.filter(models.ClaimRegulationDetail.diagnosis_id == diagnosis_id)
    elif procedure_id:
        query = query.filter(models.ClaimRegulationDetail.procedure_id == procedure_id)
    elif diagnosis_evaluation_id:
        query = query.filter(models.ClaimRegulationDetail.diagnosis_evaluation_id == diagnosis_evaluation_id)
    elif procedure_evaluation_id:
        query = query.filter(models.ClaimRegulationDetail.procedure_evaluation_id == procedure_evaluation_id)

    regs = query.all()
    print(f"🔎 Jumlah hasil regulasi: {len(regs)}")

    return {
        "status": "ok",
        "data": [
            {
                "id": r.id,
                "judul_regulasi": r.judul_regulasi,
                "dasar_hukum": r.dasar_hukum,
                "bab_pasal": r.bab_pasal,
                "isi": r.isi
            }
            for r in regs
        ]
    }


# -------------------------
# --- AI Evaluations ---
def store_ai_evaluations(db: Session, claim_id: int, evaluasi: dict):
    """Simpan hasil evaluasi kombinasi ke tabel sesuai model"""
    db.query(models.ClaimRegulationDetail).filter_by(claim_id=claim_id).delete()
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
    db.flush()

    if diag_eval:
        reg = models.ClaimRegulationDetail(
            claim_id=claim_id,
            diagnosis_evaluation_id=diag_eval.id,
            judul_regulasi="PNPK Evaluasi Diagnosis 2020",
            dasar_hukum="PNPK",
            bab_pasal="Bab IV Pasal 8",
            isi="Evaluasi kombinasi diagnosis harus berdasarkan kriteria klinis",
            is_dummy=True,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    db.add(reg)

    # === Kombinasi Tindakan ===
    for td in evaluasi.get("kombinasi_tindakan", []):
        proc_eval = models.ClaimProcedureEvaluation(
            claim_id=claim_id,
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
        db.flush()

    for proc_eval in db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=claim_id).all():
        reg = models.ClaimRegulationDetail(
            claim_id=claim_id,
            procedure_evaluation_id=proc_eval.id,
            judul_regulasi="PNPK Evaluasi Tindakan 2020",
            dasar_hukum="PNPK",
            bab_pasal="Bab V Pasal 12",
            isi=f"Evaluasi regulasi terkait tindakan {proc_eval.status_tindakan or '-'}",
            is_dummy=True,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(reg)
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
            is_dummy=True,
            is_deleted=False,
            created_at=datetime.utcnow(),
        )
        db.add(comb)

    db.commit()
# end evaluasi AI untuk Klaim

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
        # === Kombinasi Diagnosis ===
        diag_id = summ_data.get("kombinasi_diagnosis", {}).get("diagnosis_id")
        if not diag_id:
            diag_name = summ_data.get("kombinasi_diagnosis", {}).get("name") \
                        or summ_data.get("kombinasi_diagnosis", {}).get("diagnosis_text")
            if diag_name:
                diag_row = db.query(models.ClaimDiagnosis).filter_by(
                    claim_id=claim_id, diagnosis_text=diag_name
                ).first()
                diag_id = diag_row.id if diag_row else None
                if not diag_id:
                    print(f"[WARN] Evaluasi diagnosis '{diag_name}' tidak ditemukan untuk claim_id={claim_id}")

        diag_eval = models.ClaimDiagnosisEvaluation(
            claim_id=claim_id,
            diagnosis_id=diag_id,
            validitas=summ_data.get("kombinasi_diagnosis", {}).get("validitas"),
            severity=summ_data.get("kombinasi_diagnosis", {}).get("severity"),
            validitas_detail=summ_data.get("kombinasi_diagnosis", {}).get("validitas_detail"),
            kode_ina_cbg=summ_data.get("kombinasi_diagnosis", {}).get("kode_ina_cbg"),
            estimasi_tarif=parse_number(summ_data.get("kombinasi_diagnosis", {}).get("estimasi_tarif")),
            syarat_klinis=summ_data.get("kombinasi_diagnosis", {}).get("syarat_klinis"),
            evaluasi_faskes=summ_data.get("kombinasi_diagnosis", {}).get("evaluasi_faskes"),
            rawat_inap=summ_data.get("kombinasi_diagnosis", {}).get("rawat_inap"),
            created_at=datetime.utcnow() - timedelta(days=1),
            is_deleted=False,
            is_dummy=True
        )
        db.add(diag_eval)

        # === Kombinasi Tindakan ===
        for v in summ_data.get("procedure", []):
            proc_id = v.get("procedure_id")
            if not proc_id:
                proc_name = v.get("tindakan") or v.get("name") or v.get("procedure_text")
                if proc_name:
                    proc = db.query(models.ClaimProcedure).filter_by(
                        claim_id=claim_id, procedure_text=proc_name
                    ).first()
                    proc_id = proc.id if proc else None
                    if not proc_id:
                        print(f"[WARN] Evaluasi procedure '{proc_name}' tidak ditemukan untuk claim_id={claim_id}")

            proc_eval = models.ClaimProcedureEvaluation(
                claim_id=claim_id,
                procedure_id=proc_id,
                validitas=v.get("validitas"),
                validitas_detail=v.get("validitas_detail"),
                status_tindakan=v.get("status_tindakan"),
                tarif_impact=parse_number(v.get("tarif_impact")),
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
            "id": diag.id if diag else "-",
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
                "id": p.id,
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

# ------------------------
# Claim AI Simulations (Handling BE untuk Role Verifikator)
# ------------------------

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

# END Claim AI Recommendations and Simulations

# Update Status Klaim Draft
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
# end update claim draft

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
    csrf_token: str = Form(...),
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

# 🔹 CRUD klaim
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
        "claim_left.html",
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

def load_sim_and_summary(db: Session, claim_id: int, include_summary: bool = True):
    """Ambil ulang simulasi + evaluasi dari tabel pecahan"""
    sim: dict = {}
    summ: dict = {}

    # === ClaimSimulation ===
    sims = db.query(models.ClaimSimulation).filter_by(claim_id=claim_id).all()
    for s in sims:
        if s.stage not in sim:
            sim[s.stage] = {
                "utama_diagnosis": None,
                "utama_tindakan": None,
                "sekunder_diagnosis": [],
                "sekunder_tindakan": []
            }
        if s.diagnosis_utama_id:
            sim[s.stage]["utama_diagnosis"] = {"id": s.diagnosis_utama_id, "type": "diagnosis"}
        if s.tindakan_utama_id:
            sim[s.stage]["utama_tindakan"] = {"id": s.tindakan_utama_id, "type": "tindakan"}
        if s.diagnosis_sekunder_id:
            sim[s.stage]["sekunder_diagnosis"].append({"id": s.diagnosis_sekunder_id, "type": "diagnosis"})
        if s.tindakan_sekunder_id:
            sim[s.stage]["sekunder_tindakan"].append({"id": s.tindakan_sekunder_id, "type": "tindakan"})

    # === Evaluasi (opsional) ===
    if include_summary:
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
            for d in db.query(models.ClaimDiagnosisEvaluation).filter_by(claim_id=claim_id).all()
        ]
        summ["procedure"] = [
            {
                "validitas": p.validitas,
                "status_tindakan": p.status_tindakan,
                "tarif_impact": float(p.tarif_impact) if p.tarif_impact else None,
                "faskes": p.faskes,
                "rawat_inap": p.rawat_inap,
                "syarat_klinis": p.syarat_klinis,
            }
            for p in db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=claim_id).all()
        ]
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
            }
            for a in db.query(models.ClaimCombinationAlternative).filter_by(claim_id=claim_id).all()
        ]

    return sim, summ


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

    # === Load sim & summary sesuai role ===
    is_doctor = (isinstance(user.role, str) and user.role == "doctor") or \
                (isinstance(user.role, (list, tuple)) and "doctor" in user.role)

    include_summary = not is_doctor  # doctor tidak boleh lihat summary
    sim, summ = load_sim_and_summary(db, id, include_summary=include_summary)

    # === Pilih template sesuai role ===
    template_name = "claim_left.html" if is_doctor else "claim_right.html"

    # === Siapkan fields form ===
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

    return templates.TemplateResponse(template_name, {
        "request": request,
        "mode": "edit",
        "record": claim,
        "csrf_token": csrf_token,
        "current_user": user,
        "user": user,
        "role": user.role if isinstance(user.role, str) else user.role[0],
        "isDoctor": is_doctor,
        "isVerifikator": (user.role == "verifikator") if isinstance(user.role, str) else ("verifikator" in user.role),
        "fields": fields,
        "sim": sim,      # dokter & verifikator sama-sama dapat sim
        "summ": summ,    # summ kosong untuk doctor
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

# END CRUD KLAIM Routes

# -------------------------
# VISIT ROUTES
# -------------------------


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