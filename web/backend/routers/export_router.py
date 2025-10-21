from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Claim, Patient, Visit, MedicalRecord, ClaimDiagnosis, ClaimProcedure
from backend.auth import require_roles_session
from pydantic import BaseModel
import os
from datetime import datetime
import json

router = APIRouter(prefix="/api/export", tags=["export"])

class ExportTxtRequest(BaseModel):
    sep_number: str

@router.post("/claims/{claim_id}/txt")
async def export_claim_txt(
    claim_id: int,
    request: ExportTxtRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator"))
):
    """Export claim to TXT format for BPJS e-Claim"""
    
    # Get claim data
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Simple TXT generator for testing
    sep_number = request.sep_number.strip()
    if not sep_number:
        raise HTTPException(status_code=400, detail="SEP number required")
    
    # Generate 12 lines BPJS format sesuai request atasan
    lines = []
    
    # Line 1: Header - format sesuai request atasan
    hospital_name = claim.hospital.nama if claim.hospital else "RS HAJI SURABAYA"
    lines.append(f"1|KLAIM|{sep_number}|{hospital_name}|BPJS")
    
    # Line 2: Patient info - format sesuai request atasan  
    patient_name = claim.patient.nama if claim.patient else "PASIEN_UNKNOWN"
    patient_gender = claim.patient.jenis_kelamin if claim.patient and claim.patient.jenis_kelamin else "L"
    patient_birth = claim.patient.tanggal_lahir.strftime("%Y-%m-%d") if claim.patient and claim.patient.tanggal_lahir else "1990-01-01"
    patient_address = claim.patient.alamat if claim.patient and claim.patient.alamat else "Alamat tidak diketahui"
    bpjs_number = claim.patient.no_bpjs if claim.patient and claim.patient.no_bpjs else "000000000000"
    lines.append(f"2|{patient_name}|{patient_gender}|{patient_birth}|{patient_address}|{bpjs_number}")
    
    # Line 3: Service info - format sesuai request atasan
    today = datetime.now().strftime("%Y-%m-%d")
    lines.append(f"3|{today}|{today}|Rawat Inap|Penyakit Dalam")
    
    # Line 4-5: Diagnosis (real data from claim) - try multiple diagnosis types
    primary_diag = db.query(ClaimDiagnosis).filter(
        ClaimDiagnosis.claim_id == claim_id,
        ClaimDiagnosis.diagnosis_type.in_(["Primary", "utama", "Diagnosis Utama"]),
        ClaimDiagnosis.is_deleted == False
    ).first()
    
    secondary_diag = db.query(ClaimDiagnosis).filter(
        ClaimDiagnosis.claim_id == claim_id,
        ClaimDiagnosis.diagnosis_type.in_(["Secondary", "sekunder"]),
        ClaimDiagnosis.is_deleted == False
    ).first()
    
    # Line 4: Primary diagnosis (format sesuai request atasan)
    if primary_diag:
        main_icd = primary_diag.icd10_code or "J18.9"  # Pneumonia default ICD
        main_icd_name = primary_diag.diagnosis_text or "Diagnosis Tidak Diketahui"
        lines.append(f"4|{main_icd}|{main_icd_name}|Primer")
    else:
        lines.append(f"4|Z000|Tidak Ada Diagnosis Utama|Primer")
    
    # Line 5: Secondary diagnosis (format sesuai request atasan)
    if secondary_diag:
        sec_icd = secondary_diag.icd10_code or "E14.9"  # Diabetes default ICD
        sec_icd_name = secondary_diag.diagnosis_text or "Diagnosis Sekunder"
        lines.append(f"5|{sec_icd}|{sec_icd_name}|Sekunder")
    else:
        lines.append(f"5|||")
    
    # Line 6-7: Procedures - format sesuai request atasan
    procedures = db.query(ClaimProcedure).filter(
        ClaimProcedure.claim_id == claim_id,
        ClaimProcedure.is_deleted == False
    ).limit(2).all()
    
    # Line 6: Primary procedure
    if procedures and len(procedures) > 0:
        proc_code = "88.72"  # X-ray thorax code
        proc_name = procedures[0].procedure_text or "Tindakan Tidak Diketahui"
        lines.append(f"6|{proc_code}|{proc_name}|ICD-9-CM")
    else:
        lines.append(f"6|||ICD-9-CM")
        
    # Line 7: Doctor info - format sesuai request atasan
    doctor_code = "001"
    doctor_name = claim.doctor_name if claim.doctor_name else "Dr. Unknown"
    lines.append(f"7|{doctor_code}|{doctor_name}|DPJP")
    
    # Line 8-12: Format sesuai request atasan
    tarif_bpjs = "15000000"
    ina_cbg = "G-4-12-I"
    service_type = "Rawat Inap" 
    room_class = "3"
    
    lines.append(f"8|{tarif_bpjs}|{ina_cbg}|{service_type}|Kelas {room_class}")
    lines.append(f"9|{sep_number}|V-Claim|Valid")
    lines.append(f"10|Resume medis pneumonia|Terapi antibiotik|Membaik")
    
    # Line 11: Files (jika ada)
    file_names = "Hasil Lab, X-ray Thorax, Resume"
    lines.append(f"11|{file_names}")
    
    # Line 12: End
    final_date = datetime.now().strftime("%Y-%m-%d")
    lines.append(f"12|END OF CLAIM|{final_date}")
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"CLAIM_{claim_id}_{sep_number}_{timestamp}.txt"
    
    # Create export directory if not exists
    export_dir = "/tmp/exports"  # For Docker container
    os.makedirs(export_dir, exist_ok=True)
    
    # Generate TXT content
    txt_content = "\n".join(lines)
    
    # Save file to disk
    file_path = os.path.join(export_dir, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    
    return {
        "success": True,
        "filename": filename,
        "file_path": file_path,
        "content_preview": txt_content[:200] + "..." if len(txt_content) > 200 else txt_content,
        "lines_count": len(lines),
        "download_url": f"/api/export/download/{filename}",
        "message": f"TXT file generated and saved: {filename}"
    }

@router.get("/claims/{claim_id}/check-sep")
async def check_sep_simrs(
    claim_id: int,
    sep_number: str = Query(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator"))
):
    """Check SEP in SIMRS (mock implementation for testing)"""
    
    # Mock SIMRS check (for testing)
    # In real implementation, this would call SIMRS API
    
    # Simulate different responses based on SEP format
    if len(sep_number) < 10:
        return {
            "found": False,
            "message": "Format SEP tidak valid",
            "details": "SEP harus minimal 10 karakter"
        }
    
    # Mock: if SEP starts with '0123', consider it found
    if sep_number.startswith('0123'):
        return {
            "found": True,
            "message": "SEP ditemukan di SIMRS",
            "patient_name": "PASIEN TEST SIMRS",
            "sep_date": "2024-10-21",
            "faskes_code": "0123",
            "details": "Data SEP valid dan terdaftar"
        }
    else:
        return {
            "found": False,
            "message": "SEP tidak ditemukan di SIMRS",
            "details": "SEP tidak terdaftar atau sudah kadaluarsa"
        }

@router.get("/claims/{claim_id}/preview")
async def preview_export_data(
    claim_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator"))
):
    """Preview export data before generating TXT"""
    
    # Get claim data
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Generate preview lines (without SEP number)
    lines = [
        "Line 1: Header - [AKAN DIISI DENGAN SEP]",
        f"Line 2: Patient - {claim.patient.nama if claim.patient else 'N/A'}",
        "Line 3: SEP Info - [DARI INPUT SEP]",
        "Line 4: Primary Diagnosis",
        "Line 5: Secondary Diagnosis", 
        "Line 6: Primary Procedure",
        "Line 7: Secondary Procedure",
        "Line 8: Tariff Information",
        "Line 9: Additional Costs",
        "Line 10: Total Billing",
        "Line 11: Special Conditions",
        "Line 12: Notes & Remarks"
    ]
    
    return {
        "success": True,
        "lines": lines,
        "claim_id": claim_id,
        "patient_name": claim.patient.nama if claim.patient else "N/A",
        "message": "Preview data berhasil dimuat"
    }

@router.get("/download/{filename}")
async def download_export_file(
    filename: str,
    user=Depends(require_roles_session("verifikator"))
):
    """Download exported TXT file"""
    
    # Security: validate filename
    if not filename.endswith('.txt') or '..' in filename or '/' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    export_dir = "/tmp/exports"
    file_path = os.path.join(export_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='text/plain'
    )