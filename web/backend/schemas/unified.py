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


# ============================================================
# FASE 3: EXCEL COLUMN MAPPING SCHEMAS
# ============================================================

class ColumnMatch(BaseModel):
    """Single column match result"""
    excel_column: str
    standard_field: str
    match_type: str  # "exact" | "fuzzy" | "manual"
    confidence: float  # 0-100


class ColumnAnalysis(BaseModel):
    """Analysis result of Excel columns"""
    total_rows: int
    total_columns: int
    exact_matches: list[ColumnMatch]
    fuzzy_matches: list[ColumnMatch]
    missing_fields: dict[str, str]  # {field: priority_level}
    extra_columns: list[str]
    preview_data: list[dict]  # First 10 rows
    available_fields: Optional[list[str]] = []  # All standard fields for dropdown


class ColumnMappingRequest(BaseModel):
    """User-confirmed column mapping for import"""
    column_mapping: dict[str, str]  # {"Excel Col": "standard_field"}
    extra_column_action: Optional[dict[str, str]] = {}  # {"Extra Col": "skip"|"add"}
    missing_field_values: Optional[dict[str, str]] = {}  # {"field": "default_value"}


class ImportProgress(BaseModel):
    """Real-time import progress"""
    total_rows: int
    processed: int
    success: int
    failed: int
    errors: list[str]


class ImportResult(BaseModel):
    """Final import result"""
    source_id: int
    records_imported: int
    records_failed: int
    duplicates_found: Optional[int] = 0
    errors: list[str]


