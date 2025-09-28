# services/regulation_service.py
import os
import json
from datetime import date
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------
# Mapping field → regulasi
# ---------------------------
FIELD_REGULATION_MAP = {
    "justifikasi": ["PNPK", "CP", "Permenkes"],
    "bukti_klinis": [],
    "syarat_klinis": ["PNPK", "CP", "Permenkes"],
    "confidence_ai": [],

    "icd10_code": ["ICD-10 WHO", "Mapping BPJS"],
    "kode_ganda": ["ICD-10 WHO"],
    "z_code": ["ICD-10 WHO"],
    "kode_bpjs_khusus": ["Aturan BPJS e-Claim"],

    "syarat_klinis_tindakan": ["PNPK", "CP", "BPJS"],
    "status_tindakan": ["INA-CBG", "CP"],
    "ina_cbg_impact": ["INA-CBG Casemix"],

    "indikasi_rawat": ["PNPK", "CP"],
    "lama_rawat": ["PNPK", "INA-CBG"],
    "perpanjangan_rawat": ["PNPK", "INA-CBG"],

    "kesesuaian_rs": ["Permenkes RS", "INA-CBG"],

    "syarat_rujukan": ["Permenkes Rujukan", "INA-CBG"],
    "kelayakan_rujukan": ["Permenkes Rujukan"],

    "icd9_code": ["ICD-9-CM resmi"],
    "icd9_desc": ["ICD-9-CM resmi"],
    "validitas_tindakan": [],
    "status_tindakan_proc": ["CP", "INA-CBG"],
    "tarif": ["INA-CBG Casemix"],
    "faskes_proc": ["Permenkes RS"],
    "rawat_inap_proc": ["PNPK", "INA-CBG"],
    "syarat_klinis_proc": ["PNPK", "CP"],

    "validitas_kombinasi": ["PNPK", "CP"],
    "severity": ["INA-CBG Casemix"],
    "kode_ina_cbg": ["INA-CBG resmi"],
    "estimasi_tarif": [],
    "syarat_klinis_kombinasi": ["PNPK", "CP"],
    "evaluasi_faskes": ["Permenkes RS", "INA-CBG"],
    "rawat_inap_eval": ["PNPK", "INA-CBG"],

    "tindakan_wajib_kombinasi": ["PNPK", "INA-CBG"],
    "validasi_verifikator": [],
    "dampak_tarif": ["INA-CBG"],
    "konflik_duplikasi": ["INA-CBG", "CP"],
}

# ---------------------------
# Service utama
# ---------------------------
def process_regulation_detail(payload: dict, field: str):
    claim_id = payload.get("claim_id")
    context_type = payload.get("context_type", "")
    kategori = payload.get("kategori", "")
    icd10 = payload.get("icd10_code")
    icd9 = payload.get("icd9_code")
    current_value = payload.get("current_value", "")
    patient_context = payload.get("patient_context", {})

    regulasi_sumber = FIELD_REGULATION_MAP.get(field, ["PNPK", "Permenkes"])

    # 📝 Prompt ketat dengan aturan output
    prompt = f"""
    Kamu adalah asisten regulasi medis Indonesia.

    Konteks klaim pasien:
    - Claim ID: {claim_id}
    - Context: {context_type}
    - Diagnosis/Tindakan: {kategori}
    - ICD-10: {icd10}
    - ICD-9: {icd9}
    - Field yang ditekan: {field}
    - Nilai field: {current_value}
    - Data pasien: {patient_context}

    Aturan output:
    1. Jawab hanya dalam JSON valid.
    2. Output wajib berisi: dasar_hukum, judul_regulasi, bab_pasal, isi.
    3. "isi" harus memuat poin-poin aturan/kriteria eksplisit (angka, syarat, batas nilai).
    4. Referensi hanya boleh dari: PNPK, CP, Permenkes, BPJS, ICD-10, ICD-9, INA-CBG.
    5. Jika tidak ada aturan relevan, isi dengan "-".

    Jawablah sesuai dasar regulasi: {', '.join(regulasi_sumber) if regulasi_sumber else '-'}.
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Kamu hanya menjawab dengan regulasi resmi Indonesia. Jangan beropini."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}  # ⬅️ hasil pasti JSON valid
        )

        # ambil hasil dan parse ke dict
        content = resp.choices[0].message.content
        parsed = json.loads(content)

        result = {
            "claim_id": claim_id,
            "field": field,
            "regulasi": parsed,  # sudah dict, bukan string lagi
            "engine_version": f"regulation_service@{date.today().isoformat()}"
        }
        return result

    except Exception as e:
        return {
            "claim_id": claim_id,
            "field": field,
            "error": str(e),
            "engine_version": f"regulation_service@{date.today().isoformat()}"
        }
