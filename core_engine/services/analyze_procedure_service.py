# services/analyze_procedure_service.py
import os, json
from datetime import date
from typing import Any, Dict, List, Optional
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def _sv(x: Any, default: str = "-") -> str:
    return x.strip() if isinstance(x, str) and x.strip() else default

def process_analyze_procedure(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluasi 1 tindakan (ICD-9) untuk modal tindakan (modal di dalam modal).
    Minimal input:
      { "claim_id": 56, "procedure_name": "Ventilasi Mekanik" }

    Opsional:
      { "stage": "admission"|"daily"|"discharge",
        "context": {
           "primary_claim": "Sepsis",
           "secondary_claims": ["ARDS","DM"],
           "primary_action": "Ventilasi Mekanik",
           "secondary_actions": ["Antibiotik IV"],
           "hospital_level": "RS Tipe B",
           "patient_context": "ICU; PaO2/FiO2 150; kultur darah +"
        }
      }

    Output siap render:
      {
        "procedure": "...",
        "icd9_code": "...",
        "icd9_desc": "...",
        "validitas": "...",
        "status_tindakan": "Wajib | Opsional | Minor (+alasan)",
        "ina_cbg_tarif": "...",
        "faskes": "...",
        "rawat_inap": "...",
        "syarat_klinis": "...",
        "engine_version": "analyze_procedure@YYYY-MM-DD"
      }
    """
    claim_id = payload.get("claim_id")
    procedure = payload.get("procedure_name") or payload.get("procedure") or ""
    stage = (payload.get("stage") or "admission").strip()

    # konteks opsional (boleh kosong)
    ctx = payload.get("context") or {}
    dx_pri = ctx.get("primary_claim", "")
    dx_sec = ctx.get("secondary_claims", [])
    act_pri = ctx.get("primary_action", "")
    act_sec = ctx.get("secondary_actions", [])
    hospital_level = ctx.get("hospital_level", "")
    patient_context = ctx.get("patient_context", "")

    prompt = f"""
    Kamu adalah AI coding medis Indonesia (BPJS/INA-CBG).
    Evaluasi tindakan berikut untuk kebutuhan verifikasi klaim.
    TULIS RINGKAS, faktual, dan gunakan bahasa Indonesia.

    # Input minimal
    - Claim ID: {claim_id}
    - Stage: {stage}
    - Tindakan: {procedure}

    # KONTEKS (opsional, mungkin kosong)
    - Diagnosis utama: {dx_pri}
    - Diagnosis sekunder: {dx_sec}
    - Tindakan lain: utama={act_pri}; sekunder={act_sec}
    - Level RS: {hospital_level}
    - Konteks klinis: {patient_context}

    # KELUARAN — WAJIB JSON VALID TANPA TEKS DI LUAR JSON
    {{
      "procedure": "{procedure}",
      "icd9_code": "",            // jika tidak yakin: "-"
      "icd9_desc": "",            // jika tidak yakin: "-"
      "validitas": "",            // apakah match dengan diagnosis + alasan singkat
      "status_tindakan": "",      // Wajib | Opsional | Minor (+alasan singkat)
      "ina_cbg_tarif": "",        // dampak tarif (atau "tidak berpengaruh")
      "faskes": "",               // kecocokan level RS; jika tak relevan: "-"
      "rawat_inap": "",           // ketentuan rawat inap; jika tak relevan: "-"
      "syarat_klinis": ""         // syarat klinis tindakan/indikasi ringkas
    }}

    Aturan:
    - Jangan mengarang kode ICD-9; jika ragu, isi "-".
    - Jika informasi tidak relevan/tersedia, isi "-".
    - Hindari bullet list panjang; kalimat ringkas cukup.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Kamu adalah AI medis. Jawab hanya JSON valid."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )

    raw = (response.choices[0].message.content or "").strip()
    print("==== RAW OUTPUT ANALYZE_PROCEDURE ====")
    print(raw)
    print("======================================")

    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    out = {
        "procedure": _sv(data.get("procedure", procedure), procedure or "-"),
        "icd9_code": _sv(data.get("icd9_code", "")),
        "icd9_desc": _sv(data.get("icd9_desc", "")),
        "validitas": _sv(data.get("validitas", "")),
        "status_tindakan": _sv(data.get("status_tindakan", "")),
        "ina_cbg_tarif": _sv(data.get("ina_cbg_tarif", "")),
        "faskes": _sv(data.get("faskes", "")),
        "rawat_inap": _sv(data.get("rawat_inap", "")),
        "syarat_klinis": _sv(data.get("syarat_klinis", "")),
        "engine_version": f"analyze_procedure@{date.today().isoformat()}",
    }
    return out
