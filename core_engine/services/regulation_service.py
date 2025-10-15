# services/regulation_service.py
import os
import json
from datetime import date
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
from sqlalchemy.orm import Session
from database_connection import SessionLocal
from models import RulesMaster
from .rules_loader import load_rules_multilayer, get_active_rule_for_field
from .field_rule_mapping import FIELD_NAME_ALIAS, match_field_alias


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
# Field name normalization helpers
# ---------------------------
def normalize_field_name(field_name):
    """
    Normalize frontend field name to match database field names
    Examples: 
    - lama_rawat → rawat_inap.lama_rawat
    - status → status_tindakan
    """
    # Direct mapping for common field name discrepancies
    field_mapping = {
        # Rawat Inap
        "lama_rawat": "rawat_inap.lama_rawat",
        # Tindakan
        "status": "status_tindakan",
        "status_tindakan": "status_tindakan",
        "ina_cbg": "ina_cbg_impact",
        "ina_cbg_impact": "ina_cbg_impact",
        "syarat_klinis_tindakan": "syarat_klinis_tindakan",
        # Faskes
        "tingkat": "faskes_tingkat",
        "justifikasi_faskes": "faskes.justifikasi",
        # Rujukan
        "kriteria_rujukan": "rujukan.kriteria",
        "tujuan": "rujukan.tujuan",
        "indikasi_rujukan": "rujukan.indikasi",
        "indikasi": "indikasi_rujukan",
        # ICD-10 fields
        "struktur_icd10": "icd10.struktur", 
        "kode_ganda": "icd10.kode_ganda",
        "z_code": "icd10.z_code",
        "kode_bpjs_khusus": "icd10.kode_bpjs",
        # ICD-9-CM (procedural)
        "icd9_code": "icd9.kode",
        "icd9_desc": "icd9.deskripsi"
    }
    
    # Return mapped field name if it exists, otherwise return original
    return field_mapping.get(field_name, field_name)

def get_field_aliases(field_name):
    """
    Ambil semua kemungkinan alias field dari FIELD_NAME_ALIAS dan normalized.
    """
    aliases = set()
    
    # 1. Tambahkan field asli
    aliases.add(field_name)
    
    # 2. Alias langsung dari FIELD_NAME_ALIAS
    if field_name in FIELD_NAME_ALIAS:
        aliases.update(FIELD_NAME_ALIAS[field_name])
    
    # 3. Normalized field name
    normalized = normalize_field_name(field_name)
    aliases.add(normalized)
    
    # 4. Jika field berupa path (rawat_inap.lama_rawat), ambil subfield juga
    if '.' in field_name:
        section, subfield = field_name.split('.', 1)
        aliases.add(subfield)
        aliases.add(f"{section}_{subfield}")
        if subfield in FIELD_NAME_ALIAS:
            aliases.update(FIELD_NAME_ALIAS[subfield])
    
    # 5. Jika normalized berupa path, ambil subfield juga
    if '.' in normalized and normalized != field_name:
        section, subfield = normalized.split('.', 1)
        aliases.add(subfield)
        aliases.add(f"{section}_{subfield}")
        if subfield in FIELD_NAME_ALIAS:
            aliases.update(FIELD_NAME_ALIAS[subfield])
    
    # 6. Jika field berisi underscore, coba alternatif
    if '_' in field_name:
        parts = field_name.split('_')
        if len(parts) == 2:
            # indikasi_rujukan -> rujukan.indikasi
            aliases.add(f"{parts[1]}.{parts[0]}")
    
    # 7. Tambahkan kasus khusus
    special_mapping = {
        "indikasi_rujukan": ["rujukan.indikasi", "indikasi", "rujukan_indikasi", "alasan"],
        "kriteria_rujukan": ["rujukan.kriteria", "kriteria", "rujukan_kriteria", "syarat"],
        "tujuan_rujukan": ["rujukan.tujuan", "tujuan", "rujukan_tujuan", "destinasi"],
        "lama_rawat": ["rawat_inap.lama_rawat", "rawat.lama", "los", "length_of_stay"],
        "status_tindakan": ["tindakan.status", "status", "status_prosedur"],
        "icd9_code": ["icd9.kode", "tindakan.kode", "procedure_code"]
    }
    
    if field_name in special_mapping:
        aliases.update(special_mapping[field_name])
    
    # Remove None values
    if None in aliases:
        aliases.remove(None)
        
    return list(aliases)

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

