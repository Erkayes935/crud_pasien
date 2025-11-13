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
    "no_ktp": "nik",
    "nomor_ktp": "nik",
    "ktp": "nik",
    "no_identitas": "nik",
    "nomor_identitas": "nik",
    "id_card": "nik",
    "identity_number": "nik",
    
    # ========== ADDRESS VARIATIONS ==========
    "alamat_lengkap": "alamat",
    "alamat_pasien": "alamat",
    "address": "alamat",
    "alamat_rumah": "alamat",
    
    # ========== PHONE VARIATIONS ==========
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
    "lama_rawat_inap": "lama_rawat",
    "lama_hari": "lama_rawat",
    "jumlah_hari": "lama_rawat",
    "length_of_stay": "lama_rawat",
    "los": "lama_rawat",
    "lama_dirawat": "lama_rawat",
    "total_hari": "lama_rawat",
    
    # ========== SYMPTOMS VARIATIONS ==========
    "keluhan": "gejala",
    "keluhan_utama": "gejala",
    "chief_complaint": "gejala",
    "symptoms": "gejala",
    "gejala_klinis": "gejala",
    
    # ========== HISTORY VARIATIONS ==========
    "riwayat_penyakit": "riwayat",
    "riwayat_kesehatan": "riwayat",
    "medical_history": "riwayat",
    "history": "riwayat",
    "anamnesa": "riwayat",
    "anamnesis": "riwayat",
    
    # ========== TREATMENT/ACTION VARIATIONS ==========
    "tindakan_medis": "tindakan",
    "prosedur": "tindakan",
    "treatment": "tindakan",
    "procedure": "tindakan",
    "terapi": "tindakan",
    "penanganan": "tindakan",
    
    # ========== MEDICINE VARIATIONS ==========
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
