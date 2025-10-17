# services/idrg_service.py
import os
import re
import json
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI

# Add imports for multilayer rule system
from .rules_loader import load_rules_multilayer, LAYER_PRIORITIES
from .field_rule_mapping import FIELD_RULE_MAP, match_field_alias, FIELD_NAME_ALIAS

# ============================
# Setup
# ============================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================
# Helper functions for rules
# ============================
def load_idrg_rules(diagnosis_name, rs_id=None, region_id=None):
    """
    Load i-DRG specific rules using the multilayer system
    """
    try:
        # Load rules using the multilayer system
        rules = load_rules_multilayer([diagnosis_name], rs_id, region_id)
        
        # Extract i-DRG related fields
        idrg_fields = FIELD_RULE_MAP.get('idrg', {}).keys()
        idrg_rules = {}
        
        # Process each field looking for matches in rules
        for field_name in idrg_fields:
            # Check all possible aliases for this field
            aliases = FIELD_NAME_ALIAS.get(field_name, [field_name])
            
            # Look for this field in rules (using all possible aliases)
            for db_field, rule_data in rules.items():
                if any(db_field.endswith(alias) or db_field == alias for alias in aliases):
                    # We found rules for this field
                    if rule_data and isinstance(rule_data, list) and len(rule_data) > 0:
                        # Get the highest priority rule (first one after sorting)
                        idrg_rules[field_name] = rule_data[0].get('isi', None)
                        idrg_rules[f"{field_name}_source"] = rule_data[0].get('sumber', 'Unknown')
                        idrg_rules[f"{field_name}_layer"] = rule_data[0].get('layer', 'Unknown')
                    break
        
        # Add metadata
        if idrg_rules:
            idrg_rules['diagnosis'] = diagnosis_name
            idrg_rules['sources'] = list(set(value for key, value in idrg_rules.items() if key.endswith('_source')))
            
        return idrg_rules
    except Exception as e:
        print(f"Error loading i-DRG rules: {e}")
        return {}

def format_rule_data(rule_data, field_name):
    """Format rule data to match expected frontend format"""
    # Handle checklist_dokumentasi specifically (as array)
    if field_name == 'checklist_dokumentasi' and isinstance(rule_data, str):
        if '•' in rule_data or '- ' in rule_data:
            # Split by line break and clean up items
            return [line.strip().replace('• ', '').replace('- ', '') for line in rule_data.split('\n') if line.strip()]
        return [rule_data]
    
    # Handle faktor_penentu_severity specifically (as array)
    if field_name == 'faktor_penentu_severity' and isinstance(rule_data, str):
        if '•' in rule_data or '- ' in rule_data:
            # Split by line break and clean up items
            return [line.strip().replace('• ', '').replace('- ', '') for line in rule_data.split('\n') if line.strip()]
        return [rule_data]
        
    # Handle numeric fields (estimasi_tarif_idrg, gap_analysis)
    if field_name in ['estimasi_tarif_idrg', 'gap_analysis'] and isinstance(rule_data, str):
        # Extract numbers from strings like "Rp 5.000.000" -> 5000000
        numeric_str = ''.join(c for c in rule_data if c.isdigit())
        if numeric_str:
            return int(numeric_str)
    
    return rule_data

