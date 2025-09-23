# services/analyze_diagnosis_service.py

import os, json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load API Key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Import rules loader (pastikan file rules_loader.py ada di services/)
from services.rules_loader import (
    icd10_rules, icd9_rules, fornas_rules,
    inacbg_rules, cp_pnpk_rules, load_diagnosis_rule
)

# ==============================
# GPT ANALYZER
# ==============================
def gpt_analyze_diagnosis(disease_name: str, rekam_medis: list):
    """
    Meminta GPT untuk analisis narasi medis + ICD utama
    """
    prompt = f"""
    Anda adalah asisten medis untuk klaim BPJS.
    Analisis diagnosis: {disease_name}
    Rekam Medis: {rekam_medis}

    Output hanya JSON valid dengan struktur:
    {{
      "aspek_klinis": {{
        "justifikasi": "...",
        "bukti": ["..."],
        "syarat_medis": ["..."]
      }},
      "icd10": {{
        "utama": "..."
      }}
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}  # ✅ pastikan JSON valid
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print("❌ Error GPT analyze_diagnosis:", e)
        return {
            "aspek_klinis": {
                "justifikasi": "-",
                "bukti": ["-"],
                "syarat_medis": ["-"]
            },
            "icd10": {"utama": "-"}
        }

# ==============================
# INTEGRATOR GPT + RULES
# ==============================
def process_analyze_diagnosis(input_data: dict) -> dict:
    """
    Analisis detail diagnosis:
    - Narasi dari GPT (aspek_klinis, ICD utama)
    - Validasi dan mapping dengan rules lokal (ICD10, ICD9, CP/PNPK, Fornas, INA-CBG, faskes, dll.)
    """

    claim_id = input_data.get("claim_id")
    disease_name = input_data.get("disease_name", "")
    rekam_medis = input_data.get("rekam_medis", [])

    # --- 1. Ambil rules spesifik diagnosis (misal pneumonia.json, asmabronkial.json, dll.)
    rule_data = load_diagnosis_rule(disease_name)

    # --- 2. Ambil aspek klinis dari rules, fallback ke OpenAI jika kosong
    aspek_klinis = rule_data.get("aspek_klinis", {})
    gpt_result = None
    if not aspek_klinis or not aspek_klinis.get("justifikasi"):
        gpt_result = gpt_analyze_diagnosis(disease_name, rekam_medis)
        aspek_klinis = gpt_result.get("aspek_klinis", aspek_klinis)

    # --- 3. ICD-10, BPJS, catatan BPJS dari rules mapping
    icd_code = aspek_klinis.get("icd10_code") or (gpt_result.get("icd10", {}).get("utama", "") if gpt_result else "")
    icd10_info = icd10_rules.get(icd_code, {
        "who": icd_code,
        "bpjs": icd_code,
        "catatan_bpjs": ""
    })

    # --- 4. Tindakan dari rules CP/PNPK, fallback ke OpenAI jika rules kosong
    tindakan = rule_data.get("tindakan", [])
    if not tindakan and gpt_result:
        tindakan = gpt_result.get("tindakan", [])
    # Format tindakan agar sesuai UI
    tindakan_ui = []
    for t in tindakan:
        if isinstance(t, dict):
            tindakan_ui.append({
                "nama": t.get("nama", "-"),
                "icd9": t.get("icd9", "-"),
                "status": t.get("status", "-"),
                "kategori": t.get("kategori", "-"),
                "regulasi": t.get("regulasi", "-"),
                "fornas": ", ".join(t.get("fornas", [])) if isinstance(t.get("fornas", []), list) else t.get("fornas", "")
            })
        else:
            tindakan_ui.append({"nama": str(t)})

    # --- 5. Fornas, rawat inap, faskes, rujukan, INA-CBG dari rules
    obat_fornas = rule_data.get("fornas", [])
    rawat_inap = rule_data.get("rawat_inap", {})
    faskes = rule_data.get("faskes", {})
    rujukan = rule_data.get("rujukan", {})
    ina_cbg_info = rule_data.get("ina_cbg", {})

    # --- 6. Build response sesuai struktur UI/modal
    result = {
        "kategori": disease_name,
        "justifikasi": aspek_klinis.get("justifikasi", "-"),
        "bukti_klinis": "; ".join(aspek_klinis.get("bukti", [])) if isinstance(aspek_klinis.get("bukti", []), list) else aspek_klinis.get("bukti", "-"),
        "syarat_klinis": "; ".join(aspek_klinis.get("syarat_medis", [])) if isinstance(aspek_klinis.get("syarat_medis", []), list) else aspek_klinis.get("syarat_medis", "-"),
        "icd10_code": icd10_info.get("who", "-"),
        "kode_bpjs_khusus": icd10_info.get("bpjs", "-"),
        "catatan_bpjs": icd10_info.get("catatan_bpjs", "-"),
        "tindakan": tindakan_ui,
        "rawat_inap": {
            "indikasi": "; ".join(rawat_inap.get("indikasi", [])) if isinstance(rawat_inap.get("indikasi", []), list) else rawat_inap.get("indikasi", "-"),
            "lama_rawat": rawat_inap.get("lama_rawat", "-"),
            "perpanjangan": rawat_inap.get("perpanjangan", "-")
        },
        "faskes": {
            "kesesuaian_rs": faskes.get("kesesuaian", faskes.get("level", "-"))
        },
        "rujukan": {
            "syarat": rujukan.get("syarat", "-"),
            "kelayakan": rujukan.get("kelayakan", "-")
        },
        "ina_cbg": ina_cbg_info,
        "source": "AI+Rule",
        "engine_version": "analyze_diagnosis@2025-09-22"
    }
    return result
