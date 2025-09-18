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

    # --- 1. Ambil hasil GPT (narasi klinis + ICD utama)
    gpt_result = gpt_analyze_diagnosis(disease_name, rekam_medis)
    aspek_klinis = gpt_result.get("aspek_klinis", {})

    # --- 2. Mapping ICD utama ke rules lokal
    icd_code = gpt_result.get("icd10", {}).get("utama", "")
    icd10_info = icd10_rules.get(icd_code, {
        "who": icd_code,
        "bpjs": icd_code,
        "catatan_bpjs": ""
    })

    # --- 3. Ambil tindakan dari CP/PNPK rules
    tindakan = []
    for t in cp_pnpk_rules.get(disease_name, []):
        icd9_code = icd9_rules.get(t, None)
        tindakan_item = {
            "nama": t,
            "icd9": icd9_code,
            "status": "wajib" if "Antibiotik" in t or "X-ray" in t else "opsional"
        }
        if icd9_code is None:
            tindakan_item["catatan"] = "Terapi obat, tidak ada kode ICD-9 (cek Fornas)"
        tindakan.append(tindakan_item)

    # --- 4. Ambil obat Fornas
    obat_fornas = fornas_rules.get(disease_name, [])

    # --- 5. Ambil tarif INA-CBG
    ina_cbg_info = {}
    for k, v in inacbg_rules.items():
        if disease_name.lower() in v["deskripsi"].lower():
            ina_cbg_info = v.copy()
            ina_cbg_info["kode"] = k
            break

    # --- 6. Ambil tambahan rules spesifik diagnosis (misal pneumonia.json, asmabronkial.json, dll.)
    rule_data = load_diagnosis_rule(disease_name)

    # --- 7. Merge semua hasil
    return {
        "claim_id": claim_id,
        "disease_name": disease_name,
        "aspek_klinis": aspek_klinis or rule_data.get("aspek_klinis", {}),
        "icd10": icd10_info,
        "tindakan": tindakan or rule_data.get("tindakan", []),
        "fornas": obat_fornas,
        "rawat_inap": rule_data.get("rawat_inap", {}),
        "faskes": rule_data.get("faskes", {}),
        "rujukan": rule_data.get("rujukan", {}),
        "ina_cbg": ina_cbg_info,
        "source": "AI+Rule",
        "engine_version": "analyze_diagnosis@2025-09-17"
    }