# ============================
# Prompt builders
# ============================
def build_prompt_single(payload: dict) -> str:
    """
    Membangun prompt untuk prediksi i-DRG diagnosis tunggal
    Enhanced with rule context
    """
    claim_id = payload.get("claim_id")
    diagnosis_name = payload.get("diagnosis_name", "")
    diagnosis_data = payload.get("diagnosis_data", {})
    rs_id = payload.get("rs_id")
    region_id = payload.get("region_id")
    
    # Extract relevant clinical data
    justifikasi = diagnosis_data.get("justifikasi", "")
    bukti_klinis = diagnosis_data.get("bukti_klinis", "")
    tindakan = diagnosis_data.get("tindakan", [])
    tindakan_names = [t.get("nama", "") for t in tindakan if isinstance(t, dict)]
    
    # Get rule data for context
    idrg_rules = load_idrg_rules(diagnosis_name, rs_id, region_id)
    
    # Extract rule context for prompt
    rule_context = ""
    if idrg_rules:
        rule_context = f"""
Rule-based information from official sources ({', '.join(idrg_rules.get('sources', ['Unknown']))}):
- i-DRG Code: {idrg_rules.get('kode_idrg', 'Not found in rules')}
- Severity Index: {idrg_rules.get('severity_index', 'Not found in rules')}
- Documentation Requirements: {idrg_rules.get('checklist_dokumentasi', 'Not found in rules')}
- Severity Factors: {idrg_rules.get('faktor_penentu_severity', 'Not found in rules')}
- Ungroupable Alert: {idrg_rules.get('ungroupable_alert', 'Not found in rules')}
- Estimated Tariff: {idrg_rules.get('estimasi_tarif_idrg', 'Not found in rules')}
- Gap Analysis: {idrg_rules.get('gap_analysis', 'Not found in rules')}
"""
    
    return f"""
Anda adalah sistem prediksi i-DRG Indonesia yang juga memberikan *notifikasi AI* kepada dokter/verifikator.

Data klaim:
- Claim ID: {claim_id}
- Diagnosis utama: {diagnosis_name}
- Justifikasi: {justifikasi}
- Bukti klinis: {bukti_klinis}
- Tindakan terkait: {', '.join(tindakan_names)}

{rule_context}

Tugas Anda:
1. Prediksi i-DRG sesuai aturan resmi (kode, severity, estimasi tarif, dsb)
2. Gunakan rule-based information jika tersedia 
3. Tambahkan notifikasi AI klinis yang bersifat rekomendatif seperti contoh berikut:
   - "Severity konsisten, gap tarif wajar" (🟢 success)
   - "HbA1c tidak tercatat — dokumentasi perlu dilengkapi" (🟡 warning)
   - "Durasi rawat < 3 hari — risiko ungroupable" (🔴 error)

Jawab hanya JSON valid dengan struktur berikut:

{{
  "group_idrg": "Kode resmi i-DRG untuk diagnosis ini. Contoh: I-SEP-2",
  "severity_index": "Angka 1–4 sesuai level severity (1=ringan, 4=sangat berat)",
  "checklist_dokumentasi": [
    "Daftar syarat dokumentasi medis/lab yang wajib dicatat agar klaim valid. Contoh: Kultur darah wajib, LOS ≥ 3 hari"
  ],
  "faktor_penentu_severity": [
    "Faktor utama yang membuat severity = X. Maksimal 3 item. Contoh: LOS 4 hari, prosedur laparoskopi, komplikasi vaskular"
  ],
  "ungroupable_alert": "Alasan klaim bisa gagal grouping. Jika tidak ada, isi '-'",
  "estimasi_tarif_idrg": "Angka rupiah estimasi tarif i-DRG (integer, tanpa Rp atau titik)",
  "gap_analysis": "Selisih tarif i-DRG dengan tarif INA-CBG (angka integer saja)",
  "notification": {{
    "status": "success/warning/error/info",
    "message": "Pesan singkat rekomendasi seperti contoh di atas"
  }}
}}

Aturan tambahan:
- Semua angka harus integer murni.
- Jangan naratif panjang.
- Jika tidak ada data → isi dengan "-".
- Status notifikasi berdasarkan kondisi:
  - success → gap wajar dan severity sesuai
  - warning → data sebagian belum lengkap
  - error → risiko ungroupable atau gap terlalu tinggi
  - info → rekomendasi tambahan umum
"""

