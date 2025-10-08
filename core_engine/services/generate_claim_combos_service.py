# services/generate_claim_combos_service.py
import os
import json
import random
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def process_generate_claim_combos(payload: dict) -> dict:
    """
    Evaluasi kombinasi klaim berdasarkan mapping diagnosis & tindakan.
    Input payload:
    {
      "primary_claim": "string",
      "secondary_claims": ["string", ...],
      "primary_action": "string",
      "secondary_actions": ["string", ...]
    }

    Output format:
    {
      "evaluasi_diagnosis": {...},
      "evaluasi_tindakan": {...},
      "alternatif": [],  # Kosong, akan diisi melalui request terpisah
      "engine_version": "generate_claim_combos@YYYY-MM-DD"
    }
    """
    # Panggil fungsi evaluasi
    evaluation_result = process_generate_evaluations(payload)
    
    # Untuk kompatibilitas, kembalikan struktur lengkap tetapi dengan alternatif kosong
    # Alternatif akan diisi nanti melalui request terpisah
    result = {
        "evaluasi_diagnosis": evaluation_result["evaluasi_diagnosis"],
        "evaluasi_tindakan": evaluation_result["evaluasi_tindakan"],
        "alternatif": [],  # Kosongkan, akan diisi melalui request terpisah
        "engine_version": evaluation_result["engine_version"]
    }
    
    return result

