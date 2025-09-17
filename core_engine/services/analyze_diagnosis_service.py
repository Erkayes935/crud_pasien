import os
import json
from pathlib import Path
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_rules():
    """Load ICD mapping rules Indo dari folder rules"""
    rules_path = Path(__file__).parent / "rules" / "icd_mapping.json"
    if rules_path.exists():
        with open(rules_path, encoding="utf-8") as f:
            return json.load(f)
    return {}

def map_to_indo(original_code: str, rules: dict) -> dict:
    """Mapping ICD WHO ke standar Indo pakai rules JSON"""
    return rules.get(original_code, {
        "code_icd": original_code or "-",
        "description": "Deskripsi tidak tersedia",
        "bpjs_tariff_code": None
    })

def process_analyze_diagnosis(data: dict) -> dict:
    """
    Analisis detail diagnosis menggunakan OpenAI + mapping rules Indo.
    Input: { claim_id, disease_name, rekam_medis }
    Output: JSON detail diagnosis lengkap untuk modal
    """

    claim_id = data.get("claim_id")
    disease_name = data.get("disease_name", "Tidak diketahui")
    rekam_medis = data.get("rekam_medis", [])

    # === Prompt dinamis ===
    prompt = f"""
    Berdasarkan data rekam medis berikut:
    {rekam_medis}

    Analisis detail diagnosis untuk penyakit: {disease_name}

    Kembalikan JSON VALID dengan struktur berikut (jangan tambahkan teks lain):

    {{
      "aspek_klinis": {{
        "justifikasi": "Alasan pemilihan diagnosis {disease_name}",
        "bukti": "Ringkasan hasil klinis yang mendukung {disease_name}",
        "syarat": "Syarat minimal diagnosis {disease_name}"
      }},
      "icd10": {{
        "kode": "Kode ICD-10 untuk {disease_name}",
        "struktur_kode": "Struktur kode ICD dari {disease_name}",
        "kode_ganda": "Opsional, jika ada kombinasi",
        "z_code": "Opsional",
        "kode_bpjs_khusus": "Aturan BPJS terkait {disease_name}"
      }},
      "tindakan": [
        {{ "nama": "Tindakan medis 1 terkait {disease_name}", "aturan": "Aturan tindakan 1", "pengaruh_tarif": "Pengaruh tarif INA-CBG" }},
        {{ "nama": "Tindakan medis 2 terkait {disease_name}", "aturan": "Aturan tindakan 2", "pengaruh_tarif": "Pengaruh tarif INA-CBG" }},
        {{ "nama": "Tindakan medis 3 terkait {disease_name}", "aturan": "Opsional, jika ada", "pengaruh_tarif": "Opsional" }}
      ],
      "rawat_inap": {{
        "indikasi": "Kapan perlu rawat inap untuk {disease_name}",
        "lama_rawat": "Durasi rawat inap standar",
        "perpanjangan": "Kondisi perpanjangan"
      }},
      "rujukan": {{
        "syarat": "Syarat rujukan {disease_name}",
        "kelayakan": "Kelayakan rujukan {disease_name}"
      }},
      "faskes": [
        {{ "nama": "Faskes tingkat 1", "aturan": "Kapan bisa ditangani di faskes 1" }},
        {{ "nama": "RS Tipe B", "aturan": "Kapan perlu dirujuk ke faskes tipe B" }}
      ]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Kamu adalah AI medis, jawab HANYA dengan JSON valid."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw_output = response.choices[0].message.content.strip()
        ai_result = json.loads(raw_output)
    except Exception as e:
        print("❌ Error OpenAI analyze_diagnosis:", e)
        ai_result = {
            "aspek_klinis": {"justifikasi": "-", "bukti": "-", "syarat": "-"},
            "icd10": {"kode": "-", "struktur_kode": "-", "kode_ganda": "-", "z_code": "-", "kode_bpjs_khusus": "-"},
            "tindakan": [],
            "rawat_inap": {"indikasi": "-", "lama_rawat": "-", "perpanjangan": "-"},
            "rujukan": {"syarat": "-", "kelayakan": "-"},
            "faskes": []
        }

    # === Mapping ICD ke standar Indo kalau ada rules ===
    rules = load_rules()
    mapped = map_to_indo(ai_result.get("icd10", {}).get("kode"), rules)

    # === Hasil akhir ===
    final_result = {
        "claim_id": claim_id,
        "disease_name": disease_name,
        "aspek_klinis": ai_result.get("aspek_klinis", {}),
        "icd10": {
            "kode": mapped["code_icd"],
            "struktur_kode": ai_result.get("icd10", {}).get("struktur_kode"),
            "kode_ganda": ai_result.get("icd10", {}).get("kode_ganda"),
            "z_code": ai_result.get("icd10", {}).get("z_code"),
            "kode_bpjs_khusus": ai_result.get("icd10", {}).get("kode_bpjs_khusus"),
            "description": mapped["description"],
            "bpjs_tariff_code": mapped.get("bpjs_tariff_code")
        },
        "tindakan": ai_result.get("tindakan", []),
        "rawat_inap": ai_result.get("rawat_inap", {}),
        "rujukan": ai_result.get("rujukan", {}),
        "faskes": ai_result.get("faskes", []),
        "source": "AI+Rule",
        "engine_version": "analyze_diagnosis@2025-09-17"
    }

    return final_result
