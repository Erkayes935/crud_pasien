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
    Evaluasi diagnosis dan tindakan kombinasi + notifikasi AI.
    """
    primary_claim = payload.get("primary_claim", "")
    secondary_claims = payload.get("secondary_claims", [])
    primary_action = payload.get("primary_action", "")
    secondary_actions = payload.get("secondary_actions", [])

    prompt = f"""
    Kamu adalah AI medis yang bertugas mengevaluasi kombinasi klaim BPJS/INA-CBG.
    Input:
    - Primary Claim: {primary_claim}
    - Secondary Claims: {secondary_claims}
    - Primary Action: {primary_action}
    - Secondary Actions: {secondary_actions}

    Tugas:
    1. Buat evaluasi kombinasi DIAGNOSIS (7 field) dengan notifikasi AI.
        {{
          "validitas": "Apakah kombinasi diagnosis valid menurut CP/PNPK",
          "severity": "Level keparahan kombinasi (Rendah/Sedang/Tinggi/Sangat Tinggi)",
          "kode_cbg": "Kode INA-CBG sesuai kombinasi",
          "estimasi_tarif": "Estimasi tarif (Rp ...)",
          "syarat_klinis": "Syarat klinis utama (mis. HbA1c + kultur darah)",
          "evaluasi_faskes": "Tipe RS minimal (mis. RS Type B)",
          "rawat_inap": "Durasi minimal rawat (mis. 3 hari)",
          "notification": {{
             "status": "success/warning/error/info",
             "message": "Rekomendasi AI klinis, misalnya: 'DM tipe 2 + Pneumonia → tidak valid menurut CP'"
          }}
        }}

    2. Buat evaluasi kombinasi TINDAKAN (4 field) dengan notifikasi AI.
        {{
          "wajib": "Tindakan wajib kombinasi (mis. Sepsis + ARDS valid)",
          "validasi": "Validasi pilihan verifikator (mis. Ventilasi Mekanik → wajib untuk sepsis berat)",
          "dampak": "Dampak terhadap INA-CBG / tarif (mis. Rp 12.500.000, Severity High)",
          "konflik": "Konflik atau duplikasi tindakan (mis. Infus IV tercatat ganda)",
          "notification": {{
             "status": "success/warning/error/info",
             "message": "Rekomendasi AI, misalnya: 'Ventilator 96.72 memerlukan rawat inap ≥3 hari'"
          }}
        }}

    Aturan tambahan:
    - Jawab hanya JSON valid, tanpa teks lain.
    - Gunakan gaya ringkas, tidak naratif panjang.
    - 'status' notifikasi:
        - success → kombinasi valid dan konsisten dengan CP
        - warning → perlu justifikasi tambahan atau data belum lengkap
        - error → kombinasi tidak sesuai CP / INA-CBG
        - info → tidak berpengaruh terhadap tarif klaim

    Contoh singkat:
    {{
      "evaluasi_diagnosis": {{
        "validitas": "Sepsis + DM valid (komorbid umum)",
        "severity": "Medium (Sepsis + DM)",
        "kode_cbg": "D-04-12",
        "estimasi_tarif": "Rp 7.500.000",
        "syarat_klinis": "HbA1c + kultur darah",
        "evaluasi_faskes": "Minimal RS Tipe B",
        "rawat_inap": "Minimal 3 hari rawat",
        "notification": {{
          "status": "error",
          "message": "DM tipe 2 + Pneumonia → tidak valid menurut CP"
        }}
      }},
      "evaluasi_tindakan": {{
        "wajib": "Sepsis + ARDS → kombinasi lazim, valid",
        "validasi": "Ventilasi Mekanik → wajib untuk pasien sepsis berat",
        "dampak": "Sepsis + ARDS + Ventilasi Mekanik → Severity High, Rp 12.500.000",
        "konflik": "Infus IV tercatat ganda → tidak pengaruh tarif",
        "notification": {{
          "status": "warning",
          "message": "Ventilator 96.72 memerlukan rawat inap ≥3 hari"
        }}
      }}
    }}
    """

    # ===================== CALL OPENAI =====================
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Kamu adalah AI medis. Jawab hanya JSON valid."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    raw_output = response.choices[0].message.content.strip()

    print("==== RAW OUTPUT GENERATE_CLAIM_EVALUATIONS ====")
    print(raw_output)
    print("==============================================")
    
    # ===================== PARSE JSON =====================
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
        "rawat_inap": safe_val(dx.get("rawat_inap", "")),
        "notification": dx.get("notification", {"status": "info", "message": "Belum ada notifikasi AI"})
    }

    tdk = ai_result["evaluasi_tindakan"]
    ai_result["evaluasi_tindakan"] = {
        "wajib": safe_val(tdk.get("wajib", "")),
        "validasi": safe_val(tdk.get("validasi", "")),
        "dampak": safe_val(tdk.get("dampak", "")),
        "konflik": safe_val(tdk.get("konflik", "")),
        "notification": tdk.get("notification", {"status": "info", "message": "Belum ada notifikasi AI"})
    }

    ai_result["engine_version"] = "generate_claim_evaluations@2025-10-10"
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
