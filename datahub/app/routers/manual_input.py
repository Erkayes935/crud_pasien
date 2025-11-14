"""
Router for Enhanced Manual Input
=================================
Support for Patient, Visit, and Medical Record input with anonymization.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Dict
import uuid as uuid_lib
from datetime import datetime, date

from ..db import get_session
from ..models.core import Patient, Visit, MedicalRecord, PatientUUIDMap
from ..services.anonymizer import Anonymizer
from ..services.logger import log_event
from ..services.manual_duplicate_detector import ManualDuplicateDetector

router = APIRouter(prefix="/manual", tags=["Manual Input"])
templates = Jinja2Templates(directory="app/templates")


# =====================================================================
# SCHEMAS (Pydantic Models)
# =====================================================================

from pydantic import BaseModel, Field
from typing import Optional

class PatientCreateRequest(BaseModel):
    """Request untuk create patient."""
    hospital_id: str = Field(..., description="ID Rumah Sakit")
    
    # PHI fields (akan di-anonymize)
    nama: str = Field(..., description="Nama Pasien")
    no_ktp: Optional[str] = Field(None, description="NIK/KTP")
    no_hp: Optional[str] = Field(None, description="No HP")
    
    # Safe fields
    tanggal_lahir: Optional[str] = Field(None, description="YYYY-MM-DD")
    jenis_kelamin: Optional[str] = Field(None, description="L/P")
    alamat: Optional[str] = Field(None, description="Alamat Lengkap")
    email: Optional[str] = Field(None, description="Email")
    
    # Optional
    no_rm: Optional[str] = Field(None, description="No Rekam Medis")
    no_bpjs: Optional[str] = Field(None, description="No BPJS")
    eksternal_id: Optional[str] = Field(None, description="ID Eksternal")


class VisitCreateRequest(BaseModel):
    """Request untuk create visit."""
    patient_id: Optional[int] = Field(None, description="Patient ID (jika sudah ada)")
    patient_uuid: Optional[str] = Field(None, description="Patient UUID (jika sudah ada)")
    hospital_id: str = Field(..., description="ID Rumah Sakit")
    
    # Visit info
    tanggal_kunjungan: str = Field(..., description="YYYY-MM-DD")
    jenis_kunjungan: Optional[str] = Field("Rawat Inap", description="Rawat Inap/Jalan")
    jenis_rawat: Optional[str] = Field("Rawat Inap", description="Jenis Rawat")
    lama_rawat: Optional[int] = Field(1, description="Lama Rawat (hari)")
    
    # Clinical
    poli: Optional[str] = Field(None, description="Poliklinik")
    gejala: Optional[str] = Field(None, description="Keluhan/Gejala")
    riwayat: Optional[str] = Field(None, description="Riwayat Penyakit")
    
    # Doctor (akan di-mask)
    doctor_name: Optional[str] = Field(None, description="Nama Dokter")
    
    # Optional
    episode_id: Optional[str] = Field(None, description="Episode ID")
    visit_no: Optional[int] = Field(1, description="Kunjungan ke-")


class MedicalRecordCreateRequest(BaseModel):
    """Request untuk create medical record."""
    visit_id: Optional[int] = Field(None, description="Visit ID")
    patient_id: Optional[int] = Field(None, description="Patient ID")
    hospital_id: str = Field(..., description="ID Rumah Sakit")
    
    # Record info
    record_type: str = Field(..., description="admission/daily/discharge")
    notes_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    
    # Doctor (akan di-mask)
    doctor_name: str = Field(..., description="Nama Dokter")
    
    # Riwayat
    keluhan: Optional[str] = None
    riwayat_penyakit: Optional[str] = None
    riwayat_pengobatan: Optional[str] = None
    riwayat_operasi: Optional[str] = None
    alergi: Optional[str] = None
    gejala_lain: Optional[str] = None
    
    # Pemeriksaan Fisik
    tekanan_darah: Optional[str] = None
    nadi: Optional[str] = None
    pernapasan: Optional[str] = None
    suhu: Optional[str] = None
    spo2: Optional[str] = None
    berat_badan: Optional[str] = None
    tinggi_badan: Optional[str] = None
    
    # Lab
    hemoglobin: Optional[str] = None
    leukosit: Optional[str] = None
    trombosit: Optional[str] = None
    gula_darah: Optional[str] = None
    creatinin: Optional[str] = None
    rontgen_thorax: Optional[str] = None
    ct_scan: Optional[str] = None
    usg: Optional[str] = None
    
    # Diagnosis & Tindakan
    diagnosis_awal: Optional[str] = None
    diagnosis: Optional[str] = None
    komorbid: Optional[str] = None
    komplikasi: Optional[str] = None
    diagnosis_akhir: Optional[str] = None
    tindakan: Optional[str] = None
    
    # Obat
    obat: Optional[str] = None
    validasi_fornas: Optional[str] = None
    notes_doctor: Optional[str] = None


# =====================================================================
# UI ENDPOINT
# =====================================================================

@router.get("/", response_class=HTMLResponse)
async def manual_input_page(request: Request):
    """
    Render halaman manual input dengan tab system.
    """
    return templates.TemplateResponse("manual_input.html", {
        "request": request,
        "page_title": "Manual Input - AI CLAIM Data Hub"
    })


# =====================================================================
# API ENDPOINTS
# =====================================================================

@router.post("/patient")
def create_patient(
    data: PatientCreateRequest,
    db: Session = Depends(get_session)
):
    """
    Create patient baru dengan anonymization dan duplicate detection.
    
    Process:
    1. Validate input
    2. Generate/get patient_uuid (dengan hash dari data ASLI)
    3. **PHASE 1: Check patient duplicate by patient_uuid**
    4. Anonymize PHI fields (mask nama, NIK, no HP)
    5. Save to database
    """
    try:
        # Prepare data dict untuk anonymizer
        patient_data = data.dict()
        
        # Anonymize
        anonymizer = Anonymizer(db)
        anonymized = anonymizer.anonymize_record(
            data=patient_data,
            source_type="manual",
            source_record_id=None
        )
        
        # PHASE 1: Check patient duplicate
        duplicate_detector = ManualDuplicateDetector(db)
        existing_patient = duplicate_detector.check_patient_duplicate(
            patient_uuid=anonymized["patient_uuid"],
            hospital_id=anonymized["hospital_id"]
        )
        
        if existing_patient:
            # Patient sudah ada, return existing patient
            return {
                "status": "duplicate",
                "message": "⚠️ Patient sudah ada (duplicate detected)",
                "duplicate_type": "patient",
                "data": {
                    "id": existing_patient.id,
                    "patient_uuid": existing_patient.patient_uuid,
                    "nama": existing_patient.nama,
                    "hospital_id": existing_patient.hospital_id,
                    "created_at": str(existing_patient.created_at)
                }
            }
        
        # Parse tanggal lahir
        tanggal_lahir_date = None
        if anonymized.get("tanggal_lahir"):
            try:
                tanggal_lahir_date = datetime.strptime(
                    anonymized["tanggal_lahir"], "%Y-%m-%d"
                ).date()
            except:
                pass
        
        # Create patient record
        patient = Patient(
            uuid=uuid_lib.uuid4(),
            patient_uuid=anonymized["patient_uuid"],
            hospital_id=anonymized["hospital_id"],
            
            # Anonymized fields
            nama=anonymized.get("nama"),
            no_ktp=anonymized.get("no_ktp"),
            no_hp=anonymized.get("no_hp"),
            
            # Original fields (tidak diubah)
            tanggal_lahir=tanggal_lahir_date,
            jenis_kelamin=anonymized.get("jenis_kelamin"),
            alamat=anonymized.get("alamat"),
            email=anonymized.get("email"),
            
            # Optional
            no_rm=anonymized.get("no_rm"),
            no_bpjs=anonymized.get("no_bpjs"),
            eksternal_id=anonymized.get("eksternal_id"),
            
            # Metadata
            source_type="manual",
            is_deleted=False,
            is_dummy=False
        )
        
        db.add(patient)
        db.commit()
        db.refresh(patient)
        
        log_event(db, str(patient.id), "manual_patient", "info", f"Patient created: {patient.nama}")
        
        return {
            "status": "success",
            "message": "✅ Patient berhasil ditambahkan",
            "data": {
                "id": patient.id,
                "patient_uuid": patient.patient_uuid,
                "nama": patient.nama,  # Already masked
                "hospital_id": patient.hospital_id
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create patient: {str(e)}")


@router.post("/visit")
def create_visit(
    data: VisitCreateRequest,
    db: Session = Depends(get_session)
):
    """
    Create visit baru dengan duplicate detection.
    
    Requirements:
    - Patient harus sudah ada (by patient_id atau patient_uuid)
    
    Process:
    1. Find patient
    2. **PHASE 2: Check visit duplicate by patient + date + type**
    3. Create visit if not duplicate
    """
    try:
        # Find patient
        patient = None
        if data.patient_id:
            patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
        elif data.patient_uuid:
            patient = db.query(Patient).filter(Patient.patient_uuid == data.patient_uuid).first()
        
        if not patient:
            raise HTTPException(
                status_code=404,
                detail="Patient not found. Please create patient first or provide valid patient_id/patient_uuid."
            )
        
        # Anonymize doctor name
        anonymizer = Anonymizer(db)
        doctor_name_masked = None
        if data.doctor_name:
            doctor_name_masked = anonymizer._mask_name(data.doctor_name)
        
        # Parse tanggal kunjungan
        tanggal_kunjungan_date = datetime.strptime(
            data.tanggal_kunjungan, "%Y-%m-%d"
        ).date()
        
        # PHASE 2: Check visit duplicate
        duplicate_detector = ManualDuplicateDetector(db)
        existing_visit = duplicate_detector.check_visit_duplicate(
            patient_id=patient.id,
            tanggal_kunjungan=tanggal_kunjungan_date,
            jenis_rawat=data.jenis_rawat
        )
        
        if existing_visit:
            # Visit sudah ada, return existing visit
            return {
                "status": "duplicate",
                "message": "⚠️ Visit sudah ada (duplicate detected)",
                "duplicate_type": "visit",
                "data": {
                    "id": existing_visit.id,
                    "visit_uuid": existing_visit.visit_uuid,
                    "patient_uuid": patient.patient_uuid,
                    "tanggal_kunjungan": str(existing_visit.tanggal_kunjungan),
                    "jenis_rawat": existing_visit.jenis_rawat,
                    "created_at": str(existing_visit.created_at)
                }
            }
        
        # Create visit record
        visit = Visit(
            uuid=uuid_lib.uuid4(),
            visit_uuid=str(uuid_lib.uuid4()),
            patient_id=patient.id,
            hospital_id=data.hospital_id,
            
            # Visit info
            tanggal_kunjungan=tanggal_kunjungan_date,
            jenis_kunjungan=data.jenis_kunjungan,
            jenis_rawat=data.jenis_rawat,
            lama_rawat=data.lama_rawat,
            
            # Clinical
            poli=data.poli,
            gejala=data.gejala,
            riwayat=data.riwayat,
            
            # Doctor (masked)
            doctor_name=doctor_name_masked,
            
            # Optional
            episode_id=data.episode_id,
            visit_no=data.visit_no,
            
            # Metadata
            source_type="manual",
            is_deleted=False,
            is_dummy=False
        )
        
        db.add(visit)
        db.commit()
        db.refresh(visit)
        
        log_event(db, str(visit.id), "manual_visit", "info", f"Visit created for patient {patient.nama}")
        
        return {
            "status": "success",
            "message": "✅ Visit berhasil ditambahkan",
            "data": {
                "id": visit.id,
                "visit_uuid": visit.visit_uuid,
                "patient_uuid": patient.patient_uuid,
                "tanggal_kunjungan": str(visit.tanggal_kunjungan)
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create visit: {str(e)}")


@router.post("/medical_record")
def create_medical_record(
    data: MedicalRecordCreateRequest,
    db: Session = Depends(get_session)
):
    """
    Create medical record baru dengan duplicate detection.
    
    Requirements:
    - Visit harus sudah ada (by visit_id)
    
    Process:
    1. Find visit
    2. **PHASE 3: Check medical record duplicate by visit + type + date + all fields**
    3. Create record if not duplicate
    """
    try:
        # Find visit
        visit = None
        if data.visit_id:
            visit = db.query(Visit).filter(Visit.id == data.visit_id).first()
        
        if not visit:
            raise HTTPException(
                status_code=404,
                detail="Visit not found. Please create visit first or provide valid visit_id."
            )
        
        # Anonymize doctor name
        anonymizer = Anonymizer(db)
        doctor_name_masked = anonymizer._mask_name(data.doctor_name)
        
        # Parse notes date
        notes_date_parsed = date.today()
        if data.notes_date:
            try:
                notes_date_parsed = datetime.strptime(data.notes_date, "%Y-%m-%d").date()
            except:
                pass
        
        # Prepare record data untuk duplicate check
        record_data = {
            'doctor_name': doctor_name_masked,
            'keluhan': data.keluhan,
            'riwayat_penyakit': data.riwayat_penyakit,
            'riwayat_pengobatan': data.riwayat_pengobatan,
            'riwayat_operasi': data.riwayat_operasi,
            'alergi': data.alergi,
            'gejala_lain': data.gejala_lain,
            'tekanan_darah': data.tekanan_darah,
            'nadi': data.nadi,
            'pernapasan': data.pernapasan,
            'suhu': data.suhu,
            'spo2': data.spo2,
            'berat_badan': data.berat_badan,
            'tinggi_badan': data.tinggi_badan,
            'hemoglobin': data.hemoglobin,
            'leukosit': data.leukosit,
            'trombosit': data.trombosit,
            'gula_darah': data.gula_darah,
            'creatinin': data.creatinin,
            'rontgen_thorax': data.rontgen_thorax,
            'ct_scan': data.ct_scan,
            'usg': data.usg,
            'diagnosis_awal': data.diagnosis_awal,
            'diagnosis': data.diagnosis,
            'komorbid': data.komorbid,
            'komplikasi': data.komplikasi,
            'diagnosis_akhir': data.diagnosis_akhir,
            'tindakan': data.tindakan,
            'obat': data.obat,
            'validasi_fornas': data.validasi_fornas,
            'notes_doctor': data.notes_doctor
        }
        
        # PHASE 3: Check medical record duplicate
        duplicate_detector = ManualDuplicateDetector(db)
        existing_record, is_exact_duplicate = duplicate_detector.check_medical_record_duplicate(
            visit_id=visit.id,
            record_type=data.record_type,
            notes_date=notes_date_parsed,
            record_data=record_data
        )
        
        if existing_record and is_exact_duplicate:
            # Medical record sudah ada dan SEMUA field sama persis
            return {
                "status": "duplicate",
                "message": "⚠️ Medical Record sudah ada dengan data yang sama persis (exact duplicate)",
                "duplicate_type": "medical_record_exact",
                "data": {
                    "id": existing_record.id,
                    "record_uuid": existing_record.record_uuid,
                    "visit_uuid": visit.visit_uuid,
                    "record_type": existing_record.record_type,
                    "notes_date": str(existing_record.notes_date),
                    "created_at": str(existing_record.created_at)
                }
            }
        elif existing_record and not is_exact_duplicate:
            # Ada record dengan visit+type+date sama tapi field berbeda
            # Log warning tapi tetap create (bukan duplicate)
            log_event(
                db,
                str(visit.id),
                "manual_medical_record",
                "warning",
                f"Medical record with same visit+type+date exists but fields differ. Creating new record."
            )
        
        # Create medical record
        record = MedicalRecord(
            uuid=uuid_lib.uuid4(),
            record_uuid=str(uuid_lib.uuid4()),
            patient_id=visit.patient_id,
            visit_id=visit.id,
            hospital_id=data.hospital_id,
            
            # Record info
            record_type=data.record_type,
            notes_date=notes_date_parsed,
            is_final=False,
            
            # Doctor (masked)
            doctor_name=doctor_name_masked,
            
            # Riwayat
            keluhan=data.keluhan,
            riwayat_penyakit=data.riwayat_penyakit,
            riwayat_pengobatan=data.riwayat_pengobatan,
            riwayat_operasi=data.riwayat_operasi,
            alergi=data.alergi,
            gejala_lain=data.gejala_lain,
            
            # Pemeriksaan Fisik
            tekanan_darah=data.tekanan_darah,
            nadi=data.nadi,
            pernapasan=data.pernapasan,
            suhu=data.suhu,
            spo2=data.spo2,
            berat_badan=data.berat_badan,
            tinggi_badan=data.tinggi_badan,
            
            # Lab
            hemoglobin=data.hemoglobin,
            leukosit=data.leukosit,
            trombosit=data.trombosit,
            gula_darah=data.gula_darah,
            creatinin=data.creatinin,
            rontgen_thorax=data.rontgen_thorax,
            ct_scan=data.ct_scan,
            usg=data.usg,
            
            # Diagnosis & Tindakan
            diagnosis_awal=data.diagnosis_awal,
            diagnosis=data.diagnosis,
            komorbid=data.komorbid,
            komplikasi=data.komplikasi,
            diagnosis_akhir=data.diagnosis_akhir,
            tindakan=data.tindakan,
            
            # Obat
            obat=data.obat,
            validasi_fornas=data.validasi_fornas,
            notes_doctor=data.notes_doctor,
            
            # Metadata
            source_type="manual",
            status="ready_for_ai",
            is_deleted=False,
            is_dummy=False
        )
        
        db.add(record)
        db.commit()
        db.refresh(record)
        
        log_event(db, str(record.id), "manual_medical_record", "info", f"Medical record created for visit {visit.visit_uuid}")
        
        return {
            "status": "success",
            "message": "✅ Medical Record berhasil ditambahkan",
            "data": {
                "id": record.id,
                "record_uuid": record.record_uuid,
                "visit_uuid": visit.visit_uuid,
                "record_type": record.record_type
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create medical record: {str(e)}")


# =====================================================================
# HELPER ENDPOINTS
# =====================================================================

@router.get("/patients")
def list_patients(
    limit: int = 100,
    hospital_id: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """List patients untuk dropdown selection."""
    query = db.query(Patient).filter(Patient.is_deleted == False)
    
    if hospital_id:
        query = query.filter(Patient.hospital_id == hospital_id)
    
    patients = query.order_by(Patient.created_at.desc()).limit(limit).all()
    
    return {
        "status": "success",
        "data": [
            {
                "id": p.id,
                "patient_uuid": p.patient_uuid,
                "nama": p.nama,  # Already masked
                "hospital_id": p.hospital_id
            }
            for p in patients
        ]
    }


@router.get("/visits")
def list_visits(
    patient_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_session)
):
    """List visits untuk dropdown selection dengan informasi pasien."""
    query = db.query(Visit).filter(Visit.is_deleted == False)
    
    if patient_id:
        query = query.filter(Visit.patient_id == patient_id)
    
    visits = query.order_by(Visit.created_at.desc()).limit(limit).all()
    
    return {
        "status": "success",
        "data": [
            {
                "id": v.id,
                "visit_uuid": v.visit_uuid,
                "patient_id": v.patient_id,
                "patient_name": v.patient.nama if v.patient else "Unknown",
                "patient_uuid": v.patient.patient_uuid if v.patient else None,
                "tanggal_kunjungan": str(v.tanggal_kunjungan),
                "jenis_rawat": v.jenis_rawat
            }
            for v in visits
        ]
    }


@router.get("/duplicate_stats")
def get_duplicate_statistics(
    db: Session = Depends(get_session)
):
    """
    Get statistik duplicate detection untuk manual input.
    """
    try:
        duplicate_detector = ManualDuplicateDetector(db)
        stats = duplicate_detector.get_duplicate_summary()
        
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get duplicate stats: {str(e)}")


@router.get("/current_user")
def get_current_user(
    request: Request,
    db: Session = Depends(get_session)
):
    """
    Get current logged-in user info (hospital_id, name, etc.)
    
    TODO: Integrate with actual authentication system
    For now, return mock data or from session
    """
    # Option 1: From session/cookie (if you have auth)
    # user_id = request.session.get('user_id')
    # user = db.query(User).filter(User.id == user_id).first()
    
    # Option 2: From JWT token
    # token = request.headers.get('Authorization')
    # user = decode_token(token)
    
    # Option 3: Mock data for now (REPLACE THIS!)
    return {
        "status": "success",
        "data": {
            "hospital_id": "RS001",  # TODO: Get from actual user session
            "name": "Admin RS",
            "role": "admin_rs"
        }
    }