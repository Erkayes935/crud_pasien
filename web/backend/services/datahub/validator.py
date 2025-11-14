"""
Enhanced Validator Service
===========================
FASE 1.4 - Step 17: Comprehensive field validation

Features:
- Required field validation
- Date format validation (YYYY-MM-DD only)
- Numeric range validation
- Enum validation (jenis_rawat)
- Business logic validation (tanggal_keluar >= tanggal_masuk)
- Type checking

Before: Only check required fields
After: Complete validation with business rules!
"""

import re
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================
# DATE VALIDATION
# ============================================================

def validate_date_format(date_str, field_name="tanggal") -> bool:
    """
    Validate date is in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to validate
        field_name: Field name for error message
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If date format invalid
        
    Example:
        validate_date_format("2024-10-27", "tanggal_masuk")  # OK
        validate_date_format("27/10/2024", "tanggal_masuk")  # ValueError!
        validate_date_format("TBD", "tanggal_masuk")  # OK (will use default)
    """
    if not date_str:
        return True  # Allow None/empty (optional fields)
    
    date_str = str(date_str).strip()
    
    # Allow sentinel values (will be handled by processor with defaults)
    if date_str.upper() in ('TBD', '__DEFAULT__', '__BLOCK__'):
        return True
    
    # Check format: YYYY-MM-DD
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise ValueError(
            f"{field_name} harus format YYYY-MM-DD (contoh: 2024-10-27) atau 'TBD' untuk tanggal default. "
            f"Nilai sekarang: '{date_str}'"
        )
    
    # Validate date is real (not 2024-13-99)
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"{field_name} bukan tanggal valid: '{date_str}' ({str(e)})")
    
    return True


# ============================================================
# NUMERIC VALIDATION
# ============================================================

def validate_numeric_range(value, field_name, min_val=None, max_val=None) -> bool:
    """
    Validate numeric field is within range.
    
    Args:
        value: Numeric value to validate
        field_name: Field name for error message
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If value out of range or not numeric
    """
    if value is None or value == "":
        return True  # Allow None/empty (optional fields)
    
    try:
        num = float(value) if isinstance(value, str) else value
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} harus berupa angka. Nilai sekarang: '{value}'")
    
    if min_val is not None and num < min_val:
        raise ValueError(
            f"{field_name} tidak boleh kurang dari {min_val}. "
            f"Nilai sekarang: {num}"
        )
    
    if max_val is not None and num > max_val:
        raise ValueError(
            f"{field_name} tidak boleh lebih dari {max_val}. "
            f"Nilai sekarang: {num}"
        )
    
    return True


# ============================================================
# ENUM VALIDATION
# ============================================================

def validate_enum(value, field_name, allowed_values) -> bool:
    """
    Validate field value is in allowed list.
    
    Args:
        value: Value to validate
        field_name: Field name for error message
        allowed_values: List of allowed values
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If value not in allowed list
    """
    if not value:
        return True  # Allow None/empty (optional fields)
    
    val = str(value).strip()
    
    if val not in allowed_values:
        raise ValueError(
            f"{field_name} harus salah satu dari: {', '.join(allowed_values)}. "
            f"Nilai sekarang: '{val}'"
        )
    
    return True


# ============================================================
# BUSINESS LOGIC VALIDATION
# ============================================================

def validate_date_logic(data: dict) -> bool:
    """
    Validate business logic for dates.
    
    Rules:
    - tanggal_keluar >= tanggal_masuk (if both present)
    - lama_rawat consistent with dates (if all present)
    
    Args:
        data: Data dictionary with date fields
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If business logic violated
    """
    tanggal_masuk = data.get("tanggal_masuk")
    tanggal_keluar = data.get("tanggal_keluar")
    
    if not tanggal_masuk or not tanggal_keluar:
        return True  # Cannot validate without both dates
    
    try:
        dt_masuk = datetime.strptime(str(tanggal_masuk), "%Y-%m-%d")
        dt_keluar = datetime.strptime(str(tanggal_keluar), "%Y-%m-%d")
        
        if dt_keluar < dt_masuk:
            raise ValueError(
                f"tanggal_keluar ({tanggal_keluar}) tidak boleh lebih awal dari "
                f"tanggal_masuk ({tanggal_masuk})"
            )
        
        # Optional: Check lama_rawat consistency
        if "lama_rawat" in data and data["lama_rawat"] is not None:
            calculated_days = (dt_keluar - dt_masuk).days
            lama_rawat = int(data["lama_rawat"])
            
            # Allow some flexibility (±1 day for partial days)
            if abs(calculated_days - lama_rawat) > 1:
                logger.warning(
                    f"lama_rawat ({lama_rawat}) tidak konsisten dengan "
                    f"tanggal_masuk - tanggal_keluar ({calculated_days} hari). "
                    f"Data tetap disimpan."
                )
    
    except ValueError as e:
        if "does not match format" in str(e):
            # Date format error, will be caught by validate_date_format
            pass
        else:
            raise
    
    return True


