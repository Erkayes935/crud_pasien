from pydantic import BaseModel
from typing import Optional

class UnifiedClinicalRecord(BaseModel):
    record_id: Optional[str] = None
    hospital_id: Optional[str] = None
    source: str
    episode_id: Optional[str] = None
    visit_no: Optional[int] = 1
    jenis_rawat: str
    tanggal_masuk: str
    lama_rawat: Optional[int] = None
    gejala: Optional[str] = None
    riwayat: Optional[str] = None
    diagnosis: str
    tindakan: str
    obat: Optional[str] = None
    status: str = "ingested"
    
    # FASE 1.2: PHI fields (akan di-remove setelah anonymization)
    nama_pasien: Optional[str] = None
    nik: Optional[str] = None
    alamat: Optional[str] = None
    no_telepon: Optional[str] = None
    email: Optional[str] = None
    
    # FASE 1.2: Anonymous identifier (added after anonymization atau dari Gateway)
    patient_uuid: Optional[str] = None
    
    # FASE 1.2: PHI fields (akan di-remove setelah anonymization)
    nama_pasien: Optional[str] = None
    nik: Optional[str] = None
    alamat: Optional[str] = None
    no_telepon: Optional[str] = None
    email: Optional[str] = None
    
    # FASE 1.2: Anonymous identifier (added after anonymization)
    patient_uuid: Optional[str] = None