def collect_regulations_for_field(payload: dict, field: str):
    """
    Ambil semua regulasi multilayer dari DB & JSON via rules_loader.py
    untuk field tertentu.
    """
    try:
        diagnosis = payload.get("kategori") or payload.get("diagnosis_name") or "default"
        rs_id = payload.get("rs_id")
        region_id = payload.get("region_id")

        # Get the original field name from payload if provided (frontend might send it)
        original_field = payload.get("original_field", field)
        
        # Get all possible field aliases using the field_rule_mapping
        field_aliases = get_field_aliases(field)
        
        # Log for troubleshooting
        print(f"[REGULATION] Collecting rules for field={field}, diagnosis={diagnosis}")
        print(f"[REGULATION] Field aliases: {field_aliases}")
        print(f"[REGULATION] Context: rs_id={rs_id}, region_id={region_id}")
        
        # Handle empty diagnosis secara eksplisit
        if not diagnosis or diagnosis.strip() == "" or diagnosis == "default":
            return [{
                "layer": "default",
                "sumber": "Informasi",
                "judul_regulasi": "Diagnosis Tidak Terdeteksi",
                "isi": f"Untuk melihat regulasi terkait '{field.replace('_', ' ')}', silakan pilih diagnosis terlebih dahulu.",
                "status": "Info",
                "color": "#9ca3af"
            }]
        
        # Ambil multilayer rules (gabungan semua layer)
        # IMPORTANT: Only try to call load_rules_multilayer if diagnosis is not empty
        all_rules = {}  # Default empty rules
        if diagnosis and diagnosis.strip() != "":
            try:
                all_rules = load_rules_multilayer([diagnosis], rs_id, region_id)
                
                # Debug: show what fields are available in the rules
                if all_rules:
                    print(f"[REGULATION] Available fields in rules: {list(all_rules.keys())}")
            except Exception as rule_err:
                print(f"[REGULATION] Error loading rules: {rule_err}")
                # Continue with empty rules dictionary

        # Try to find matching rules using all field aliases
        rules_for_field = []
        matched_field = None
        
        # PERBAIKAN: Pindah blok ini ke setelah all_rules diinisialisasi
        # First check if any of our aliases match directly
        for alias in field_aliases:
            if alias in all_rules:
                rules_for_field = all_rules[alias]
                matched_field = alias
                print(f"[REGULATION] Found exact match using alias: {alias}")
                break
        
        # If no direct match found, try partial matching
        if not rules_for_field:
            for rule_field in all_rules.keys():
                for alias in field_aliases:
                    if alias in rule_field or rule_field in alias:
                        rules_for_field = all_rules[rule_field]
                        matched_field = rule_field
                        print(f"[REGULATION] Found partial match: alias='{alias}' → field='{rule_field}'")
                        break
                if rules_for_field:
                    break

        # Mapping warna layer (untuk FE)
        LAYER_COLOR = {
            "nasional": "#3b82f6",
            "regional": "#22c55e",
            "rs": "#eab308",
            "bridging": "#a855f7",
            "fraud": "#ef4444",
            "temporary": "#9ca3af"
        }

        formatted = []
        for rule in rules_for_field:
            # Skip if rule is not a dictionary
            if not isinstance(rule, dict):
                continue
                
            formatted.append({
                "layer": rule.get("layer", "nasional"),
                "sumber": rule.get("sumber", "Tidak diketahui"),
                "judul_regulasi": rule.get("judul", field.replace("_", " ").title()),
                "isi": rule.get("isi") or "-",
                "update": str(rule.get("updated_at", ""))[:10] if rule.get("updated_at") else None,
                "status": "Verified (Official)",
                "color": LAYER_COLOR.get(rule.get("layer", "nasional"), "#3b82f6"),
                "tanggal_update": rule.get("updated_at", None)
            })

        # If no rules found, provide a fallback message
        if not formatted:
            formatted = [{
                "layer": "default",
                "sumber": f"Regulasi untuk {original_field}",
                "judul_regulasi": original_field.replace("_", " ").title(),
                "isi": "Tidak ada regulasi spesifik untuk field ini." + 
                       (f" Diagnosis: {diagnosis}" if diagnosis and diagnosis != "default" else "") +
                       f"\n\nField yang dicari: {field}" +
                       (f"\nField yang cocok: {matched_field}" if matched_field else "") +
                       f"\nAlias yang dicoba: {', '.join(field_aliases)}",
                "update": None,
                "status": "Default",
                "color": "#9ca3af",
                "tanggal_update": None
            }]

        return formatted
        
    except Exception as e:
        print(f"[REGULATION] Error in collect_regulations_for_field: {str(e)}")
        # Return error as a regulation item
        return [{
            "layer": "error",
            "sumber": "Error",
            "judul_regulasi": "Error",
            "isi": f"Terjadi kesalahan saat memuat regulasi: {str(e)}",
            "update": None,
            "status": "Error",
            "color": "#ef4444",
            "tanggal_update": None
        }]
    
