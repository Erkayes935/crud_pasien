# services/regulation_service.py
import os
import json
from datetime import date
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

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

# ---------------------------
# Service utama
# ---------------------------
def process_regulation_detail(payload: dict, field: str):
    claim_id = payload.get("claim_id")
    item_id = payload.get("item_id")
    field_name = field  # save original field name
    
    # Extract any namespaced fields (like idrg_diagnosis_group -> group)
    if "_" in field:
        parts = field.split("_")
        if len(parts) >= 3:
            # Extract the real field name from namespaced fields
            # e.g., idrg_diagnosis_group -> group
            real_field = parts[-1]
            namespace = "_".join(parts[:-1])  # e.g. idrg_diagnosis
            print(f"Extracting field {real_field} from namespaced field {field}")
        else:
            real_field = field
    else:
        real_field = field

    # Set defaults
    kategori = payload.get("kategori", "")
    icd10 = payload.get("icd10_code", "")
    icd9 = payload.get("icd9_code", "")
    current_value = payload.get("current_value", "")
    patient_context = payload.get("patient_context", {})
    
    # Get regulation sources for this field
    regulasi_sumber = FIELD_REGULATION_MAP.get(field, ["PNPK", "Permenkes"])
    
    # If no specific regulation mapping, try with the real field name
    if not regulasi_sumber and real_field != field:
        regulasi_sumber = FIELD_REGULATION_MAP.get(real_field, ["PNPK", "Permenkes"])

    # Load rules lokal
    rules_diagnosis = load_rule_files(kategori)
    rules_global = load_global_rules()

    # Build konteks rules
    context_rules = {
        "diagnosis_rules": rules_diagnosis,
        "global_rules": rules_global,
    }
    
    # Tambahan informasi untuk field i-DRG
    is_idrg = "idrg" in field.lower() or field in [
        "group_idrg", "severity_index", "checklist", "faktor_severity", 
        "ungroupable_alert", "simulasi_tarif", "gap_analysis",
        "group_idrg_kombinasi", "severity_kombinasi", "checklist_kombinasi", 
        "risiko_ungroupable", "estimasi_tarif", "gap_inacbg_vs_idrg"
    ]
    
    idrg_info = ""
    if is_idrg:
        idrg_info = """
        Tambahan untuk konteks i-DRG:
        - i-DRG adalah Indonesian DRG (versi Indonesia dari Diagnosis Related Group)
        - Digunakan untuk grouping casemix dan perhitungan tarif layanan kesehatan
        - Severity level berkisar dari 1 (Minor) hingga 4 (Extreme)
        - Setiap kode i-DRG memiliki standar dokumentasi, length of stay, dan kriteria severity
        """

    # Prompt ke AI
    prompt = f"""
    Kamu adalah asisten regulasi medis Indonesia.

    Konteks klaim pasien:
    - Claim ID: {claim_id}
    - Item ID: {item_id}
    - Diagnosis/Tindakan: {kategori}
    - ICD-10: {icd10}
    - ICD-9: {icd9}
    - Field yang ditekan: {field_name}
    - Nilai field: {current_value}
    - Data pasien: {json.dumps(patient_context, ensure_ascii=False)}
    
    {idrg_info}

    Data rules lokal (hanya sebagai konteks tambahan, JANGAN disalin mentah):
    {json.dumps(context_rules, ensure_ascii=False)}

    Aturan output:
    1. Jawab hanya dalam JSON valid.
    2. Output wajib berisi: dasar_hukum, judul_regulasi, bab_pasal, isi.
    3. "isi" harus berupa LIST poin-poin ringkasan aturan/pasal resmi (angka, syarat, batas nilai).
       - Contoh: ["Kode ICD-10 E11.9 digunakan untuk DM tanpa komplikasi.", "Catatan BPJS: klaim valid untuk terapi standar."]
    4. Jangan pernah menyalin mentah isi rules JSON ke field "isi".
    5. Referensi hanya boleh dari: PNPK, CP, Permenkes, BPJS, ICD-10, ICD-9, INA-CBG, i-DRG.
    6. Jika tidak ada aturan relevan, isi dengan ["-"].

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
            response_format={"type": "json_object"}
        )

        content = resp.choices[0].message.content
        parsed = json.loads(content)
        
        # Ensure isi is a list
        if isinstance(parsed.get("isi"), str):
            parsed["isi"] = [parsed["isi"]]

        result = {
            "status": "success",
            "claim_id": claim_id,
            "field": field_name,
            "data": [parsed],  # Wrap in array to match frontend expectation
            "engine_version": f"regulation_service@{date.today().isoformat()}"
        }
        return result

    except Exception as e:
        return {
            "status": "error",
            "claim_id": claim_id,
            "field": field_name,
            "error": str(e),
            "message": "Gagal memproses regulasi",
            "engine_version": f"regulation_service@{date.today().isoformat()}"
        }
