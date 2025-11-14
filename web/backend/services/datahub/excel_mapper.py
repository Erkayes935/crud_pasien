"""
Excel Column Mapper Service
============================
Auto-maps Excel column variations to standard field names.

FASE 1.4 - Step 15: Dynamic Excel Column Mapping

Problem dari Ridho:
- Excel dari berbagai RS punya nama kolom berbeda
- "diagnosa" vs "diagnosis" vs "penyakit"
- "nama" vs "nama_pasien" vs "nama_lengkap"

Solution:
- Auto-map column variations ke standard fields
- Case-insensitive matching
- User-friendly (tidak perlu tahu exact column names)

Example:
    Input Excel:  {"diagnosa": "Diabetes", "nama": "Budi"}
    Output:       {"diagnosis": "Diabetes", "nama_pasien": "Budi"}
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================
# COLUMN MAPPING DICTIONARY
# ============================================================

COLUMN_MAPPING = {
    # ========== DIAGNOSIS VARIATIONS ==========
    "diagnosis": "diagnosis",  # ✅ Include standard name itself!
    "diagnosa": "diagnosis",
    "diagnos": "diagnosis",
    "penyakit": "diagnosis",
    "diagnose": "diagnosis",
    "diag": "diagnosis",
    
    # ========== PATIENT NAME VARIATIONS ==========
    "nama": "nama_pasien",
    "nama_lengkap": "nama_pasien",
    "nama_pasien": "nama_pasien",  # Keep standard
    "nama pasien": "nama_pasien",
    "patient_name": "nama_pasien",
    "name": "nama_pasien",
    "fullname": "nama_pasien",
    "nama_lengkap_pasien": "nama_pasien",
    
    # ========== NIK/KTP VARIATIONS ==========
    "nik": "nik",  # ✅ Standard name
    "no_ktp": "nik",
    "nomor_ktp": "nik",
    "ktp": "nik",
    "no_identitas": "nik",
    "nomor_identitas": "nik",
    "id_card": "nik",
    "identity_number": "nik",
    
    # ========== ADDRESS VARIATIONS ==========
    "alamat": "alamat",  # ✅ Standard name
    "alamat_lengkap": "alamat",
    "alamat_pasien": "alamat",
    "address": "alamat",
    "alamat_rumah": "alamat",
    
    # ========== PHONE VARIATIONS ==========
    "no_telepon": "no_telepon",  # ✅ Standard name
    "no_hp": "no_telepon",
    "nomor_hp": "no_telepon",
    "no_telp": "no_telepon",
    "nomor_telepon": "no_telepon",
    "telepon": "no_telepon",
    "phone": "no_telepon",
    "phone_number": "no_telepon",
    "mobile": "no_telepon",
    "handphone": "no_telepon",
    
    # ========== EMAIL VARIATIONS ==========
    "email": "email",  # ✅ Standard name
    "email_address": "email",
    "e_mail": "email",
    "alamat_email": "email",
    
    # ========== EPISODE ID VARIATIONS ==========
    "episode": "episode_id",
    "episode_number": "episode_id",
    "no_episode": "episode_id",
    "nomor_episode": "episode_id",
    
    # ========== VISIT NUMBER VARIATIONS ==========
    "visit": "visit_no",
    "visit_number": "visit_no",
    "no_kunjungan": "visit_no",
    "kunjungan_ke": "visit_no",
    "kunjungan": "visit_no",
    
    # ========== JENIS RAWAT VARIATIONS ==========
    "jenis_rawat": "jenis_rawat",  # ✅ Standard name
    "jenis_perawatan": "jenis_rawat",
    "tipe_rawat": "jenis_rawat",
    "care_type": "jenis_rawat",
    "perawatan": "jenis_rawat",
    
    # ========== DATE ADMISSION VARIATIONS ==========
    "tanggal_masuk_rs": "tanggal_masuk",
    "tgl_masuk": "tanggal_masuk",
    "tanggal_masuk": "tanggal_masuk",  # Keep standard
    "tanggal masuk": "tanggal_masuk",
    "tgl_masuk_rs": "tanggal_masuk",
    "admission_date": "tanggal_masuk",
    "date_admission": "tanggal_masuk",
    "tanggal_daftar": "tanggal_masuk",
    "tanggal_registrasi": "tanggal_masuk",
    
    # ========== DATE DISCHARGE VARIATIONS ==========
    "tanggal_keluar_rs": "tanggal_keluar",
    "tgl_keluar": "tanggal_keluar",
    "tanggal keluar": "tanggal_keluar",
    "discharge_date": "tanggal_keluar",
    "date_discharge": "tanggal_keluar",
    "tanggal_pulang": "tanggal_keluar",
    
    # ========== LENGTH OF STAY VARIATIONS ==========
    "lama_rawat": "lama_rawat",  # ✅ Standard name
    "lama_rawat_inap": "lama_rawat",
    "lama_hari": "lama_rawat",
    "jumlah_hari": "lama_rawat",
    "length_of_stay": "lama_rawat",
    "los": "lama_rawat",
    "lama_dirawat": "lama_rawat",
    "total_hari": "lama_rawat",
    
    # ========== SYMPTOMS VARIATIONS ==========
    "gejala": "gejala",  # ✅ Standard name
    "keluhan": "gejala",
    "keluhan_utama": "gejala",
    "chief_complaint": "gejala",
    "symptoms": "gejala",
    "gejala_klinis": "gejala",
    
    # ========== HISTORY VARIATIONS ==========
    "riwayat": "riwayat",  # ✅ Standard name
    "riwayat_penyakit": "riwayat",
    "riwayat_kesehatan": "riwayat",
    "medical_history": "riwayat",
    "history": "riwayat",
    "anamnesa": "riwayat",
    "anamnesis": "riwayat",
    
    # ========== TREATMENT/ACTION VARIATIONS ==========
    "tindakan": "tindakan",  # ✅ Standard name
    "tindakan_medis": "tindakan",
    "prosedur": "tindakan",
    "treatment": "tindakan",
    "procedure": "tindakan",
    "terapi": "tindakan",
    "penanganan": "tindakan",
    
    # ========== MEDICINE VARIATIONS ==========
    "obat": "obat",  # ✅ Standard name
    "obat_diberikan": "obat",
    "obat_yang_diberikan": "obat",
    "medication": "obat",
    "medicine": "obat",
    "resep": "obat",
    "resep_obat": "obat",
    "drugs": "obat",
    
    # ========== HOSPITAL ID VARIATIONS ==========
    "kode_rs": "hospital_id",
    "id_rs": "hospital_id",
    "hospital": "hospital_id",
    "rs": "hospital_id",
    "faskes": "hospital_id",
    "kode_faskes": "hospital_id",
    
    # ========== PATIENT FIELDS ==========
    "tanggal_lahir": "tanggal_lahir",
    "tgl_lahir": "tanggal_lahir",
    "date_of_birth": "tanggal_lahir",
    "dob": "tanggal_lahir",
    "lahir": "tanggal_lahir",
    "birth_date": "tanggal_lahir",
    
    "jenis_kelamin": "jenis_kelamin",
    "kelamin": "jenis_kelamin",
    "gender": "jenis_kelamin",
    "sex": "jenis_kelamin",
    "l_p": "jenis_kelamin",
    "jk": "jenis_kelamin",
    
    "no_rm": "no_rm",
    "nomor_rm": "no_rm",
    "rm": "no_rm",
    "medical_record": "no_rm",
    "rekam_medis": "no_rm",
    
    "no_bpjs": "no_bpjs",
    "nomor_bpjs": "no_bpjs",
    "bpjs": "no_bpjs",
    "kartu_bpjs": "no_bpjs",
    
    # ========== VISIT FIELDS ==========
    "tanggal_kunjungan": "tanggal_kunjungan",
    "tgl_kunjungan": "tanggal_kunjungan",
    "visit_date": "tanggal_kunjungan",
    
    "jenis_kunjungan": "jenis_kunjungan",
    "tipe_kunjungan": "jenis_kunjungan",
    "visit_type": "jenis_kunjungan",
    
    "episode_id": "episode_id",
    "episode": "episode_id",
    "no_episode": "episode_id",
    "episode_number": "episode_id",
    
    "visit_no": "visit_no",
    "no_visit": "visit_no",
    "kunjungan_ke": "visit_no",
    "visit_number": "visit_no",
    
    "poli": "poli",
    "poliklinik": "poli",
    "klinik": "poli",
    "clinic": "poli",
    "department": "poli",
    
    "eksternal_id": "eksternal_id",
    "external_id": "eksternal_id",
    "id_eksternal": "eksternal_id",
    
    "sumber": "sumber",
    "source": "sumber",
    "sumber_data": "sumber",
    
    # ========== DOCTOR FIELDS ==========
    "doctor_id": "doctor_id",
    "id_dokter": "doctor_id",
    "kode_dokter": "doctor_id",
    
    "doctor_name": "doctor_name",
    "nama_dokter": "doctor_name",
    "dokter": "doctor_name",
    "dr": "doctor_name",
    
    # ========== MEDICAL RECORD TYPE & DATE ==========
    "record_type": "record_type",
    "jenis_rekam": "record_type",
    "tipe_record": "record_type",
    "tipe_catatan": "record_type",
    
    "notes_date": "notes_date",
    "tanggal_catatan": "notes_date",
    "tgl_catatan": "notes_date",
    
    # ========== VITAL SIGNS ==========
    "tekanan_darah": "tekanan_darah",
    "td": "tekanan_darah",
    "blood_pressure": "tekanan_darah",
    "bp": "tekanan_darah",
    "tensi": "tekanan_darah",
    
    "nadi": "nadi",
    "pulse": "nadi",
    "denyut_nadi": "nadi",
    "heart_rate": "nadi",
    "hr": "nadi",
    
    "pernapasan": "pernapasan",
    "respiratory_rate": "pernapasan",
    "rr": "pernapasan",
    "napas": "pernapasan",
    
    "suhu": "suhu",
    "temperature": "suhu",
    "temp": "suhu",
    "suhu_badan": "suhu",
    
    "spo2": "spo2",
    "saturasi": "spo2",
    "saturasi_oksigen": "spo2",
    "oxygen_saturation": "spo2",
    
    "berat_badan": "berat_badan",
    "bb": "berat_badan",
    "weight": "berat_badan",
    "berat": "berat_badan",
    
    "tinggi_badan": "tinggi_badan",
    "tb": "tinggi_badan",
    "height": "tinggi_badan",
    "tinggi": "tinggi_badan",
    
    # ========== LAB RESULTS ==========
    "hemoglobin": "hemoglobin",
    "hb": "hemoglobin",
    "haemoglobin": "hemoglobin",
    
    "leukosit": "leukosit",
    "wbc": "leukosit",
    "white_blood_cell": "leukosit",
    "sel_darah_putih": "leukosit",
    
    "trombosit": "trombosit",
    "platelet": "trombosit",
    "plt": "trombosit",
    "keping_darah": "trombosit",
    
    "gula_darah": "gula_darah",
    "gds": "gula_darah",
    "gdp": "gula_darah",
    "blood_sugar": "gula_darah",
    "glucose": "gula_darah",
    
    "creatinin": "creatinin",
    "kreatinin": "creatinin",
    "creatinine": "creatinin",
    "cr": "creatinin",
    
    # ========== IMAGING ==========
    "rontgen_thorax": "rontgen_thorax",
    "rontgen": "rontgen_thorax",
    "xray": "rontgen_thorax",
    "chest_xray": "rontgen_thorax",
    "thorax": "rontgen_thorax",
    
    "ct_scan": "ct_scan",
    "ctscan": "ct_scan",
    "ct": "ct_scan",
    
    "usg": "usg",
    "ultrasound": "usg",
    "ultrasonography": "usg",
    
    # ========== DIAGNOSIS EXTENDED ==========
    "diagnosis_awal": "diagnosis_awal",
    "diag_awal": "diagnosis_awal",
    "initial_diagnosis": "diagnosis_awal",
    "diagnosis_masuk": "diagnosis_awal",
    
    "diagnosis_akhir": "diagnosis_akhir",
    "diag_akhir": "diagnosis_akhir",
    "final_diagnosis": "diagnosis_akhir",
    "diagnosis_keluar": "diagnosis_akhir",
    
    "komorbid": "komorbid",
    "comorbid": "komorbid",
    "penyakit_penyerta": "komorbid",
    "komorbiditas": "komorbid",
    
    "komplikasi": "komplikasi",
    "complication": "komplikasi",
    "penyulit": "komplikasi",
    
    # ========== MEDICAL HISTORY ==========
    "riwayat_penyakit": "riwayat_penyakit",
    "riwayat_penyakit_dahulu": "riwayat_penyakit",
    "medical_history": "riwayat_penyakit",
    
    "riwayat_pengobatan": "riwayat_pengobatan",
    "riwayat_obat": "riwayat_pengobatan",
    "medication_history": "riwayat_pengobatan",
    
    "riwayat_operasi": "riwayat_operasi",
    "riwayat_pembedahan": "riwayat_operasi",
    "surgery_history": "riwayat_operasi",
    
    "alergi": "alergi",
    "allergy": "alergi",
    "riwayat_alergi": "alergi",
    
    # ========== SYMPTOMS & COMPLAINTS ==========
    "keluhan": "keluhan",
    "chief_complaint": "keluhan",
    "keluhan_pasien": "keluhan",
    
    "gejala_lain": "gejala_lain",
    "gejala_tambahan": "gejala_lain",
    "other_symptoms": "gejala_lain",
    
    # ========== NOTES & VALIDATION ==========
    "notes_doctor": "notes_doctor",
    "catatan_dokter": "notes_doctor",
    "doctor_notes": "notes_doctor",
    "keterangan_dokter": "notes_doctor",
    
    "validasi_fornas": "validasi_fornas",
    "fornas": "validasi_fornas",
    "validasi_obat": "validasi_fornas",
    
    # ========== RECORD STATUS ==========
    "status": "status",
    "status_rekam": "status",
    "record_status": "status",
    
    "is_final": "is_final",
    "final": "is_final",
    "sudah_final": "is_final",
}


# ============================================================
# MAPPING FUNCTIONS
# ============================================================

def normalize_column_name(col: str) -> str:
    """
    Normalize column name untuk matching.
    
    Steps:
    1. Lowercase
    2. Strip whitespace
    3. Replace spaces with underscore
    4. Remove special characters
    
    Args:
        col: Original column name from Excel
        
    Returns:
        Normalized column name
        
    Example:
        "Nama Pasien" → "nama_pasien"
        "NO. KTP" → "no_ktp"
        "Diagnosa (ICD-10)" → "diagnosa"
    """
    if not col:
        return ""
    
    # Lowercase and strip
    normalized = str(col).lower().strip()
    
    # Replace spaces with underscore
    normalized = normalized.replace(" ", "_")
    
    # Remove special characters but keep underscore
    import re
    normalized = re.sub(r'[^a-z0-9_]', '', normalized)
    
    return normalized


def map_excel_columns(row: Dict[str, any]) -> Dict[str, any]:
    """
    Auto-map Excel columns to standard field names.
    
    Features:
    - Case-insensitive matching
    - Handles column name variations
    - Preserves original data if no mapping found
    - Logs unmapped columns for debugging
    
    Args:
        row: Dictionary from Excel row (pandas Series.to_dict())
        
    Returns:
        Dictionary with standardized field names
        
    Example:
        Input:  {"Diagnosa": "Diabetes", "Nama": "Budi Santoso"}
        Output: {"diagnosis": "Diabetes", "nama_pasien": "Budi Santoso"}
    """
    mapped = {}
    unmapped_columns = []
    
    for col, value in row.items():
        # Normalize column name
        normalized_col = normalize_column_name(col)
        
        # Try to map to standard field
        if normalized_col in COLUMN_MAPPING:
            standard_field = COLUMN_MAPPING[normalized_col]
            mapped[standard_field] = value
            logger.debug(f"Mapped column: '{col}' → '{standard_field}'")
        else:
            # Keep original if no mapping found
            mapped[normalized_col] = value
            unmapped_columns.append(col)
    
    # Log unmapped columns for debugging
    if unmapped_columns:
        logger.info(f"Unmapped columns (using original names): {unmapped_columns}")
    
    return mapped


def get_standard_field_name(column_name: str) -> Optional[str]:
    """
    Get standard field name for a given column variation.
    
    Args:
        column_name: Original column name from Excel
        
    Returns:
        Standard field name or None if no mapping exists
        
    Example:
        >>> get_standard_field_name("diagnosa")
        "diagnosis"
        >>> get_standard_field_name("unknown_column")
        None
    """
    normalized = normalize_column_name(column_name)
    return COLUMN_MAPPING.get(normalized)


def validate_required_fields(data: Dict[str, any]) -> bool:
    """
    Validate that required fields are present after mapping.
    
    Required fields:
    - diagnosis
    - tindakan
    - jenis_rawat
    - tanggal_masuk
    
    Args:
        data: Mapped data dictionary
        
    Returns:
        True if all required fields present, False otherwise
        
    Raises:
        ValueError: If required fields missing (with details)
    """
    required_fields = ["diagnosis", "tindakan", "jenis_rawat", "tanggal_masuk"]
    missing_fields = []
    
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValueError(
            f"Required fields missing after column mapping: {', '.join(missing_fields)}"
        )
    
    return True


def get_mapping_stats() -> Dict[str, int]:
    """
    Get statistics about column mapping coverage.
    
    Returns:
        Dictionary with mapping statistics
    """
    unique_standard_fields = set(COLUMN_MAPPING.values())
    
    return {
        "total_variations": len(COLUMN_MAPPING),
        "unique_standard_fields": len(unique_standard_fields),
        "average_variations_per_field": len(COLUMN_MAPPING) / len(unique_standard_fields)
    }


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def add_custom_mapping(from_col: str, to_field: str):
    """
    Add custom column mapping at runtime.
    
    Useful for handling RS-specific column names.
    
    Args:
        from_col: Source column name (will be normalized)
        to_field: Target standard field name
        
    Example:
        >>> add_custom_mapping("dx_utama", "diagnosis")
        >>> add_custom_mapping("nama_px", "nama_pasien")
    """
    normalized = normalize_column_name(from_col)
    COLUMN_MAPPING[normalized] = to_field
    logger.info(f"Added custom mapping: '{from_col}' → '{to_field}'")


def get_all_variations_for_field(field_name: str) -> list:
    """
    Get all column variations that map to a standard field.
    
    Args:
        field_name: Standard field name (e.g., "diagnosis")
        
    Returns:
        List of column variations
        
    Example:
        >>> get_all_variations_for_field("diagnosis")
        ["diagnosa", "diagnos", "penyakit", "diagnose", "diag"]
    """
    return [col for col, standard in COLUMN_MAPPING.items() if standard == field_name]


# ============================================================
# FASE 3: FUZZY MATCHING & COLUMN ANALYSIS
# ============================================================

# Field priority levels for validation
FIELD_PRIORITY = {
    # ========== CRITICAL (MUST HAVE) ==========
    # Block import if missing - These are REQUIRED for medical record validity
    "diagnosis": "critical",
    "tindakan": "critical",
    "jenis_rawat": "critical",
    "tanggal_masuk": "critical",
    
    # ========== HIGH (SHOULD HAVE) ==========
    # Use default if missing - Important but can be filled with defaults
    "nama_pasien": "high",
    "tanggal_kunjungan": "high",
    
    # ========== OPTIONAL (NICE TO HAVE) ==========
    # Allow NULL - Can fill later or leave empty
    
    # Patient demographics
    "nik": "optional",
    "no_rm": "optional",
    "no_bpjs": "optional",
    "alamat": "optional",
    "no_telepon": "optional",
    "email": "optional",
    "tanggal_lahir": "optional",
    "jenis_kelamin": "optional",
    
    # Visit information
    "lama_rawat": "optional",
    "tanggal_keluar": "optional",
    "episode_id": "optional",
    "visit_no": "optional",
    "jenis_kunjungan": "optional",
    "poli": "optional",
    "eksternal_id": "optional",
    "sumber": "optional",
    
    # Clinical symptoms & history
    "gejala": "optional",
    "keluhan": "optional",
    "gejala_lain": "optional",
    "riwayat": "optional",
    "riwayat_penyakit": "optional",
    "riwayat_pengobatan": "optional",
    "riwayat_operasi": "optional",
    "alergi": "optional",
    
    # Diagnosis details
    "diagnosis_awal": "optional",
    "diagnosis_akhir": "optional",
    "komorbid": "optional",
    "komplikasi": "optional",
    
    # Treatment & medication
    "obat": "optional",
    "validasi_fornas": "optional",
    
    # Doctor information
    "doctor_id": "optional",
    "doctor_name": "optional",
    
    # Vital signs
    "tekanan_darah": "optional",
    "nadi": "optional",
    "pernapasan": "optional",
    "suhu": "optional",
    "spo2": "optional",
    "berat_badan": "optional",
    "tinggi_badan": "optional",
    
    # Lab results
    "hemoglobin": "optional",
    "leukosit": "optional",
    "trombosit": "optional",
    "gula_darah": "optional",
    "creatinin": "optional",
    
    # Imaging
    "rontgen_thorax": "optional",
    "ct_scan": "optional",
    "usg": "optional",
    
    # Record metadata
    "record_type": "optional",
    "notes_date": "optional",
    "notes_doctor": "optional",
    "status": "optional",
    "is_final": "optional",
    
    # System fields
    "hospital_id": "optional",
}


def fuzzy_match_column(excel_col: str, threshold: int = 75) -> Optional[Dict[str, any]]:
    """
    Find best fuzzy match for an Excel column name.
    
    Uses fuzzywuzzy library to find similarity with standard field names.
    
    Args:
        excel_col: Column name from Excel
        threshold: Minimum similarity score (0-100). Default 75 for balanced precision/recall.
        
    Returns:
        Dictionary with match info or None if no match >= threshold
        {
            "standard_field": "diagnosis",
            "score": 85.5,
            "match_type": "fuzzy"
        }
        
    Example:
        >>> fuzzy_match_column("Diagnosa")
        {"standard_field": "diagnosis", "score": 87.5, "match_type": "fuzzy"}
        
        >>> fuzzy_match_column("Random Column")
        None  # No match >= 75%
    """
    from fuzzywuzzy import fuzz
    
    # Normalize input column
    normalized_col = normalize_column_name(excel_col)
    
    # Blacklist: Columns that should NOT auto-map (hospital-specific fields)
    # These are extra columns that are similar to standard fields but have different meanings
    BLACKLIST = [
        "hospital_code",  # Similar to hospital_id but different (internal code vs ID)
        "biaya_rawat",
        "kelas_perawatan",
        "ruang_rawat",
        "status_pembayaran",
        "no_registrasi_rs",
        "kode_icd10",
        "payment_method",
        "insurance_type",
        "room_number",
        "custom_field_1",
        "custom_field_2",
    ]
    
    # If column is blacklisted, return None (force to Extra Columns)
    if normalized_col in BLACKLIST:
        return None
    
    # Try exact match first (from COLUMN_MAPPING)
    if normalized_col in COLUMN_MAPPING:
        return {
            "standard_field": COLUMN_MAPPING[normalized_col],
            "score": 100.0,
            "match_type": "exact"
        }
    
    # Get all unique standard field names
    all_standard_fields = set(COLUMN_MAPPING.values())
    
    # Find best fuzzy match
    best_match = None
    best_score = 0
    
    for standard_field in all_standard_fields:
        # Compare with standard field name
        score = fuzz.ratio(normalized_col, standard_field)
        
        # Also check against all variations of this field
        variations = get_all_variations_for_field(standard_field)
        for variation in variations:
            var_score = fuzz.ratio(normalized_col, variation)
            score = max(score, var_score)
        
        if score > best_score:
            best_score = score
            best_match = standard_field
    
    # Return only if meets threshold
    if best_score >= threshold:
        return {
            "standard_field": best_match,
            "score": float(best_score),
            "match_type": "fuzzy"
        }
    
    return None


def analyze_excel_columns(df, threshold: int = 75) -> Dict[str, any]:
    """
    Analyze Excel DataFrame columns and suggest mappings.
    
    Categorizes columns into:
    - exact_matches: Perfect matches via COLUMN_MAPPING
    - fuzzy_matches: Similarity >= threshold
    - missing_fields: Expected fields not found in Excel
    - extra_columns: Excel columns with no standard mapping
    
    Args:
        df: pandas DataFrame from Excel
        threshold: Fuzzy matching threshold (default 75%)
        
    Returns:
        Dictionary with analysis results
        
    Example:
        >>> df = pd.read_excel("data.xlsx")
        >>> analysis = analyze_excel_columns(df)
        >>> print(analysis["exact_matches"])
        [{"excel_column": "diagnosis", "standard_field": "diagnosis", ...}]
    """
    import pandas as pd
    
    # Get all unique standard fields from COLUMN_MAPPING for dropdown
    all_available_fields = sorted(set(COLUMN_MAPPING.values()))
    
    analysis = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "exact_matches": [],
        "fuzzy_matches": [],
        "missing_fields": {},
        "extra_columns": [],
        "preview_data": df.head(10).to_dict('records') if len(df) > 0 else [],
        "available_fields": all_available_fields  # All 59 unique standard fields for dropdown
    }
    
    # Track which standard fields we've found
    found_standard_fields = set()
    
    # Analyze each Excel column
    for excel_col in df.columns:
        match_result = fuzzy_match_column(excel_col, threshold)
        
        if match_result:
            found_standard_fields.add(match_result["standard_field"])
            
            match_info = {
                "excel_column": str(excel_col),
                "standard_field": match_result["standard_field"],
                "match_type": match_result["match_type"],
                "confidence": match_result["score"]
            }
            
            if match_result["match_type"] == "exact":
                analysis["exact_matches"].append(match_info)
            else:
                analysis["fuzzy_matches"].append(match_info)
        else:
            # No match found - extra column
            analysis["extra_columns"].append(str(excel_col))
    
    # Find missing fields - Show ALL standard fields from COLUMN_MAPPING
    # Get all unique standard field names from COLUMN_MAPPING
    all_standard_fields = set(COLUMN_MAPPING.values())
    
    for field in all_standard_fields:
        if field not in found_standard_fields:
            # Get priority if defined, otherwise mark as "optional"
            priority = FIELD_PRIORITY.get(field, "optional")
            analysis["missing_fields"][field] = priority
    
    return analysis


def apply_column_mapping(df, column_mapping: Dict[str, str], 
                        extra_column_action: Dict[str, str] = None,
                        missing_field_values: Dict[str, str] = None):
    """
    Apply user-confirmed column mapping to DataFrame.
    
    Steps:
    1. Rename columns according to mapping
    2. Handle extra columns (skip or keep)
    3. Fill missing fields with default values
    4. Validate result
    
    Args:
        df: pandas DataFrame
        column_mapping: {"Excel Column": "standard_field", ...}
        extra_column_action: {"Extra Column": "skip"|"add", ...}
        missing_field_values: {"field": "default_value", ...}
        
    Returns:
        Transformed DataFrame ready for import
        
    Example:
        >>> mapping = {"Diagnosa": "diagnosis", "Nama": "nama_pasien"}
        >>> df_clean = apply_column_mapping(df, mapping)
    """
    import pandas as pd
    
    # Create a copy to avoid modifying original
    df_mapped = df.copy()
    
    # Step 1: Rename columns according to mapping
    rename_dict = {}
    for excel_col, standard_field in column_mapping.items():
        if excel_col in df_mapped.columns:
            rename_dict[excel_col] = standard_field
    
    df_mapped = df_mapped.rename(columns=rename_dict)
    
    # Step 2: Handle extra columns
    if extra_column_action:
        cols_to_drop = []
        for excel_col, action in extra_column_action.items():
            if action == "skip" and excel_col in df_mapped.columns:
                cols_to_drop.append(excel_col)
        
        if cols_to_drop:
            df_mapped = df_mapped.drop(columns=cols_to_drop)
    
    # Step 3: Fill missing fields with defaults
    if missing_field_values:
        for field, default_value in missing_field_values.items():
            if field not in df_mapped.columns:
                if default_value == "__block__":
                    # Skip - this should have been caught by frontend validation
                    continue
                elif default_value == "__manual__":
                    # Set placeholder value for manual filling later
                    df_mapped[field] = "TBD"
                else:
                    # Add column with default value
                    df_mapped[field] = default_value
    
    return df_mapped


# ============================================================
# TESTING HELPER
# ============================================================

if __name__ == "__main__":
    # Test mapping
    test_row = {
        "Diagnosa": "Diabetes Mellitus",
        "Nama": "Budi Santoso",
        "NO. KTP": "3201234567890123",
        "Tgl Masuk": "2025-10-27",
        "Lama Hari": "3"
    }
    
    mapped = map_excel_columns(test_row)
    print("Original:", test_row)
    print("Mapped:", mapped)
    
    stats = get_mapping_stats()
    print("\nMapping Stats:", stats)
