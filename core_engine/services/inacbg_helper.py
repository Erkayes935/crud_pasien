"""
INA-CBG Helper Service

Service untuk query CBG base code dan tarif dari database
Dipakai oleh analyze_diagnosis dan analyze_procedure
"""

import sys
import os

# Setup path untuk import database
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from web.backend.database import SessionLocal
from web.backend.models import INACBGTariff
from typing import Optional, Dict, List
import re


def get_cbg_base_from_icd10(icd10_code: str) -> Optional[str]:
    """
    Estimasi CBG base code dari ICD-10
    
    CATATAN: Ini hanya estimasi sederhana berdasarkan pola umum.
    Untuk akurasi penuh butuh aplikasi INA-CBG Grouper atau lookup table lengkap.
    
    Args:
        icd10_code: Kode ICD-10 (e.g., "J18.1")
    
    Returns:
        CBG base code (e.g., "I-4-10") atau None
    """
    
    # Mapping sederhana berdasarkan MDC (Major Diagnostic Category)
    # Format: prefix ICD-10 → CBG prefix
    
    icd_prefix = icd10_code[0] if icd10_code else ""
    
    # Rough mapping (akan diupdate dengan data lebih akurat)
    cbg_prefix_map = {
        "A": "Z",  # Infectious diseases → Various
        "B": "Z",  # Infectious diseases
        "C": "C",  # Neoplasms → Cancer
        "D": "C",  # Neoplasms
        "E": "K",  # Endocrine → Metabolic
        "F": "B",  # Mental → Behavioral
        "G": "B",  # Nervous system
        "H": "B",  # Eye/Ear → Sensory
        "I": "F",  # Circulatory → Cardiovascular
        "J": "I",  # Respiratory → Paru
        "K": "G",  # Digestive → GI
        "L": "J",  # Skin
        "M": "H",  # Musculoskeletal
        "N": "L",  # Genitourinary → GU
        "O": "O",  # Pregnancy → Obstetric
        "P": "P",  # Perinatal
        "Q": "Q",  # Congenital
        "R": "Z",  # Symptoms → Various
        "S": "H",  # Injury → Ortho
        "T": "H",  # Injury
        "Z": "Z",  # Factors
    }
    
    cbg_prefix = cbg_prefix_map.get(icd_prefix, "Z")
    
    # Return estimated base code (tanpa severity)
    # Format: {PREFIX}-4-10 (default medical path)
    return f"{cbg_prefix}-4-10"


def get_cbg_tariff(cbg_code: str, kelas_rs: str = "C", regional: str = "1") -> Optional[Dict]:
    """
    Get tarif INA-CBG dari database
    
    Args:
        cbg_code: Full CBG code (e.g., "I-4-10-II") atau base (e.g., "I-4-10")
        kelas_rs: Kelas RS ("A", "B", "C", "D")
        regional: Regional ("1" s/d "5")
    
    Returns:
        Dict dengan info tarif atau None jika tidak ditemukan
    """
    
    db = SessionLocal()
    
    try:
        # Query dari database
        tariff = db.query(INACBGTariff).filter(
            INACBGTariff.kode_cbg == cbg_code
        ).first()
        
        if not tariff:
            return None
        
        # Pilih tarif sesuai kelas
        tarif_selected = tariff.get_tarif_by_kelas(kelas_rs)
        
        return {
            "kode": tariff.kode_cbg,
            "deskripsi": tariff.deskripsi,
            "tarif": tarif_selected,
            "tarif_kelas_1": tariff.tarif_kelas_1,
            "tarif_kelas_2": tariff.tarif_kelas_2,
            "tarif_kelas_3": tariff.tarif_kelas_3,
            "regional": tariff.regional,
            "kelas_rs": kelas_rs,
            "tarif_formatted": f"Rp {tarif_selected:,}" if tarif_selected else "Rp 0"
        }
    
    finally:
        db.close()


