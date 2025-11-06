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
from .rules_loader import load_rules_multilayer, load_rules_for_diagnosis, get_active_rule_for_field
from .field_rule_mapping import FIELD_NAME_ALIAS, match_field_alias
from sqlalchemy import and_, or_


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
        "indikasi": "indikasi_rawat_inap",
        "kriteria": "kriteria_rawat_inap",
        # Tindakan
        "status": "status_tindakan",
        "status_tindakan": "status_tindakan",
        "ina_cbg": "ina_cbg_impact",
        "ina_cbg_impact": "ina_cbg_impact",
        "syarat_klinis_tindakan": "syarat_klinis_tindakan",
        # Faskes
        "tingkat": "faskes_tingkat",
        "justifikasi": "faskes_justifikasi",
        "kompetensi": "faskes_kompetensi",
        # Rujukan
        "indikasi_rujukan": "rujukan_indikasi",
        "kriteria_rujukan": "rujukan_kriteria",
        "tujuan": "rujukan_tujuan",
        "tujuan_rujukan": "rujukan_tujuan",
        # INA-CBG
        "kode": "kode_inacbg",
        "tarif": "tarif_inacbg",
        "deskripsi": "deskripsi_inacbg",
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
    print(f"[ALIAS] Step 1: Added original field '{field_name}'")
    
    # 2. Alias langsung dari FIELD_NAME_ALIAS
    if field_name in FIELD_NAME_ALIAS:
        from_mapping = FIELD_NAME_ALIAS[field_name]
        aliases.update(from_mapping)
        print(f"[ALIAS] Step 2: Found {len(from_mapping)} aliases in FIELD_NAME_ALIAS: {from_mapping}")
    
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
    
    # Remove None values and empty strings
    aliases.discard(None)
    aliases.discard("")
        
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
        diagnosis_name = payload.get("kategori") or payload.get("diagnosis_name") or "default"
        procedure_name = payload.get("procedure_name") or payload.get("procedure") or None
        rs_id = payload.get("rs_id")
        region_id = payload.get("region_id")
        scope = payload.get("scope") or ("tindakan" if procedure_name else "diagnosis")

        print(f"\n[REGULATION] 🔍 ===== collect_regulations_for_field =====")
        print(f"[REGULATION] 🔍 Payload: {payload}")
        print(f"[REGULATION] 🔍 Field: {field}")
        print(f"[REGULATION] 🔍 Diagnosis: {diagnosis_name}")
        print(f"[REGULATION] 🔍 Procedure: {procedure_name}")
        print(f"[REGULATION] 🔍 Scope: {scope}")

        db = SessionLocal()

         # 🔹 Ambil rules berdasarkan kombinasi diagnosis + procedure jika ada
        if procedure_name:
            print(f"[REGULATION] Looking for combined rule: {diagnosis_name} + {procedure_name}")
            print(f"[REGULATION] 🔍 Scope: {scope}, Field: {field}")
            
            # Get field aliases untuk matching yang lebih baik
            field_aliases = get_field_aliases(field)
            print(f"[REGULATION] 🔍 Field aliases: {field_aliases}")
            
            # Query dengan field aliases
            field_conditions = [RulesMaster.field == alias for alias in field_aliases]
            rules = db.query(RulesMaster).filter(
                RulesMaster.diagnosis.ilike(f"%{diagnosis_name}%"),
                RulesMaster.procedure.ilike(f"%{procedure_name}%"),
                or_(*field_conditions),
                RulesMaster.scope == scope,  # ✅ Filter scope!
                RulesMaster.status.in_(["official", "active"])
            ).all()
            
            print(f"[REGULATION] 🔍 Found {len(rules)} rules with procedure filter")
            if rules:
                for r in rules[:3]:
                    print(f"[REGULATION]   - {r.layer}: {r.procedure} | {r.field}")

            # fallback ke procedure-only (tanpa diagnosis) kalau kosong
            if not rules:
                print(f"[REGULATION] No combined rule found, trying procedure-only")
                rules = db.query(RulesMaster).filter(
                    RulesMaster.procedure.ilike(f"%{procedure_name}%"),
                    or_(*field_conditions),  # ✅ Pakai field aliases juga!
                    RulesMaster.scope == scope,  # ✅ Filter scope!
                    RulesMaster.status.in_(["official", "active"])
                ).all()
                print(f"[REGULATION] 🔍 Found {len(rules)} rules with procedure-only")
                if rules:
                    for r in rules[:3]:
                        print(f"[REGULATION]   - {r.layer}: {r.procedure} | {r.field}")
        else:
            # 🔹 Mode diagnosis-only
            field_aliases = get_field_aliases(field)
            print(f"\n[REGULATION] 🔍 ===== SEARCHING FOR FIELD =====")
            print(f"[REGULATION] 🔍 Field requested: '{field}'")
            print(f"[REGULATION] 🔍 Diagnosis: '{diagnosis_name}'")
            print(f"[REGULATION] 🔍 Scope: '{scope}'")
            print(f"[REGULATION] 🔍 Total aliases generated: {len(field_aliases)}")
            print(f"[REGULATION] 🔍 Aliases: {field_aliases}")
            print(f"[REGULATION] 🔍 Is 'kriteria_rawat_inap' in aliases? {'kriteria_rawat_inap' in field_aliases}")
            
            field_conditions = [RulesMaster.field == alias for alias in field_aliases]

            rules = db.query(RulesMaster).filter(
                RulesMaster.diagnosis.ilike(f"%{diagnosis_name}%"),
                or_(*field_conditions),
                RulesMaster.scope == scope,  # ⬅️ penting: filter sesuai scope
                RulesMaster.status.in_(["official", "active"])
            ).all()
            
            print(f"[REGULATION] 🔍 Found {len(rules)} rules with exact OR match")
            if rules:
                for r in rules[:3]:  # Show first 3
                    print(f"[REGULATION] 🔍   - Rule: field={r.field}, layer={r.layer}, diagnosis={r.diagnosis}")
            
            # 🔹 DEBUG: Test query langsung ke database
            if not rules and field == "kriteria":
                # Test 1: Query dengan scope
                test_rules_with_scope = db.query(RulesMaster).filter(
                    RulesMaster.diagnosis.ilike(f"%{diagnosis_name}%"),
                    RulesMaster.field == "kriteria_rawat_inap",
                    RulesMaster.scope == "diagnosis",
                    RulesMaster.status.in_(["official", "active"])
                ).all()
                print(f"[REGULATION] 🔍 DEBUG: Query 'kriteria_rawat_inap' WITH scope filter found {len(test_rules_with_scope)} rules")
                
                # Test 2: Query tanpa scope
                test_rules_no_scope = db.query(RulesMaster).filter(
                    RulesMaster.diagnosis.ilike(f"%{diagnosis_name}%"),
                    RulesMaster.field == "kriteria_rawat_inap",
                    RulesMaster.status.in_(["official", "active"])
                ).all()
                print(f"[REGULATION] 🔍 DEBUG: Query 'kriteria_rawat_inap' WITHOUT scope filter found {len(test_rules_no_scope)} rules")
                
                if test_rules_no_scope:
                    for tr in test_rules_no_scope[:3]:
                        print(f"[REGULATION] 🔍 DEBUG:   - field={tr.field}, scope={tr.scope}, layer={tr.layer}, status={tr.status}")
            
            # 🔹 Fallback: Coba LIKE query jika exact match tidak ada
            if not rules:
                print(f"[REGULATION] 🔍 Trying LIKE query for field aliases...")
                like_conditions = [RulesMaster.field.ilike(f"%{alias}%") for alias in field_aliases]
                rules = db.query(RulesMaster).filter(
                    RulesMaster.diagnosis.ilike(f"%{diagnosis_name}%"),
                    or_(*like_conditions),
                    RulesMaster.scope == scope,
                    RulesMaster.status.in_(["official", "active"])
                ).all()
                print(f"[REGULATION] 🔍 Found {len(rules)} rules with LIKE query")

            if not rules and field.startswith("syarat_klinis"):
                # Fallback hanya untuk diagnosis
                rules = db.query(RulesMaster).filter(
                    RulesMaster.diagnosis.ilike(f"%{diagnosis_name}%"),
                    RulesMaster.field == "syarat_klinis",
                    RulesMaster.scope == "diagnosis",
                    RulesMaster.status.in_(["official", "active"])
                ).all()

        db.close()

        # 🔹 Format output multilayer (warna, sumber, dll)
        formatted = []
        if rules:
            for rule in rules:
                formatted.append({
                    "layer": rule.layer,
                    "sumber": rule.sumber,
                    "judul_regulasi": f"{rule.layer.upper()} {field.replace('_', ' ').title()}",
                    "isi": rule.isi,
                    "status": "Verified (Official)",
                    "color": {
                        "nasional": "#3b82f6",
                        "ppk": "#60a5fa",
                        "rs": "#eab308",
                        "bridging": "#a855f7",
                        "fraud": "#ef4444",
                        "temporary": "#9ca3af"
                    }.get(rule.layer, "#3b82f6")
                })

        # 🔹 fallback info
        if not formatted:
            diagnosis_label = (
                f"{diagnosis_name} + {procedure_name}" if procedure_name else diagnosis_name
            )
            field_aliases_str = ', '.join(get_field_aliases(field))
            formatted = [{
                "layer": "default",
                "sumber": f"Aturan umum untuk field '{field}'",
                "judul_regulasi": f"Detail Regulasi: {field}",
                "isi": (
                    f"Tidak ada regulasi spesifik untuk field '{field}' dan diagnosis '{diagnosis_label}'.\n\n"
                    f"Field yang dicari: {field}\n"
                    f"Alias yang dicoba: {field_aliases_str}\n"
                    f"Scope: {scope}"
                ),
                "status": "Default",
                "color": "#9ca3af"
            }]

        return formatted

    except Exception as e:
        print(f"[REGULATION] Error in collect_regulations_for_field: {e}")
        return [{
            "layer": "error",
            "sumber": "Error",
            "judul_regulasi": "Error",
            "isi": f"Terjadi kesalahan saat memuat regulasi: {str(e)}",
            "status": "Error",
            "color": "#ef4444"
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
    Ambil aturan multilayer sesuai field yang ditekan user.
    Filter berdasarkan diagnosis (kategori), RS, dan region.
    Urutan prioritas layer: RS > Regional > Nasional > Lainnya.
    """
    try:
        claim_id   = payload.get("claim_id")
        kategori   = payload.get("kategori") or payload.get("diagnosis") or ""
        procedure_name = payload.get("procedure_name") or payload.get("procedure") or ""
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
        print(f"  • Diagnosis: {kategori}, Procedure: {procedure_name}, RS: {rs_id}, Region: {region_id}")

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
            
            # --- Procedure filter (optional) ---
            if procedure_name:
                q = q.filter(RulesMaster.procedure.ilike(f"%{procedure_name}%"))
                print(f"[CORE_ENGINE] 🔍 Filtering by procedure: {procedure_name}")
            
            # --- Scope filter (important!) ---
            scope = payload.get("scope")
            if scope:
                q = q.filter(RulesMaster.scope == scope)
                print(f"[CORE_ENGINE] 🔍 Filtering by scope: {scope}")

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
                    "judul_regulasi": rule.pdf_file or f"{rule.layer.upper()} - {rule.diagnosis}" or "-",
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