def get_general_regulations_for_field(field: str):
    """
    Get general regulations for a field without requiring a specific diagnosis.
    Used when no diagnosis is selected.
    """
    field_aliases = get_field_aliases(field)
    db: Session = SessionLocal()
    try:
        # Query general regulations (without diagnosis filter)
        results = []
        
        # Try to find general rules for this field (where diagnosis is null or empty)
        # using all possible aliases
        general_rules = []
        for alias in field_aliases:
            alias_rules = db.query(RulesMaster).filter(
                RulesMaster.field == alias,
                (RulesMaster.diagnosis == None) | (RulesMaster.diagnosis == "")
            ).all()
            
            if alias_rules:
                general_rules.extend(alias_rules)
                print(f"[REGULATION] Found general rules using alias: {alias}")
                # If we found rules for this alias, no need to check others
                break
        
        # If no general rules found, get any rules for the field (up to 5)
        # using all possible aliases
        if not general_rules:
            for alias in field_aliases:
                alias_rules = db.query(RulesMaster).filter(
                    RulesMaster.field == alias
                ).limit(5).all()
                
                if alias_rules:
                    general_rules.extend(alias_rules)
                    print(f"[REGULATION] Found specific rules using alias: {alias}")
                    # If we found rules for this alias, no need to check others
                    break
        
        for rule in general_rules:
            results.append({
                "layer": rule.layer,
                "sumber": rule.sumber or f"Aturan {rule.layer.upper()}",
                "judul_regulasi": field.replace("_", " ").title(),
                "isi": rule.isi,
                "update": rule.updated_at.strftime("%Y-%m-%d") if rule.updated_at else "-",
                "status": rule.status.capitalize() if rule.status else "General",
                "color": get_layer_color(rule.layer),
            })
        
        # If still no rules, provide a default message
        if not results:
            results = [{
                "layer": "default",
                "sumber": "Informasi",
                "judul_regulasi": field.replace("_", " ").title(),
                "isi": (
                    f"Untuk melihat aturan spesifik terkait '{field.replace('_', ' ')}', silakan pilih diagnosis terlebih dahulu.\n\n"
                    f"Field aliases yang dicoba: {', '.join(field_aliases)}"
                ),
                "update": None,
                "status": "Info",
                "color": "#9ca3af",
            }]
            
        return {"status": "success", "data": results}
        
    except Exception as e:
        print(f"[CORE_ENGINE] Error in get_general_regulations_for_field: {e}")
        return {
            "status": "error",
            "message": str(e),
            "data": [{
                "layer": "error",
                "sumber": "Error",
                "judul_regulasi": "Error",
                "isi": f"Terjadi kesalahan saat memuat regulasi umum: {str(e)}",
                "update": None,
                "status": "Error",
                "color": "#ef4444",
            }]
        }
    finally:
        db.close()