def search_cbg_by_pattern(pattern: str, limit: int = 10) -> List[Dict]:
    """
    Search CBG codes by pattern
    
    Args:
        pattern: Pattern untuk search (e.g., "I-4%", "PNEUMONIA%")
        limit: Max hasil
    
    Returns:
        List of CBG info dicts
    """
    
    db = SessionLocal()
    
    try:
        # Search by kode atau deskripsi
        results = db.query(INACBGTariff).filter(
            (INACBGTariff.kode_cbg.ilike(f"%{pattern}%")) |
            (INACBGTariff.deskripsi.ilike(f"%{pattern}%"))
        ).limit(limit).all()
        
        return [
            {
                "kode": r.kode_cbg,
                "deskripsi": r.deskripsi,
                "tarif_kelas_3": r.tarif_kelas_3,
                "tarif_formatted": f"Rp {r.tarif_kelas_3:,}" if r.tarif_kelas_3 else "Rp 0"
            }
            for r in results
        ]
    
    finally:
        db.close()


def get_all_cbg_for_base(base_code: str) -> List[Dict]:
    """
    Get semua severity variants untuk satu base code
    
    Args:
        base_code: CBG base tanpa severity (e.g., "I-4-10")
    
    Returns:
        List [I-4-10-I, I-4-10-II, I-4-10-III] beserta tarifnya
    """
    
    db = SessionLocal()
    
    try:
        # Query semua yang match pattern
        results = db.query(INACBGTariff).filter(
            INACBGTariff.kode_cbg.ilike(f"{base_code}%")
        ).all()
        
        return [
            {
                "kode": r.kode_cbg,
                "deskripsi": r.deskripsi,
                "severity": r.kode_cbg.split("-")[-1] if "-" in r.kode_cbg else "I",
                "tarif_kelas_1": r.tarif_kelas_1,
                "tarif_kelas_2": r.tarif_kelas_2,
                "tarif_kelas_3": r.tarif_kelas_3,
                "tarif_formatted": f"Rp {r.tarif_kelas_3:,}" if r.tarif_kelas_3 else "Rp 0"
            }
            for r in results
        ]
    
    finally:
        db.close()


# ============================================
# INTEGRATION WITH ANALYZE SERVICES
# ============================================

def add_cbg_to_diagnosis_result(diagnosis_name: str, icd10_code: str, result: dict) -> dict:
    """
    Tambahkan info CBG base ke result analyze_diagnosis
    
    Args:
        diagnosis_name: Nama diagnosis
        icd10_code: Kode ICD-10
        result: Dict result dari analyze_diagnosis
    
    Returns:
        Updated result dict dengan cbg_preview
    """
    
    # Estimate CBG base
    cbg_base = get_cbg_base_from_icd10(icd10_code)
    
    if not cbg_base:
        return result
    
    # Get all severity variants
    cbg_variants = get_all_cbg_for_base(cbg_base)
    
    if not cbg_variants:
        # Jika database kosong, return estimasi aja
        result["cbg_preview"] = {
            "base_code": cbg_base,
            "note": "⚠️ Data tarif belum tersedia di database. Jalankan import_inacbg_tariff.py",
            "severity_pending": "Severity akan dihitung setelah ada data tindakan"
        }
        return result
    
    # Ambil severity I sebagai preview (karena belum ada tindakan)
    default_cbg = next((v for v in cbg_variants if v["severity"] == "I"), cbg_variants[0])
    
    result["cbg_preview"] = {
        "base_code": cbg_base,
        "estimated_code": default_cbg["kode"],
        "deskripsi": default_cbg["deskripsi"],
        "tarif_range": {
            "severity_I": next((v["tarif_formatted"] for v in cbg_variants if v["severity"] == "I"), "-"),
            "severity_II": next((v["tarif_formatted"] for v in cbg_variants if v["severity"] == "II"), "-"),
            "severity_III": next((v["tarif_formatted"] for v in cbg_variants if v["severity"] == "III"), "-"),
        },
        "note": "Tarif final akan dihitung setelah mapping tindakan dan komorbid"
    }
    
    return result


