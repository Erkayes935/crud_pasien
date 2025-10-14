# services/regulation_service.py
import os
import json
from datetime import date
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
from typing import Dict, List, Any

# Import multilayer rules system
from .rules_loader import load_rules_for_diagnosis, get_rules_summary, LAYER_PRIORITIES

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------
# Mapping field → regulasi - disesuaikan dengan claim.modals.js
# ---------------------------
FIELD_REGULATION_MAP = {
    # Klinis
    "justifikasi": ["PNPK", "CP", "Permenkes"],
    "bukti_klinis": [],  # tidak perlu regulasi
    "syarat_klinis": ["PNPK", "CP", "Permenkes"],
    "confidence_ai": [],  # tidak perlu regulasi
    
    # ICD-10
    "kode_icd": ["ICD-10 WHO", "Mapping BPJS"],
    "struktur_icd10": ["ICD-10 WHO"], 
    "kode_ganda": ["ICD-10 WHO"],
    "z_code": ["ICD-10 WHO"],
    "kode_bpjs_khusus": ["Aturan BPJS e-Claim"],
    
    # Tindakan
    "syarat_klinis_tindakan": ["PNPK", "CP", "BPJS"],
    "status": ["INA-CBG", "CP"],  # status_tindakan di frontend
    "ina_cbg": ["INA-CBG Casemix"],  # ina_cbg_impact di frontend
    
    # Rawat Inap
    "indikasi": ["PNPK", "CP"],  # indikasi_rawat di frontend
    "kriteria": ["PNPK", "CP"],  # kriteria_rawat di frontend
    "lama_rawat": ["PNPK", "INA-CBG"],
    
    # Faskes
    "tingkat": ["Permenkes RS", "INA-CBG"],  # kesesuaian_rs di frontend
    "justifikasi_faskes": ["Permenkes RS", "PNPK"],
    "kompetensi": ["Permenkes RS", "PNPK"],
    
    # Rujukan
    "indikasi_rujukan": ["Permenkes Rujukan", "INA-CBG"],
    "tujuan": ["Permenkes Rujukan"],
    "kriteria_rujukan": ["Permenkes Rujukan", "PNPK"],
    
    # INA-CBG
    "kode": ["INA-CBG resmi"],
    "deskripsi": ["INA-CBG resmi"],
    "tarif": ["INA-CBG Casemix"],
    
    # Detail Prosedur
    "icd9_code": ["ICD-9-CM resmi"],
    "icd9_desc": ["ICD-9-CM resmi"],
    "validitas": [],  # tidak perlu regulasi
    "faskes": ["Permenkes RS"],  # faskes_proc di frontend
    "rawat_inap": ["PNPK", "INA-CBG"],  # rawat_inap_proc di frontend
    
    # i-DRG
    "group_idrg": ["i-DRG", "INA-CBG"],
    "severity_index": ["i-DRG", "INA-CBG"],
    "checklist": ["i-DRG", "INA-CBG"],
    "faktor_severity": ["i-DRG", "INA-CBG"],
    "ungroupable_alert": ["i-DRG", "INA-CBG"],
    "simulasi_tarif": ["i-DRG", "INA-CBG"],
    "gap_analysis": ["i-DRG", "INA-CBG"],
    
    # i-DRG Summary
    "group_idrg_kombinasi": ["i-DRG", "INA-CBG"],
    "severity_kombinasi": ["i-DRG", "INA-CBG"],
    "checklist_kombinasi": ["i-DRG", "INA-CBG"],
    "risiko_ungroupable": ["i-DRG", "INA-CBG"],
    "estimasi_tarif": ["i-DRG", "INA-CBG"],
    "gap_inacbg_vs_idrg": ["i-DRG", "INA-CBG"],
    
    # Namespacing untuk field spesifik
    "idrg_diagnosis_group": ["i-DRG", "INA-CBG"],
    "idrg_diagnosis_severity": ["i-DRG", "INA-CBG"],
    "idrg_diagnosis_checklist": ["i-DRG", "INA-CBG"],
    "idrg_diagnosis_ungroupable": ["i-DRG", "INA-CBG"],
    "idrg_summary_group": ["i-DRG", "INA-CBG"],
    "idrg_summary_severity": ["i-DRG", "INA-CBG"],
    "idrg_summary_checklist": ["i-DRG", "INA-CBG"],
    "idrg_summary_ungroupable": ["i-DRG", "INA-CBG"],
}

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"