# ---------------------------
# Service utama
# ---------------------------
def process_regulation_detail(payload: dict, field: str):
    """
<<<<<<< HEAD
    Ambil aturan multilayer sesuai field yang ditekan user.
    Filter berdasarkan diagnosis (kategori), RS, dan region.
    Urutan prioritas layer: RS > Regional > Nasional > Lainnya.
    """
    try:
        claim_id   = payload.get("claim_id")
        kategori   = payload.get("kategori") or payload.get("diagnosis") or ""
        rs_id      = payload.get("rs_id")
        region_id  = payload.get("region_id")

        # Store the original field name for display in UI
        original_field = field
        
        # Normalize the field name for database lookups
        normalized_field = normalize_field_name(field)
        
        # Get all field aliases for better matching
        field_aliases = get_field_aliases(field)
        
        # Update the payload with both original and normalized field
        payload["original_field"] = original_field
        payload["field"] = normalized_field

        print(f"[CORE_ENGINE] 🔍 process_regulation_detail:")
        print(f"  • Original field: {field}")
        print(f"  • Normalized field: {normalized_field}")
        print(f"  • Field aliases: {field_aliases}")
        print(f"  • Diagnosis: {kategori}, RS: {rs_id}, Region: {region_id}")

        # Skip trying to use load_rules_multilayer if kategori is "Regulasi Umum"
        if kategori == "Regulasi Umum":
            # Just go straight to the database for general regulations
            return get_general_regulations_for_field(normalized_field)

        # First try to get multilayer rules from JSON + DB
        try:
            multilayer_results = collect_regulations_for_field(payload, normalized_field)
            
            # Jika tidak dapat hasil dengan field yang dinormalisasi, coba dengan field asli
            if (not multilayer_results or 
                len(multilayer_results) == 0 or 
                (len(multilayer_results) == 1 and multilayer_results[0].get("layer") == "default")):
                print(f"[CORE_ENGINE] Trying original field: {field}")
                multilayer_results = collect_regulations_for_field(payload, field)
                
            # Jika masih tidak dapat hasil, coba dengan semua alias
            if (not multilayer_results or 
                len(multilayer_results) == 0 or
                (len(multilayer_results) == 1 and multilayer_results[0].get("layer") == "default")):
                for alias in field_aliases:
                    if alias != field and alias != normalized_field:
                        print(f"[CORE_ENGINE] Trying alias: {alias}")
                        alias_results = collect_regulations_for_field(payload, alias)
                        if (alias_results and 
                            len(alias_results) > 0 and
                            alias_results[0].get("layer") != "default"):
                            multilayer_results = alias_results
                            break
                
            if multilayer_results and len(multilayer_results) > 0:
                if multilayer_results[0].get("layer") != "default" or field not in FIELD_REGULATION_MAP:
                    return {"status": "success", "data": multilayer_results}
        except Exception as e:
            print(f"[CORE_ENGINE] Warning: Failed to get multilayer rules: {e}")
            # Continue to fallback DB-only approach

        # Fallback to DB-only approach
        db: Session = SessionLocal()
        try:
            # Get all field aliases to use in the query
            field_aliases = get_field_aliases(normalized_field)
            
            # Create a query for any matching field aliases
            from sqlalchemy import or_
            query_conditions = [RulesMaster.field == alias for alias in field_aliases]
            q = db.query(RulesMaster).filter(or_(*query_conditions))

            # --- Diagnosis filter (optional) ---
            if kategori:
                q = q.filter(RulesMaster.diagnosis.ilike(f"%{kategori}%"))

            # --- Ambil semua dan pisahkan per layer ---
            results = []
            matched_rules = q.all()
            
            print(f"[CORE_ENGINE] Found {len(matched_rules)} rules in database")
            
            for rule in matched_rules:
                # Filter RS dan Region secara dinamis
                if rule.rs_id and rs_id and rule.rs_id.lower() != rs_id.lower():
                    continue
                if rule.region_id and region_id and rule.region_id.lower() != region_id.lower():
                    continue

                results.append({
                    "layer": rule.layer,
                    "sumber": rule.sumber or f"Aturan {rule.layer.upper()}",
                    "dasar_hukum": rule.pdf_file or rule.diagnosis or "-",
                    "isi": rule.isi,
                    "update": rule.updated_at.strftime("%Y-%m-%d") if rule.updated_at else "-",
                    "status": rule.status.capitalize() if rule.status else "Unverified",
                    "color": get_layer_color(rule.layer),
                })

            # Urutkan agar RS > Regional > Nasional > lainnya
            layer_order = ["rs", "regional", "nasional", "permenkes", "ppk", "bridging", "fraud", "temporary", "default"]
            results.sort(key=lambda r: layer_order.index(r["layer"]) if r["layer"] in layer_order else 999)

            if not results:
                results = [{
                    "layer": "default",
                    "sumber": f"Aturan umum untuk field '{original_field}'",
                    "isi": (
                        f"Tidak ada regulasi spesifik untuk field '{original_field}' dan diagnosis '{kategori}'.\n\n"
                        f"Field yang dicari: {normalized_field}\n"
                        f"Alias yang dicoba: {', '.join(field_aliases)}"
                    ),
                    "update": "-",
                    "status": "Default",
                    "color": "#9ca3af",
                }]

            return {"status": "success", "data": results}
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"[CORE_ENGINE] ❌ Error in process_regulation_detail: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "data": [{
                "layer": "error",
                "sumber": "Error",
                "isi": f"Terjadi kesalahan saat memuat regulasi: {str(e)}",
                "update": None,
                "status": "Error",
                "color": "#ef4444",
            }]
        }

def get_layer_color(layer):
    """Helper to get consistent layer colors"""
    LAYER_COLOR = {
        "nasional": "#3b82f6",
        "regional": "#22c55e", 
        "rs": "#eab308",
        "bridging": "#a855f7",
        "fraud": "#ef4444",
        "temporary": "#9ca3af",
        "default": "#9ca3af",
        "error": "#ef4444"
    }
    return LAYER_COLOR.get(layer, "#3b82f6")

# ---------------------------
# Handling untuk berbagai format field
# ---------------------------
def format_rule_content(content):
    """Format rule content berbagai tipe menjadi string yang konsisten"""
    if isinstance(content, list):
        return "\n".join([f"• {item}" for item in content])
    elif isinstance(content, dict):
        if "isi" in content:
            return content["isi"]
        else:
            return "\n".join([f"{k}: {v}" for k, v in content.items()])
    elif content is None:
        return "-"
    else:
        return str(content)