def build_prompt_combo(payload: dict) -> str:
    """
    Membangun prompt untuk prediksi i-DRG kombinasi
    Enhanced with rule context
    """
    claim_id = payload.get("claim_id")
    primary_dx = payload.get("primary_diagnosis") or payload.get("primary_claim")
    secondary_dx = payload.get("secondary_diagnosis") or payload.get("secondary_claims", [])
    primary_tx = payload.get("primary_action")
    secondary_tx = payload.get("secondary_actions", [])
    rs_id = payload.get("rs_id")
    region_id = payload.get("region_id")
    
    # Create a unique combo key for rule lookup
    diagnoses = [primary_dx] + (secondary_dx if isinstance(secondary_dx, list) else [])
    combo_key = "+".join([d for d in diagnoses if d])
    
    # Get rule data for both combo key and primary diagnosis
    combo_rules = load_idrg_rules(combo_key, rs_id, region_id)
    primary_rules = {}
    if not combo_rules and primary_dx:
        primary_rules = load_idrg_rules(primary_dx, rs_id, region_id)
    
    # Use best available rules
    idrg_rules = combo_rules or primary_rules
    
    # Extract rule context for prompt
    rule_context = ""
    if idrg_rules:
        rule_context = f"""
Rule-based information from official sources ({', '.join(idrg_rules.get('sources', ['Unknown']))}):
- i-DRG Code: {idrg_rules.get('kode_idrg', 'Not found in rules')}
- Severity Index: {idrg_rules.get('severity_index', 'Not found in rules')}
- Documentation Requirements: {idrg_rules.get('checklist_dokumentasi', 'Not found in rules')}
- Severity Factors: {idrg_rules.get('faktor_penentu_severity', 'Not found in rules')}
- Ungroupable Alert: {idrg_rules.get('ungroupable_alert', 'Not found in rules')}
- Estimated Tariff: {idrg_rules.get('estimasi_tarif_idrg', 'Not found in rules')}
- Gap Analysis: {idrg_rules.get('gap_analysis', 'Not found in rules')}
- Recommendations: {idrg_rules.get('rekomendasi_ai', 'Not found in rules')}
"""
    
    return f"""
Anda adalah sistem prediksi i-DRG Indonesia.

Data kombinasi klaim:
- Claim ID: {claim_id}
- Primary Diagnosis: {primary_dx}
- Secondary Diagnoses: {', '.join(secondary_dx) if secondary_dx else 'None'}
- Primary Procedure: {primary_tx or 'None'}
- Secondary Procedures: {', '.join(secondary_tx) if secondary_tx else 'None'}

{rule_context}

Tugas Anda:
1. Berikan prediksi i-DRG kombinasi sesuai struktur resmi.
2. Gunakan rule-based information jika tersedia untuk prediksi yang akurat.
3. Tambahkan notifikasi AI klinis yang kontekstual seperti:
   - "Severity konsisten, gap tarif wajar" (success)
   - "HbA1c tidak tercatat di rekam medis" (warning)
   - "Gap INA-CBG terlalu tinggi, verifikasi kelengkapan data" (error)

Jawab hanya JSON valid dengan struktur berikut:

{{
  "group_idrg": "Kode resmi i-DRG untuk kombinasi klaim. Contoh: I-SEP-DM-3",
  "severity_index": "Level keparahan kasus 1-4 (1=ringan, 4=sangat berat)",
  "checklist_dokumentasi": [
    "Daftar syarat dokumentasi medis/lab yang wajib dicatat agar klaim valid. Contoh: HbA1c wajib, kultur darah wajib"
  ],
  "faktor_penentu_severity": [
    "Faktor utama yang membuat severity naik/turun. Maksimal 3 item. Contoh: Sepsis + DM, ventilasi mekanik, ICU"
  ],
  "ungroupable_alert": "Alasan klaim bisa gagal grouping. Jika tidak ada, isi '-'",
  "estimasi_tarif_idrg": "Angka rupiah estimasi tarif i-DRG (integer, tanpa Rp atau titik)",
  "gap_analysis": "Selisih tarif i-DRG dengan tarif INA-CBG (angka integer saja)",
  "rekomendasi_ai": "Saran singkat dokumentasi tambahan. Contoh: Tambahkan HbA1c di rekam medis",
  "notification": {{
    "status": "success/warning/error/info",
    "message": "Pesan singkat rekomendasi seperti contoh di atas"
  }}
}}

Aturan tambahan:
- Semua angka harus integer murni.
- Jangan naratif panjang.
- Jika tidak ada data → isi dengan "-".
- Status notifikasi:
  - success → gap wajar dan severity sesuai kombinasi
  - warning → data sebagian belum lengkap
  - error → risiko ungroupable atau selisih besar
  - info → rekomendasi umum tambahan
"""

