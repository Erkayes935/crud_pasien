from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud.claim import get_claim
import requests
import os
from datetime import datetime, date

router = APIRouter()

@router.post("/claims/{claim_id}/generate_resume")
async def generate_claim_resume(  # ✅ UBAH NAMA FUNCTION untuk avoid conflict
    claim_id: int, 
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Generate resume medis dari claim ID (call core engine /resume_medis)"""
    try:
        print(f"📋 Resume request for claim {claim_id}")
        
        # Get claim data from database
        claim = get_claim(db, claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Extract parameters from frontend
        mode = payload.get("mode", "list")
        settings = payload.get("settings", {})
        
        # ✅ MAPPING SESUAI MODELS.PY
        resume_payload = {
            "pasien": {
                "nama": getattr(claim.patient, 'nama', '') if claim.patient else "-",
                "no_rm": getattr(claim.patient, 'no_rm', '') if claim.patient else "-",
                "umur": _calculate_age(getattr(claim.patient, 'tanggal_lahir', None)) if claim.patient else "-",
                "jk": getattr(claim.patient, 'jenis_kelamin', '') if claim.patient else "-",
                "keluhan": getattr(claim.medical_record, 'keluhan', '') if claim.medical_record else "-"
            },
            "visit": {
                "tgl_masuk": str(getattr(claim.visit, 'tanggal_kunjungan', '')) if claim.visit else "-",
                "tgl_keluar": "-",  # Tidak ada field discharge_date di models
                "ruangan": getattr(claim.visit, 'poli', '') if claim.visit else "-"
            },
            "diagnosis": {
                "utama": {
                    "nama": getattr(claim.medical_record, 'diagnosis_akhir', '') if claim.medical_record else "-",
                    "icd": "-"  # Tidak ada field ICD di medical_record
                },
                "sekunder": []  # Bisa diambil dari claim.diagnoses jika diperlukan
            },
            "tindakan": {
                "utama": {
                    "nama": getattr(claim.medical_record, 'tindakan', '') if claim.medical_record else "-",
                    "kode": "-"
                },
                "sekunder": []  # Bisa diambil dari claim.procedures jika diperlukan
            },
            "obat": _parse_obat(getattr(claim.medical_record, 'obat', '') if claim.medical_record else ""),
            "regulasi": [],  # Bisa diambil dari claim.regulation_details jika diperlukan
            "dokter": {
                "dpjp": getattr(claim.medical_record, 'doctor_name', '') if claim.medical_record else getattr(claim, 'doctor_name', '') or "-",
                "perawat": "-"
            },
            
            # ✅ VI-IX: REAL DATA dari database
            "riwayat_medis": {
                "alergi_obat": getattr(claim.medical_record, 'alergi', '') if claim.medical_record else "Tidak ada alergi yang diketahui",
                "riwayat_operasi": getattr(claim.medical_record, 'riwayat_operasi', '') if claim.medical_record else "Tidak ada riwayat operasi",
                "riwayat_penyakit": getattr(claim.medical_record, 'riwayat_penyakit', '') if claim.medical_record else "Tidak ada riwayat penyakit signifikan",
                "riwayat_pengobatan": getattr(claim.medical_record, 'riwayat_pengobatan', '') if claim.medical_record else "Tidak ada riwayat pengobatan khusus",
                "gejala_lain": getattr(claim.medical_record, 'gejala_lain', '') if claim.medical_record else "Tidak ada gejala tambahan"
            },
            "vital_signs": {
                "tekanan_darah": getattr(claim.medical_record, 'tekanan_darah', '') if claim.medical_record else "-",
                "nadi": getattr(claim.medical_record, 'nadi', '') if claim.medical_record else "-",
                "suhu": getattr(claim.medical_record, 'suhu', '') if claim.medical_record else "-",
                "pernapasan": getattr(claim.medical_record, 'pernapasan', '') if claim.medical_record else "-",
                "spo2": getattr(claim.medical_record, 'spo2', '') if claim.medical_record else "-",
                "berat_badan": getattr(claim.medical_record, 'berat_badan', '') if claim.medical_record else "-",
                "tinggi_badan": getattr(claim.medical_record, 'tinggi_badan', '') if claim.medical_record else "-"
            },
            "laboratorium": {
                "hemoglobin": getattr(claim.medical_record, 'hemoglobin', '') if claim.medical_record else "-",
                "leukosit": getattr(claim.medical_record, 'leukosit', '') if claim.medical_record else "-",
                "trombosit": getattr(claim.medical_record, 'trombosit', '') if claim.medical_record else "-",
                "gula_darah": getattr(claim.medical_record, 'gula_darah', '') if claim.medical_record else "-",
                "creatinin": getattr(claim.medical_record, 'creatinin', '') if claim.medical_record else "-"
            },
            "radiologi": {
                "rontgen_thorax": getattr(claim.medical_record, 'rontgen_thorax', '') if claim.medical_record else "-",
                "ct_scan": getattr(claim.medical_record, 'ct_scan', '') if claim.medical_record else "Tidak dilakukan",
                "usg": getattr(claim.medical_record, 'usg', '') if claim.medical_record else "Tidak dilakukan"
            },
            "evaluasi": {
                "diagnosis_awal": getattr(claim.medical_record, 'diagnosis_awal', '') if claim.medical_record else "-",
                "komorbid": getattr(claim.medical_record, 'komorbid', '') if claim.medical_record else "-",
                "komplikasi": getattr(claim.medical_record, 'komplikasi', '') if claim.medical_record else "-",
                "validasi_fornas": getattr(claim.medical_record, 'validasi_fornas', '') if claim.medical_record else "-",
                "notes_doctor": getattr(claim.medical_record, 'notes_doctor', '') if claim.medical_record else "-"
            },
            "idrg_detail": {
                # Data IDRG akan diambil dari claim atau proses terpisah
                "kode_idrg": "-",
                "deskripsi_idrg": "Belum ada mapping IDRG", 
                "severity_level": "-",
                "base_rate": "-",
                "cost_weight": "-",
                "tarif_klaim": "-"
            },
            
            "mode": mode,
            "settings": settings
        }
        
        print(f"🚀 Calling core engine /resume_medis with mode: {mode}")
        
        # ✅ CALL CORRECT ENDPOINT
        core_url = os.getenv("CORE_ENGINE_URL", "http://localhost:8002")
        response = requests.post(
            f"{core_url}/resume_medis",  # ✅ CORRECT ENDPOINT
            json=resume_payload,
            timeout=60
        )
        
        if response.status_code != 200:
            error_detail = f"Core engine error: {response.status_code} - {response.text}"
            print(f"❌ {error_detail}")
            raise HTTPException(status_code=500, detail=error_detail)
        
        result = response.json()
        print(f"✅ Resume generated successfully")
        
        return result
        
    except requests.RequestException as e:
        error_msg = f"Connection error to core engine: {str(e)}"
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=503, detail=error_msg)
    except Exception as e:
        error_msg = f"Resume generation failed: {str(e)}"
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

def _calculate_age(birth_date) -> str:
    """Calculate age from birth date"""
    if not birth_date:
        return "-"
    
    try:
        if isinstance(birth_date, str):
            birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        elif isinstance(birth_date, datetime):
            birth_date = birth_date.date()
        
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return str(age)
    except:
        return "-"

def _parse_obat(obat_text: str) -> list:
    """Parse obat text into list format"""
    if not obat_text or obat_text.strip() == "":
        return []
    
    # Simple parsing - bisa diperbaiki sesuai format obat di database
    obat_list = []
    for line in obat_text.split('\n'):
        line = line.strip()
        if line:
            if '(' in line and ')' in line:
                # Format: "Nama Obat (dosis)"
                nama = line.split('(')[0].strip()
                dosis = line.split('(')[1].split(')')[0].strip()
                obat_list.append({"nama": nama, "dosis": dosis})
            else:
                obat_list.append({"nama": line, "dosis": ""})
    
    return obat_list