"""
Hasher Service - Generate Hash & Fingerprint untuk Duplicate Detection
Sesuai spesifikasi AI-CLAIM Data Hub
"""
import hashlib
from typing import Dict, Optional


def generate_content_hash(record_data: Dict) -> str:
    """
    Generate MD5 hash untuk EXACT duplicate detection.
    
    Hash dibuat dari field-field penting:
    - hospital_id: Scope duplicate per RS
    - diagnosis: Core clinical finding
    - tindakan: Core treatment
    - tanggal_masuk: Temporal scope
    - jenis_rawat: Type of care (Rawat Inap/Jalan/IGD)
    
    Args:
        record_data: Dictionary berisi data record
        
    Returns:
        str: MD5 hash (64 karakter hexadecimal)
        
    Example:
        >>> data = {
        ...     "hospital_id": "rs_001",
        ...     "diagnosis": "Pneumonia CAP",
        ...     "tindakan": "Antibiotik IV",
        ...     "tanggal_masuk": "2025-10-25",
        ...     "jenis_rawat": "Rawat Inap"
        ... }
        >>> hash_val = generate_content_hash(data)
        >>> len(hash_val)
        64
    """
    # Ambil field penting dengan default value
    hospital_id = record_data.get("hospital_id", "unknown")
    diagnosis = record_data.get("diagnosis", "")
    tindakan = record_data.get("tindakan", "")
    tanggal_masuk = record_data.get("tanggal_masuk", "")
    jenis_rawat = record_data.get("jenis_rawat", "")
    
    # Gabung jadi satu string dengan delimiter '|'
    key_string = f"{hospital_id}|{diagnosis}|{tindakan}|{tanggal_masuk}|{jenis_rawat}"
    
    # Generate MD5 hash
    hash_object = hashlib.md5(key_string.encode('utf-8'))
    content_hash = hash_object.hexdigest()
    
    return content_hash


def generate_fingerprint(record_data: Dict) -> str:
    """
    Generate text fingerprint untuk FUZZY duplicate detection.
    
    Fingerprint dibuat dari:
    - diagnosis: Core clinical finding
    - tindakan: Core treatment
    
    Text dinormalisasi (lowercase, strip whitespace) supaya:
    - "Pneumonia CAP" = "pneumonia cap"
    - "PNEUMONIA CAP" = "pneumonia cap"
    - "  Pneumonia CAP  " = "pneumonia cap"
    
    Nanti akan di-compare pakai RapidFuzz untuk fuzzy matching.
    
    Args:
        record_data: Dictionary berisi data record
        
    Returns:
        str: Normalized text fingerprint
        
    Example:
        >>> data = {
        ...     "diagnosis": "Pneumonia CAP",
        ...     "tindakan": "Antibiotik IV Ceftriaxone"
        ... }
        >>> fp = generate_fingerprint(data)
        >>> fp
        'pneumonia cap antibiotik iv ceftriaxone'
    """
    # Ambil field klinis penting
    diagnosis = record_data.get("diagnosis", "")
    tindakan = record_data.get("tindakan", "")
    
    # Handle None values (convert to empty string)
    diagnosis = diagnosis or ""
    tindakan = tindakan or ""
    
    # Normalize: lowercase dan strip whitespace
    diagnosis_clean = diagnosis.lower().strip()
    tindakan_clean = tindakan.lower().strip()
    
    # Gabung dengan spasi
    fingerprint = f"{diagnosis_clean} {tindakan_clean}".strip()
    
    return fingerprint


def generate_hashes(record_data: Dict) -> Dict[str, str]:
    """
    Generate BOTH hash dan fingerprint sekaligus.
    Helper function untuk kemudahan.
    
    Args:
        record_data: Dictionary berisi data record
        
    Returns:
        dict: {
            "content_hash": "...",
            "similarity_fingerprint": "..."
        }
        
    Example:
        >>> data = {
        ...     "hospital_id": "rs_001",
        ...     "diagnosis": "Pneumonia CAP",
        ...     "tindakan": "Antibiotik IV",
        ...     "tanggal_masuk": "2025-10-25",
        ...     "jenis_rawat": "Rawat Inap"
        ... }
        >>> hashes = generate_hashes(data)
        >>> "content_hash" in hashes
        True
        >>> "similarity_fingerprint" in hashes
        True
    """
    return {
        "content_hash": generate_content_hash(record_data),
        "similarity_fingerprint": generate_fingerprint(record_data)
    }


def verify_hash(record_data: Dict, expected_hash: str) -> bool:
    """
    Verify apakah hash dari data sesuai dengan expected hash.
    Berguna untuk integrity check.
    
    Args:
        record_data: Dictionary berisi data record
        expected_hash: Hash yang diexpect
        
    Returns:
        bool: True jika match, False jika tidak
        
    Example:
        >>> data = {"hospital_id": "rs_001", "diagnosis": "Pneumonia", 
        ...         "tindakan": "Antibiotik", "tanggal_masuk": "2025-10-25",
        ...         "jenis_rawat": "Rawat Inap"}
        >>> hash_val = generate_content_hash(data)
        >>> verify_hash(data, hash_val)
        True
        >>> verify_hash(data, "wrong_hash")
        False
    """
    actual_hash = generate_content_hash(record_data)
    return actual_hash == expected_hash