# ============================
# OpenAI caller
# ============================
def ask_openai(prompt: str) -> dict:
    """
    Fungsi untuk memanggil OpenAI API dan mendapatkan respons
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Anda adalah sistem prediksi i-DRG resmi. Jawab hanya JSON valid."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,  # konsistensi hasil
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error calling OpenAI: {str(e)}")
        raise e

# ============================
# Main functions
# ============================
def predict_idrg(mode: str, payload: dict):
    """
    Prediksi i-DRG berdasarkan mode:
    - mode="single": untuk detail diagnosis individual
    - mode="combo": untuk kombinasi klaim (multiple diagnosis + procedures)
    """
    try:
        if mode == "single":
            return predict_single_idrg(payload)
        elif mode == "combo":
            return predict_combo_idrg(payload)
        else:
            return {"error": f"Invalid mode: {mode}"}
    except Exception as e:
        return {
            "claim_id": payload.get("claim_id", 0),
            "mode": mode,
            "error": str(e),
            "engine_version": f"idrg_service@{date.today().isoformat()}"
        }

def predict_single_idrg(payload: dict):
    """
    Prediksi i-DRG untuk diagnosis tunggal (mode single).
    Enhanced with multilayer rule system.
    """
    claim_id = payload.get("claim_id")
    diagnosis_name = payload.get("diagnosis_name", "")
    rs_id = payload.get("rs_id")
    region_id = payload.get("region_id")
    
    try:
        # First try to get rules from multilayer system
        idrg_rules = load_idrg_rules(diagnosis_name, rs_id, region_id)
        print(f"✅ Found i-DRG rules for {diagnosis_name}: {bool(idrg_rules)}")
        
        # If we have comprehensive rule data, use it directly
        if idrg_rules and all(k in idrg_rules for k in ['kode_idrg', 'severity_index', 'estimasi_tarif_idrg']):
            print(f"✅ Using complete rule data for {diagnosis_name}")
            
            # Format rule data to match expected frontend structure
            formatted_result = {
                "group_idrg": format_rule_data(idrg_rules.get('kode_idrg'), 'kode_idrg') or "-",
                "severity_index": format_rule_data(idrg_rules.get('severity_index'), 'severity_index') or "-",
                "checklist_dokumentasi": format_rule_data(idrg_rules.get('checklist_dokumentasi'), 'checklist_dokumentasi') or [],
                "faktor_penentu_severity": format_rule_data(idrg_rules.get('faktor_penentu_severity'), 'faktor_penentu_severity') or [],
                "ungroupable_alert": format_rule_data(idrg_rules.get('ungroupable_alert'), 'ungroupable_alert') or "-",
                "estimasi_tarif_idrg": format_rule_data(idrg_rules.get('estimasi_tarif_idrg'), 'estimasi_tarif_idrg') or 0,
                "gap_analysis": format_rule_data(idrg_rules.get('gap_analysis'), 'gap_analysis') or 0,
                "rule_sources": idrg_rules.get('sources', []),
                "notifications": {
                    "idrg": {
                        "status": "success",
                        "message": f"Prediksi berdasarkan aturan resmi i-DRG dari {idrg_rules.get('sources', ['database'])[0]}."
                    }
                }
            }
        else:
            # Fall back to AI with rule context
            print(f"⚠️ Incomplete rule data for {diagnosis_name}, using AI with rule context")
            prompt = build_prompt_single(payload)
            result = ask_openai(prompt)
            
            # Integrate any available rule data with AI predictions
            formatted_result = {
                "group_idrg": idrg_rules.get('kode_idrg') or result.get('group_idrg') or "-",
                "severity_index": idrg_rules.get('severity_index') or result.get('severity_index') or "-",
                "checklist_dokumentasi": (
                    format_rule_data(idrg_rules.get('checklist_dokumentasi'), 'checklist_dokumentasi') or 
                    result.get('checklist_dokumentasi') or []
                ),
                "faktor_penentu_severity": (
                    format_rule_data(idrg_rules.get('faktor_penentu_severity'), 'faktor_penentu_severity') or 
                    result.get('faktor_penentu_severity') or []
                ),
                "ungroupable_alert": result.get('ungroupable_alert') or "-",
                "estimasi_tarif_idrg": (
                    format_rule_data(idrg_rules.get('estimasi_tarif_idrg'), 'estimasi_tarif_idrg') or 
                    result.get('estimasi_tarif_idrg') or 0
                ),
                "gap_analysis": (
                    format_rule_data(idrg_rules.get('gap_analysis'), 'gap_analysis') or 
                    result.get('gap_analysis') or 0
                ),
                "notifications": {
                    "idrg": result.get('notification') or {
                        "status": "info",
                        "message": "Prediksi berdasarkan model AI i-DRG."
                    }
                },
                "rule_sources": idrg_rules.get('sources', []),
                "ai_enhanced": True  # Flag indicating AI was used for enhancement
            }
            
        # Return final response
        return {
            "status": "success",
            "mode": "single",
            "claim_id": claim_id,
            "diagnosis": diagnosis_name,
            "idrg_prediction": formatted_result,
            "engine_version": f"idrg_service@{date.today().isoformat()}",
        }
    except Exception as e:
        print(f"❌ Error in predict_single_idrg: {e}")
        return {
            "status": "error",
            "message": str(e),
            "mode": "single",
            "claim_id": claim_id,
            "diagnosis": diagnosis_name,
        }

def predict_combo_idrg(payload: dict):
    """
    Prediksi i-DRG untuk kombinasi diagnosis & tindakan (mode combo).
    Enhanced with multilayer rule system.
    """
    claim_id = payload.get("claim_id")
    primary_dx = payload.get("primary_diagnosis") or payload.get("primary_claim")
    secondary_dx = payload.get("secondary_diagnosis") or payload.get("secondary_claims", [])
    primary_tx = payload.get("primary_action")
    secondary_tx = payload.get("secondary_actions", [])
    rs_id = payload.get("rs_id")
    region_id = payload.get("region_id")

    try:
        # Create a unique combo key for rule lookup
        diagnoses = [primary_dx] + (secondary_dx if isinstance(secondary_dx, list) else [])
        combo_key = "+".join([d for d in diagnoses if d])
        
        # Try to get rules for combo first, then fall back to primary diagnosis
        combo_rules = load_idrg_rules(combo_key, rs_id, region_id)
        primary_rules = {}
        if not combo_rules and primary_dx:
            primary_rules = load_idrg_rules(primary_dx, rs_id, region_id)
        
        # Use best available rules
        idrg_rules = combo_rules or primary_rules
        
        print(f"✅ Found combo rules: {bool(idrg_rules)}")
        
        # If we have comprehensive rule data, use it directly
        if idrg_rules and all(k in idrg_rules for k in ['kode_idrg', 'severity_index', 'estimasi_tarif_idrg']):
            print(f"✅ Using complete rule data for combo")
            
            # Format rule data for frontend
            formatted_result = {
                "group_idrg": format_rule_data(idrg_rules.get('kode_idrg'), 'kode_idrg') or "-",
                "severity_index": format_rule_data(idrg_rules.get('severity_index'), 'severity_index') or "-",
                "checklist_dokumentasi": format_rule_data(idrg_rules.get('checklist_dokumentasi'), 'checklist_dokumentasi') or [],
                "faktor_penentu_severity": format_rule_data(idrg_rules.get('faktor_penentu_severity'), 'faktor_penentu_severity') or [],
                "ungroupable_alert": format_rule_data(idrg_rules.get('ungroupable_alert'), 'ungroupable_alert') or "-",
                "estimasi_tarif_idrg": format_rule_data(idrg_rules.get('estimasi_tarif_idrg'), 'estimasi_tarif_idrg') or 0,
                "gap_analysis": format_rule_data(idrg_rules.get('gap_analysis'), 'gap_analysis') or 0,
                "rekomendasi_ai": format_rule_data(idrg_rules.get('rekomendasi_ai'), 'rekomendasi_ai') or "Tidak ada rekomendasi khusus dari AI untuk kombinasi ini.",
                "rule_sources": idrg_rules.get('sources', []),
                "notifications": {
                    "idrg": {
                        "status": "success",
                        "message": f"Prediksi berdasarkan aturan resmi i-DRG dari {idrg_rules.get('sources', ['database'])[0]}."
                    }
                }
            }
        else:
            # Fall back to AI with rule context
            print(f"⚠️ Incomplete rule data for combo, using AI with rule context")
            prompt = build_prompt_combo(payload)
            result = ask_openai(prompt)
            
            # Integrate any available rule data with AI predictions
            formatted_result = {
                "group_idrg": idrg_rules.get('kode_idrg') or result.get('group_idrg') or "-",
                "severity_index": idrg_rules.get('severity_index') or result.get('severity_index') or "-",
                "checklist_dokumentasi": (
                    format_rule_data(idrg_rules.get('checklist_dokumentasi'), 'checklist_dokumentasi') or 
                    result.get('checklist_dokumentasi') or []
                ),
                "faktor_penentu_severity": (
                    format_rule_data(idrg_rules.get('faktor_penentu_severity'), 'faktor_penentu_severity') or 
                    result.get('faktor_penentu_severity') or []
                ),
                "ungroupable_alert": result.get('ungroupable_alert') or "-",
                "estimasi_tarif_idrg": (
                    format_rule_data(idrg_rules.get('estimasi_tarif_idrg'), 'estimasi_tarif_idrg') or 
                    result.get('estimasi_tarif_idrg') or 0
                ),
                "gap_analysis": (
                    format_rule_data(idrg_rules.get('gap_analysis'), 'gap_analysis') or 
                    result.get('gap_analysis') or 0
                ),
                "rekomendasi_ai": result.get('rekomendasi_ai') or "Tidak ada rekomendasi khusus dari AI untuk kombinasi ini.",
                "notifications": {
                    "idrg": result.get('notification') or {
                        "status": "info",
                        "message": "Prediksi berdasarkan model AI i-DRG."
                    }
                },
                "rule_sources": idrg_rules.get('sources', []),
                "ai_enhanced": True  # Flag indicating AI was used for enhancement
            }

        # Return final response
        return {
            "status": "success",
            "mode": "combo",
            "claim_id": claim_id,
            "primary_diagnosis": primary_dx,
            "secondary_diagnoses": secondary_dx,
            "primary_action": primary_tx,
            "secondary_actions": secondary_tx,
            "idrg_prediction": formatted_result,
            "engine_version": f"idrg_service@{date.today().isoformat()}",
        }

    except Exception as e:
        print(f"❌ Error in predict_combo_idrg: {e}")
        return {
            "status": "error",
            "message": str(e),
            "mode": "combo",
            "claim_id": claim_id,
            "primary_diagnosis": primary_dx,
            "secondary_diagnoses": secondary_dx,
        }