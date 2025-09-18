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
      "alternatif": [...],
      "engine_version": "generate_claim_combos@YYYY-MM-DD"
    }
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

    3. Buat minimal 2 alternatif kombinasi (boleh lebih), masing-masing field:
       - judul
       - catatan
       - syarat
       - tindakan (list)

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
      }},
      "alternatif": [
        {{
          "judul": "...",
          "catatan": "...",
          "syarat": "...",
          "tindakan": ["..."]
        }}
      ]
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

    print("==== RAW OUTPUT GENERATE_CLAIM_COMBOS ====")
    print(raw_output)
    print("==========================================")

    try:
        ai_result = json.loads(raw_output)
    except json.JSONDecodeError:
        ai_result = {
            "evaluasi_diagnosis": {},
            "evaluasi_tindakan": {},
            "alternatif": []
        }

    # fallback jika field kosong → isi placeholder
    ai_result.setdefault("evaluasi_diagnosis", {})
    ai_result.setdefault("evaluasi_tindakan", {})
    ai_result.setdefault("alternatif", [])

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

    alts = ai_result["alternatif"]
    fixed_alts = []
    if isinstance(alts, list):
        for alt in alts[:3]:  # batasi max 3 alternatif
            fixed_alts.append({
                "judul": safe_val(alt.get("judul", "")),
                "catatan": safe_val(alt.get("catatan", "")),
                "syarat": safe_val(alt.get("syarat", "")),
                "tindakan": alt.get("tindakan", []) if isinstance(alt.get("tindakan"), list) else []
            })
    ai_result["alternatif"] = fixed_alts or [
        {"judul": "Alternatif 1", "catatan": "-", "syarat": "-", "tindakan": []},
        {"judul": "Alternatif 2", "catatan": "-", "syarat": "-", "tindakan": []}
    ]

    ai_result["engine_version"] = "generate_claim_combos@2025-09-18"
    return ai_result