def add_cbg_to_procedure_result(icd10_code: str, icd9_codes: List[str], patient_data: dict, result: dict) -> dict:
    """
    Tambahkan info CBG final ke result analyze_procedure
    
    Args:
        icd10_code: Kode ICD-10 primary
        icd9_codes: List kode ICD-9 procedures
        patient_data: Dict dengan data pasien (komorbid, LOS, dll)
        result: Dict result dari analyze_procedure
    
    Returns:
        Updated result dict dengan cbg_final
    """
    
    # Get CBG base
    cbg_base = get_cbg_base_from_icd10(icd10_code)
    
    if not cbg_base:
        return result
    
    # Determine severity (simple logic)
    has_procedure = len(icd9_codes) > 0
    has_comorbid = len(patient_data.get("comorbids", [])) > 0
    los = patient_data.get("los", 0)
    
    # Simple severity logic
    if has_procedure and (has_comorbid or los > 7):
        severity = "III"
    elif has_procedure or has_comorbid or los > 4:
        severity = "II"
    else:
        severity = "I"
    
    # Build full CBG code
    cbg_full = f"{cbg_base}-{severity}"
    
    # Get tarif
    tariff_info = get_cbg_tariff(
        cbg_full,
        kelas_rs=patient_data.get("kelas_rs", "C"),
        regional=patient_data.get("regional", "1")
    )
    
    if tariff_info:
        result["cbg_final"] = {
            "kode": tariff_info["kode"],
            "base": cbg_base,
            "severity": severity,
            "deskripsi": tariff_info["deskripsi"],
            "tarif": tariff_info["tarif_formatted"],
            "tarif_raw": tariff_info["tarif"],
            "kelas_rs": tariff_info["kelas_rs"],
            "regional": tariff_info["regional"],
            "calculation_method": "Simple rule-based (v1.0)",
            "note": "✅ Tarif dari database INA-CBG resmi"
        }
    else:
        result["cbg_final"] = {
            "kode": cbg_full,
            "base": cbg_base,
            "severity": severity,
            "note": "⚠️ Tarif tidak ditemukan di database untuk kode: " + cbg_full,
            "suggestion": "Pastikan import_inacbg_tariff.py sudah dijalankan"
        }
    
    return result


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    print("🧪 Testing INA-CBG Helper Service\n")
    
    # Test 1: Get CBG base from ICD-10
    print("1️⃣ Testing get_cbg_base_from_icd10:")
    test_codes = ["J18.1", "I63.0", "K35.8"]
    for code in test_codes:
        base = get_cbg_base_from_icd10(code)
        print(f"  ICD-10 {code} → CBG base: {base}")
    
    # Test 2: Search CBG
    print("\n2️⃣ Testing search_cbg_by_pattern:")
    results = search_cbg_by_pattern("PNEUMONIA", limit=3)
    for r in results:
        print(f"  {r['kode']}: {r['deskripsi'][:50]}... | {r['tarif_formatted']}")
    
    # Test 3: Get all variants
    print("\n3️⃣ Testing get_all_cbg_for_base:")
    variants = get_all_cbg_for_base("I-4-10")
    for v in variants:
        print(f"  {v['kode']}: {v['tarif_formatted']}")
    
    # Test 4: Get tariff
    print("\n4️⃣ Testing get_cbg_tariff:")
    tariff = get_cbg_tariff("I-4-10-II", kelas_rs="C")
    if tariff:
        print(f"  Kode: {tariff['kode']}")
        print(f"  Deskripsi: {tariff['deskripsi'][:50]}...")
        print(f"  Tarif: {tariff['tarif_formatted']}")
    else:
        print("  ⚠️ Tarif tidak ditemukan (database masih kosong?)")
    
    print("\n✅ Testing done!")