# ---------------------------
# Utils
# ---------------------------
def load_rule_files(kategori: str):
    """Coba load file diagnosis rules berdasarkan kategori (mis. Pneumonia.json)"""
    diagnosis_file = RULES_DIR / "diagnosis" / f"{kategori.lower().replace(' ', '')}.json"
    if diagnosis_file.exists():
        with open(diagnosis_file, encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_global_rules():
    """Load semua file global (clinical_rules, fornas, icd9/icd10 mapping, ina_cbg)."""
    global_files = [
        "clinical_rules.json",
        "cp_pnpk.json",
        "fornas.json",
        "icd9_mapping.json",
        "icd10_mapping.json",
        "ina_cbg.json"
    ]
    data = {}
    for fname in global_files:
        fpath = RULES_DIR / fname
        if fpath.exists():
            with open(fpath, encoding="utf-8") as f:
                data[fname.replace(".json", "")] = json.load(f)
    return data

# ---------------------------
# Service utama
# ---------------------------
def process_regulation_detail(payload: dict, field: str):
    """
    Process regulation detail using multilayer rules system
    Returns regulations organized by layer (permenkes, nasional, ppk, regional, rs, bridging, fraud, temporary)
    """
    claim_id = payload.get("claim_id")
    item_id = payload.get("item_id")
    field_name = field  # save original field name
    
    # Extract diagnosis/category information
    kategori = payload.get("kategori", "")
    diagnosis_name = payload.get("diagnosis_name", kategori)
    icd10 = payload.get("icd10_code", "")
    icd9 = payload.get("icd9_code", "")
    current_value = payload.get("current_value", "")
    
    # Get RS and region info (you might need to extract from claim context)
    rs_id = payload.get("rs_id", "rs_notopuro")  # Default or extract from claim
    region_id = payload.get("region_id", "jatim")  # Default or extract from claim
    
    print(f"🏥 Processing regulation for field: {field_name}, diagnosis: {diagnosis_name}")
    
    try:
        # Load multilayer rules for this diagnosis
        multilayer_rules = load_rules_for_diagnosis(
            diagnosis=diagnosis_name or kategori,
            rs_id=rs_id,
            region_id=region_id
        )
        
        print(f"📋 Loaded {multilayer_rules.get('total_rules', 0)} rules from database")
        
        # Check if field needs regulation
        field_rules = multilayer_rules.get("rules", {}).get(field_name, [])
        regulasi_sumber = FIELD_REGULATION_MAP.get(field_name, [])
        
        # If no field-specific rules found in database, generate AI-based rules
        if not field_rules and regulasi_sumber:
            print(f"🤖 No database rules found for {field_name}, generating AI-based rules")
            ai_rules = generate_ai_rules_for_field(
                field_name, diagnosis_name, current_value, regulasi_sumber, 
                rs_id, region_id
            )
            return ai_rules
            
        # If field doesn't need regulation
        if not regulasi_sumber:
            return {
                "status": "success",
                "claim_id": claim_id,
                "field": field_name,
                "data": [],
                "message": f"Field {field_name} tidak memerlukan regulasi khusus"
            }
        
        # Build multilayer response from database rules
        multilayer_response = build_multilayer_response(
            field_rules, field_name, claim_id, diagnosis_name
        )
        
        return multilayer_response
        
    except Exception as e:
        print(f"❌ Error processing regulation detail: {str(e)}")
        return {
            "status": "error",
            "claim_id": claim_id,
            "field": field_name,
            "error": str(e),
            "message": "Gagal memproses regulasi multilayer"
        }

def build_multilayer_response(field_rules: List[Dict], field_name: str, claim_id: int, diagnosis_name: str):
    """
    Build response in multilayer format for frontend tabs
    """
    # Group rules by layer and add metadata
    rules_by_layer = []
    
    for rule in field_rules:
        layer = rule.get("layer", "nasional")
        
        # Build regulation entry
        regulation_entry = {
            "id": f"{layer}_{field_name}_{hash(rule.get('isi', ''))}",
            "layer": layer,
            "field": field_name,
            "judul_regulasi": get_regulation_title(layer, field_name),
            "dasar_hukum": get_dasar_hukum(layer),
            "bab_pasal": rule.get("pasal", f"Pasal terkait {field_name}"),
            "isi": rule.get("isi", "Belum ada aturan spesifik"),
            "sumber": rule.get("sumber", get_default_sumber(layer)),
            "status": "official" if rule.get("rs_specific") or rule.get("region_specific") else "active",
            "tanggal_update": "2024-10-14",  # You might want to get this from database
            "pdf_file": rule.get("pdf_file"),
            "priority": rule.get("priority", LAYER_PRIORITIES.get(layer, 99))
        }
        
        # Add override indicator for RS/PPK rules
        if layer in ["ppk", "rs"]:
            regulation_entry["is_override"] = True
            
        rules_by_layer.append(regulation_entry)
    
    # Sort by priority (lower number = higher priority)
    rules_by_layer.sort(key=lambda x: x.get("priority", 99))
    
    return {
        "status": "success",
        "claim_id": claim_id,
        "field": field_name,
        "diagnosis": diagnosis_name,
        "data": rules_by_layer,
        "total_layers": len(set(rule["layer"] for rule in rules_by_layer)),
        "engine_version": f"regulation_multilayer@{date.today().isoformat()}"
    }

def generate_ai_rules_for_field(field_name: str, diagnosis_name: str, current_value: str, 
                              regulasi_sumber: List[str], rs_id: str, region_id: str):
    """
    Generate AI-based multilayer rules when no database rules exist
    Creates simulated multilayer response based on regulation sources
    """
    try:
        # Create base multilayer structure
        multilayer_rules = []
        
        # Generate rules for each relevant layer based on regulation sources
        for source in regulasi_sumber:
            layer = map_source_to_layer(source)
            
            rule_entry = {
                "id": f"{layer}_{field_name}_{hash(source)}",
                "layer": layer,
                "field": field_name,
                "judul_regulasi": get_regulation_title(layer, field_name),
                "dasar_hukum": get_dasar_hukum(layer, source),
                "bab_pasal": f"Pasal terkait {field_name}",
                "isi": f"Aturan {source} untuk {field_name}: {generate_rule_content(source, field_name, diagnosis_name)}",
                "sumber": get_default_sumber(layer, source),
                "status": "official",
                "tanggal_update": date.today().isoformat(),
                "priority": LAYER_PRIORITIES.get(layer, 99)
            }
            
            multilayer_rules.append(rule_entry)
        
        # Sort by priority
        multilayer_rules.sort(key=lambda x: x.get("priority", 99))
        
        return {
            "status": "success",
            "field": field_name,
            "diagnosis": diagnosis_name,
            "data": multilayer_rules,
            "total_layers": len(multilayer_rules),
            "engine_version": f"regulation_ai_multilayer@{date.today().isoformat()}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "field": field_name,
            "error": str(e),
            "message": "Gagal generate AI multilayer rules"
        }

# Helper functions for multilayer system
def get_regulation_title(layer: str, field_name: str) -> str:
    """Get appropriate regulation title based on layer"""
    titles = {
        "permenkes": f"Permenkes terkait {field_name}",
        "nasional": f"Regulasi Nasional {field_name}",
        "ppk": f"PPK RS terkait {field_name}",
        "regional": f"Regulasi Regional {field_name}",
        "rs": f"Aturan RS Lokal {field_name}",
        "bridging": f"Panduan Teknis Bridging {field_name}",
        "fraud": f"Deteksi Fraud {field_name}",
        "temporary": f"Kebijakan Sementara {field_name}"
    }
    return titles.get(layer, f"Regulasi {field_name}")

def get_dasar_hukum(layer: str, source: str = "") -> str:
    """Get legal basis based on layer"""
    basis = {
        "permenkes": "Permenkes No. 52 Tahun 2016",
        "nasional": "Peraturan Menteri Kesehatan RI",
        "ppk": "Pedoman Praktik Klinis RS",
        "regional": "Surat Edaran BPJS Regional",
        "rs": "Berita Acara/SOP RS Internal",
        "bridging": "Panduan Teknis e-Claim BPJS",
        "fraud": "Sistem Anti-Fraud BPJS",
        "temporary": "Kebijakan Transisi"
    }
    return basis.get(layer, "Regulasi Umum")

def get_default_sumber(layer: str, source: str = "") -> str:
    """Get default source based on layer"""
    sources = {
        "permenkes": "Kemenkes RI",
        "nasional": "BPJS Kesehatan Pusat", 
        "ppk": "RS Notopuro",
        "regional": "BPJS Kesehatan Jawa Timur",
        "rs": "RS Notopuro Internal",
        "bridging": "BPJS Kesehatan - Teknis",
        "fraud": "AI Compliance System",
        "temporary": "Kebijakan Khusus"
    }
    return sources.get(layer, source or "Sumber Regulasi")

def map_source_to_layer(source: str) -> str:
    """Map regulation source to multilayer system"""
    mapping = {
        "Permenkes": "permenkes",
        "PNPK": "nasional",
        "CP": "ppk", 
        "ICD-10": "nasional",
        "ICD-9": "nasional",
        "INA-CBG": "nasional",
        "i-DRG": "nasional",
        "BPJS": "regional",
        "Fornas": "nasional"
    }
    return mapping.get(source, "nasional")

def generate_rule_content(source: str, field_name: str, diagnosis_name: str) -> str:
    """Generate appropriate rule content based on source and field"""
    content_templates = {
        "PNPK": f"Sesuai PNPK {diagnosis_name}, field {field_name} harus memenuhi kriteria klinis standar",
        "CP": f"Clinical Pathway {diagnosis_name} mengatur bahwa {field_name} mengikuti protokol medis",  
        "Permenkes": f"Berdasarkan Permenkes, {field_name} untuk {diagnosis_name} mengikuti standar nasional",
        "ICD-10": f"Kode ICD-10 untuk {field_name} mengikuti struktur WHO classification",
        "ICD-9": f"Prosedur ICD-9 {field_name} sesuai standar international classification",
        "INA-CBG": f"Grouping INA-CBG untuk {field_name} mengikuti casemix Indonesia",
        "BPJS": f"Ketentuan BPJS untuk {field_name} sesuai panduan e-claim"
    }
    return content_templates.get(source, f"Aturan umum untuk {field_name}")
