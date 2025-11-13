"""
Enhanced Standardizer Service
==============================
FASE 1.4 - Step 16: Comprehensive data standardization for ALL fields

Features:
- Text normalization (all text fields)
- Date format standardization (YYYY-MM-DD)
- Phone number cleaning
- Enum standardization (jenis_rawat)
- Whitespace cleanup

Before: Only diagnosis & tindakan
After: ALL 14+ fields standardized!
"""

import re
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text) -> str:
    """
    Basic text normalization.
    
    Steps:
    1. Convert to string
    2. Strip whitespace
    3. Title case (capitalize each word)
    4. Clean multiple spaces
    
    Args:
        text: Input text (any type)
        
    Returns:
        Normalized text
        
    Example:
        "  diabetes mellitus  " → "Diabetes Mellitus"
        "RAWAT INAP" → "Rawat Inap"
    """
    if not text:
        return ""
    
    # Convert to string and strip
    normalized = str(text).strip()
    
    # Clean multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Title case
    normalized = normalized.title()
    
    return normalized


# ============================================================
# ENUM STANDARDIZATION
# ============================================================

def standardize_jenis_rawat(value) -> str:
    """
    Standardize jenis_rawat enum values.
    
    Valid outputs:
    - "Rawat Inap"
    - "Rawat Jalan"
    
    Input variations:
    - "RI", "ri", "inap", "RAWAT INAP", "inpatient"  → "Rawat Inap"
    - "RJ", "rj", "jalan", "RAWAT JALAN", "outpatient" → "Rawat Jalan"
    
    Args:
        value: Raw jenis_rawat value
        
    Returns:
        Standardized value ("Rawat Inap" or "Rawat Jalan")
    """
    if not value:
        return "Rawat Inap"  # Default
    
    val = str(value).lower().strip()
    
    # Rawat Inap variations
    if any(x in val for x in ["inap", "ri", "ranap", "inpatient", "hospitalized"]):
        return "Rawat Inap"
    
    # Rawat Jalan variations
    if any(x in val for x in ["jalan", "rj", "rajal", "outpatient", "ambulatory"]):
        return "Rawat Jalan"
    
    # Default if ambiguous
    logger.warning(f"Ambiguous jenis_rawat value: '{value}', defaulting to 'Rawat Inap'")
    return "Rawat Inap"


# ============================================================
# DATE STANDARDIZATION
# ============================================================

def standardize_date(value) -> Optional[str]:
    """
    Convert various date formats to YYYY-MM-DD.
    
    Supported formats:
    - YYYY-MM-DD (unchanged)
    - DD/MM/YYYY → YYYY-MM-DD
    - DD-MM-YYYY → YYYY-MM-DD
    - DD.MM.YYYY → YYYY-MM-DD
    - YYYYMMDD → YYYY-MM-DD
    
    Args:
        value: Raw date value
        
    Returns:
        Date in YYYY-MM-DD format, or None if cannot parse
        
    Example:
        "27/10/2024" → "2024-10-27"
        "27-10-2024" → "2024-10-27"
        "2024-10-27" → "2024-10-27" (unchanged)
    """
    if not value:
        return None
    
    val = str(value).strip()
    
    # Already YYYY-MM-DD (valid format)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', val):
        return val
    
    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    # Fixed regex: escape dash or use at start/end of character class
    match = re.match(r'^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})$', val)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # YYYYMMDD (no separators)
    match = re.match(r'^(\d{4})(\d{2})(\d{2})$', val)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    
    # Try parsing with datetime (more formats)
    date_formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y/%m/%d",
        "%Y.%m.%d",
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(val, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # Cannot parse
    logger.warning(f"Cannot parse date: '{value}', keeping original value")
    return val


# ============================================================
# PHONE NUMBER CLEANING
# ============================================================

def clean_phone(value) -> Optional[str]:
    """
    Clean phone number: remove spaces, dashes, parentheses, +62 prefix.
    
    Steps:
    1. Remove all non-digits
    2. Replace +62 or 62 prefix with 0
    3. Return digits only
    
    Args:
        value: Raw phone number
        
    Returns:
        Cleaned phone number (digits only)
        
    Example:
        "0812-3456-7890" → "081234567890"
        "+62 812 3456 7890" → "081234567890"
        "(021) 123-4567" → "0211234567"
        "62812 3456 7890" → "081234567890"
    """
    if not value:
        return None
    
    val = str(value).strip()
    
    # Remove all non-digits
    digits = re.sub(r'\D', '', val)
    
    if not digits:
        return None
    
    # Replace +62 or 62 prefix with 0
    if digits.startswith('62') and len(digits) > 10:
        digits = '0' + digits[2:]
    
    return digits


# ============================================================
# MAIN STANDARDIZATION FUNCTION
# ============================================================

def run(data: dict) -> dict:
    """
    Enhanced standardization for ALL fields.
    
    FASE 1.4: Complete rewrite!
    
    Before (Old standardizer):
    - Only 2 fields: diagnosis, tindakan
    - Only title case
    
    After (New standardizer):
    - 14+ fields: all text, dates, phone, enums
    - Comprehensive normalization
    
    Fields standardized:
    - Text: diagnosis, tindakan, gejala, riwayat, obat
    - Enum: jenis_rawat
    - Date: tanggal_masuk, tanggal_keluar
    - Phone: no_telepon
    
    Args:
        data: Raw data dictionary
        
    Returns:
        Standardized data dictionary
    """
    
    # ========== 1. NORMALIZE TEXT FIELDS ==========
    text_fields = [
        "diagnosis",
        "tindakan", 
        "gejala",
        "riwayat",
        "obat",
        "hospital_id",
        "episode_id"
    ]
    
    for field in text_fields:
        if field in data and data[field]:
            data[field] = normalize_text(data[field])
    
    # ========== 2. STANDARDIZE ENUMS ==========
    if "jenis_rawat" in data:
        data["jenis_rawat"] = standardize_jenis_rawat(data["jenis_rawat"])
    
    # ========== 3. STANDARDIZE DATES ==========
    date_fields = ["tanggal_masuk", "tanggal_keluar"]
    
    for field in date_fields:
        if field in data and data[field]:
            standardized_date = standardize_date(data[field])
            if standardized_date:
                data[field] = standardized_date
    
    # ========== 4. CLEAN PHONE NUMBERS ==========
    if "no_telepon" in data and data["no_telepon"]:
        cleaned = clean_phone(data["no_telepon"])
        if cleaned:
            data["no_telepon"] = cleaned
    
    # ========== 5. CLEAN NUMERIC FIELDS ==========
    if "lama_rawat" in data:
        try:
            data["lama_rawat"] = int(data["lama_rawat"]) if data["lama_rawat"] else 0
        except (ValueError, TypeError):
            logger.warning(f"Cannot convert lama_rawat to int: {data['lama_rawat']}")
            data["lama_rawat"] = 0
    
    if "visit_no" in data:
        try:
            data["visit_no"] = int(data["visit_no"]) if data["visit_no"] else 1
        except (ValueError, TypeError):
            logger.warning(f"Cannot convert visit_no to int: {data['visit_no']}")
            data["visit_no"] = 1
    
    return data