# ============================================================
# MAIN VALIDATION FUNCTION
# ============================================================

def validate_fields(data: dict) -> bool:
    """
    Enhanced comprehensive field validation.
    
    FASE 1.4: Complete rewrite!
    
    Before (Old validator):
    - Only check required fields
    
    After (New validator):
    - Required fields
    - Date format (YYYY-MM-DD)
    - Numeric ranges
    - Enum values
    - Business logic
    
    Validation rules:
    1. Required fields: source, diagnosis, tindakan, jenis_rawat, tanggal_masuk
    2. Date format: YYYY-MM-DD only
    3. Numeric: lama_rawat >= 0, visit_no >= 1
    4. Enum: jenis_rawat in ["Rawat Inap", "Rawat Jalan"]
    5. Business: tanggal_keluar >= tanggal_masuk
    
    Args:
        data: Data dictionary to validate
        
    Returns:
        True if all validations pass
        
    Raises:
        ValueError: If any validation fails (with detailed message)
    """
    
    # ========== 1. REQUIRED FIELDS ==========
    required = ["source", "diagnosis", "tindakan", "jenis_rawat", "tanggal_masuk"]
    missing = [f for f in required if not data.get(f)]
    
    if missing:
        raise ValueError(f"Field wajib tidak boleh kosong: {', '.join(missing)}")
    
    # ========== 2. DATE FORMAT VALIDATION ==========
    # tanggal_masuk (required)
    validate_date_format(data.get("tanggal_masuk"), "tanggal_masuk")
    
    # tanggal_keluar (optional)
    if "tanggal_keluar" in data and data["tanggal_keluar"]:
        validate_date_format(data.get("tanggal_keluar"), "tanggal_keluar")
    
    # ========== 3. NUMERIC RANGE VALIDATION ==========
    # lama_rawat: must be >= 0
    if "lama_rawat" in data and data["lama_rawat"] is not None:
        validate_numeric_range(
            data["lama_rawat"], 
            "lama_rawat", 
            min_val=0, 
            max_val=365  # Max 1 year (reasonable limit)
        )
    
    # visit_no: must be >= 1
    if "visit_no" in data and data["visit_no"] is not None:
        validate_numeric_range(
            data["visit_no"], 
            "visit_no", 
            min_val=1, 
            max_val=9999  # Reasonable limit
        )
    
    # ========== 4. ENUM VALIDATION ==========
    # jenis_rawat: must be "Rawat Inap" or "Rawat Jalan"
    validate_enum(
        data.get("jenis_rawat"), 
        "jenis_rawat", 
        ["Rawat Inap", "Rawat Jalan"]
    )
    
    # ========== 5. BUSINESS LOGIC VALIDATION ==========
    # tanggal_keluar >= tanggal_masuk
    validate_date_logic(data)
    
    # ========== 6. TEXT LENGTH VALIDATION (Optional) ==========
    # Prevent extremely long text that could break storage
    text_fields_limits = {
        "diagnosis": 500,
        "tindakan": 500,
        "gejala": 1000,
        "riwayat": 1000,
        "obat": 500
    }
    
    for field, max_length in text_fields_limits.items():
        if field in data and data[field]:
            text = str(data[field])
            if len(text) > max_length:
                logger.warning(
                    f"{field} terlalu panjang ({len(text)} karakter, "
                    f"max {max_length}). Akan dipotong."
                )
                data[field] = text[:max_length] + "..."
    
    return True


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def is_valid_phone(phone: str) -> bool:
    """
    Quick validation for Indonesian phone number.
    
    Rules:
    - Must start with 0 or +62
    - Length: 10-13 digits (after cleaning)
    
    Args:
        phone: Phone number string
        
    Returns:
        True if valid format
    """
    if not phone:
        return True
    
    # Remove non-digits
    digits = re.sub(r'\D', '', phone)
    
    # Check length
    if len(digits) < 10 or len(digits) > 13:
        return False
    
    # Check prefix
    if not (digits.startswith('0') or digits.startswith('62')):
        return False
    
    return True