def process_generate_evaluations(payload: dict) -> dict:
    """
    Evaluasi diagnosis dan tindakan saja, tanpa alternatif kombinasi.
    """
    primary_claim = payload.get("primary_claim", "")
    secondary_claims = payload.get("secondary_claims", [])
    primary_action = payload.get("primary_action", "")
    secondary_actions = payload.get("secondary_actions", [])

    prompt = f"""
    Kamu adalah AI medis yang bertugas mengevaluasi kombinasi klaim BPJS/INA-CBG.
    Input berikut:
    - Primary Claim: {primary_claim}
    - Secondary Claims: {secondary_claims}
    - Primary Action: {primary_action}
    - Secondary Actions: {secondary_actions}

    Tugas:
    1. Buat evaluasi diagnosis (7 field):
       - validitas
       - severity
       - kode_cbg
       - estimasi_tarif
       - syarat_klinis
       - evaluasi_faskes
       - rawat_inap

    2. Buat evaluasi tindakan (4 field):
       - wajib
       - validasi
       - dampak
       - konflik

    Keluaran HARUS dalam format JSON valid tanpa teks tambahan di luar JSON.
    Contoh struktur:
    {{
      "evaluasi_diagnosis": {{
        "validitas": "...",
        "severity": "...",
        "kode_cbg": "...",
        "estimasi_tarif": "...",
        "syarat_klinis": "...",
        "evaluasi_faskes": "...",
        "rawat_inap": "..."
      }},
      "evaluasi_tindakan": {{
        "wajib": "...",
        "validasi": "...",
        "dampak": "...",
        "konflik": "..."
      }}
    }}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Kamu adalah AI medis. Jawab hanya JSON valid."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    raw_output = response.choices[0].message.content.strip()

    print("==== RAW OUTPUT GENERATE_CLAIM_EVALUATIONS ====")
    print(raw_output)
    print("==============================================")

    try:
        ai_result = json.loads(raw_output)
    except json.JSONDecodeError:
        ai_result = {
            "evaluasi_diagnosis": {},
            "evaluasi_tindakan": {}
        }

    # fallback jika field kosong → isi placeholder
    ai_result.setdefault("evaluasi_diagnosis", {})
    ai_result.setdefault("evaluasi_tindakan", {})

    def safe_val(val, default="-"):
        return val if isinstance(val, str) and val.strip() else default

    dx = ai_result["evaluasi_diagnosis"]
    ai_result["evaluasi_diagnosis"] = {
        "validitas": safe_val(dx.get("validitas", "")),
        "severity": safe_val(dx.get("severity", "")),
        "kode_cbg": safe_val(dx.get("kode_cbg", "")),
        "estimasi_tarif": safe_val(dx.get("estimasi_tarif", "")),
        "syarat_klinis": safe_val(dx.get("syarat_klinis", "")),
        "evaluasi_faskes": safe_val(dx.get("evaluasi_faskes", "")),
        "rawat_inap": safe_val(dx.get("rawat_inap", ""))
    }

    tdk = ai_result["evaluasi_tindakan"]
    ai_result["evaluasi_tindakan"] = {
        "wajib": safe_val(tdk.get("wajib", "")),
        "validasi": safe_val(tdk.get("validasi", "")),
        "dampak": safe_val(tdk.get("dampak", "")),
        "konflik": safe_val(tdk.get("konflik", ""))
    }

    ai_result["engine_version"] = "generate_claim_evaluations@2025-09-18"
    return ai_result

def process_generate_alternatives(payload: dict) -> dict:
    """
    Fungsi terpisah untuk menghasilkan alternatif kombinasi saja.
    """
    primary_claim = payload.get("primary_claim", "")
    secondary_claims = payload.get("secondary_claims", [])
    primary_action = payload.get("primary_action", "")
    secondary_actions = payload.get("secondary_actions", [])

    prompt = f"""
    Kamu adalah AI medis yang bertugas menghasilkan alternatif kombinasi klaim BPJS/INA-CBG.
    Input berikut:
    - Primary Claim: {primary_claim}
    - Secondary Claims: {secondary_claims}
    - Primary Action: {primary_action}
    - Secondary Actions: {secondary_actions}

    Tugas:
    Buat minimal 2 alternatif kombinasi yang mencakup field berikut:
    - judul: nama singkat alternatif kombinasi (mis. "Sepsis + ARDS")
    - catatan: penjelasan singkat alternatif ini
    - severity: penilaian severity (mis. "Medium (Sepsis + DM)")
    - ina_cbg: kode INA-CBG (mis. "D-04-13")
    - tarif: estimasi tarif dalam rupiah (mis. 12500000)
    - syarat: syarat klinis (mis. "Ventilasi Mekanik + catatan ICU")
    - faskes: evaluasi faskes (mis. "RS Type B")
    - rawat_inap: informasi lama rawat (mis. "≥ 3 hari + ICU ≥ 2 hari")
    - tindakan: array tindakan yang diperlukan (mis. ["Ventilasi Mekanik"])

    Keluaran HARUS dalam format JSON valid tanpa teks tambahan di luar JSON.
    Contoh struktur:
    {
      "alternatif": [
        {
          "judul": "Sepsis + ARDS",
          "catatan": "Kombinasi ini mencakup tindakan operasi dan pemeriksaan penunjang untuk diagnosis yang lebih akurat.",
          "severity": "Medium (Sepsis + DM)",
          "ina_cbg": "D-04-13",
          "tarif": 12500000,
          "syarat": "Ventilasi Mekanik + catatan ICU",
          "faskes": "RS Type B",
          "rawat_inap": "≥ 3 hari + ICU ≥ 2 hari",
          "tindakan": ["Ventilasi Mekanik"]
        }
      ]
    }
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Bisa menggunakan model yang sama
        messages=[
            {"role": "system", "content": "Kamu adalah AI medis. Jawab hanya JSON valid."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5  # Sedikit lebih tinggi untuk variasi alternatif
    )

    raw_output = response.choices[0].message.content.strip()

    print("==== RAW OUTPUT GENERATE_CLAIM_ALTERNATIVES ====")
    print(raw_output)
    print("===============================================")

    try:
        ai_result = json.loads(raw_output)
    except json.JSONDecodeError:
        ai_result = {
            "alternatif": []
        }

    # fallback jika field kosong → isi placeholder
    ai_result.setdefault("alternatif", [])

    def safe_val(val, default="-"):
        return val if isinstance(val, str) and val.strip() else default

    alts = ai_result["alternatif"]
    fixed_alts = []
    if isinstance(alts, list):
        for alt in alts[:3]:  # batasi max 3 alternatif
            fixed_alts.append({
                "judul": safe_val(alt.get("judul", "")),
                "catatan": safe_val(alt.get("catatan", "")),
                "severity": safe_val(alt.get("severity", "")),
                "ina_cbg": safe_val(alt.get("ina_cbg", "")),
                "tarif": alt.get("tarif") if isinstance(alt.get("tarif"), (int, float)) else 0,
                "syarat": safe_val(alt.get("syarat", "")),
                "faskes": safe_val(alt.get("faskes", "")),
                "rawat_inap": safe_val(alt.get("rawat_inap", "")),
                "tindakan": alt.get("tindakan", []) if isinstance(alt.get("tindakan"), list) else []
            })
    
    if not fixed_alts:
        fixed_alts = [
            {
                "judul": "Kombinasi Klaim Apendektomi dengan CT Scan",
                "catatan": "Kombinasi ini mencakup tindakan operasi dan pemeriksaan penunjang untuk diagnosis yang lebih akurat.",
                "severity": "Medium",
                "ina_cbg": "D-04-13",
                "tarif": 12500000,
                "syarat": "Diagnosis utama harus terkonfirmasi, dan CT Scan harus dilakukan sebelum operasi.",
                "faskes": "RS Type B",
                "rawat_inap": "≥ 3 hari + ICU ≥ 2 hari",
                "tindakan": ["Operasi Apendektomi", "CT Scan Abdomen"]
            },
            {
                "judul": "Kombinasi Klaim Apendektomi dengan Komorbid",
                "catatan": "Mempertimbangkan adanya komorbiditas dalam penanganan pasien pasca operasi.",
                "severity": "Medium",
                "ina_cbg": "D-04-13",
                "tarif": 13500000,
                "syarat": "Pasien harus memiliki diagnosis komorbid yang relevan dan terdaftar dalam rekam medis.",
                "faskes": "RS Type B/C",
                "rawat_inap": "≥ 3 hari + ICU ≥ 2 hari",
                "tindakan": ["Operasi Apendektomi"]
            }
        ]

    result = {
        "alternatif": fixed_alts,
        "engine_version": "generate_claim_alternatives@2025-09-18"
    }
    
    return result
