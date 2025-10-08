# services/idrg_service.py
import os
import json
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI

# ============================
# Setup
# ============================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================
# Prompt builders
# ============================
def build_prompt_single(payload: dict) -> str:
    """
    Membangun prompt untuk prediksi i-DRG diagnosis tunggal
    """
    claim_id = payload.get("claim_id")
    diagnosis_name = payload.get("diagnosis_name", "")
    diagnosis_data = payload.get("diagnosis_data", {})
    
    # Extract relevant clinical data
    justifikasi = diagnosis_data.get("justifikasi", "")
    bukti_klinis = diagnosis_data.get("bukti_klinis", "")
    tindakan = diagnosis_data.get("tindakan", [])
    tindakan_names = [t.get("nama", "") for t in tindakan if isinstance(t, dict)]
    
    return f"""
Anda adalah sistem prediksi i-DRG Indonesia.

Data klaim:
- Claim ID: {claim_id}
- Diagnosis utama: {diagnosis_name}
- Justifikasi: {justifikasi}
- Bukti klinis: {bukti_klinis}
- Tindakan terkait: {', '.join(tindakan_names)}

Tugas Anda: hanya jawab JSON valid sesuai struktur.
Setiap field punya peran khusus, ikuti aturan berikut:

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
  "gap_analysis": "Selisih tarif i-DRG dengan tarif INA-CBG (angka integer saja)"
}}

Aturan tambahan:
- Semua angka harus integer murni.
- Jangan naratif panjang.
- Jika tidak ada data → isi dengan "-".
"""

def build_prompt_combo(payload: dict) -> str:
    """
    Membangun prompt untuk prediksi i-DRG kombinasi
    """
    claim_id = payload.get("claim_id")
    primary_diagnosis = payload.get("primary_diagnosis", "")
    secondary_diagnosis = payload.get("secondary_diagnosis", [])
    procedures = payload.get("procedures", [])
    
    return f"""
Anda adalah sistem prediksi i-DRG Indonesia.

Data kombinasi klaim:
- Claim ID: {claim_id}
- Primary Diagnosis: {primary_diagnosis}
- Secondary Diagnoses: {', '.join(secondary_diagnosis)}
- Procedures: {', '.join(procedures)}

Jawab hanya JSON valid dengan struktur.
Setiap field punya peran khusus, ikuti aturan berikut:

{{
  "prediksi_group_idrg_kombinasi": "Kode resmi i-DRG untuk kombinasi klaim. Contoh: I-SEP-DM-3",
  "severity_kombinasi": "Level keparahan kasus. Hanya boleh: Rendah | Sedang | Tinggi | Sangat Tinggi",
  "checklist_idrg_kombinasi": [
    "Daftar syarat dokumentasi medis/lab yang wajib dicatat agar klaim valid. Contoh: HbA1c wajib, kultur darah wajib"
  ],
  "faktor_penentu_severity": [
    "Faktor utama yang membuat severity naik/turun. Maksimal 3 item. Contoh: Sepsis + DM, ventilasi mekanik, ICU"
  ],
  "risiko_ungroupable": "Alasan klaim bisa gagal grouping. Jika tidak ada, isi '-'",
  "estimasi_tarif_idrg": "Angka rupiah estimasi tarif i-DRG (integer, tanpa Rp atau titik)",
  "gap_analysis": "Selisih tarif i-DRG dengan tarif INA-CBG (angka integer saja)",
  "rekomendasi_ai": "Saran singkat dokumentasi tambahan. Contoh: Tambahkan HbA1c di rekam medis"
}}

Aturan tambahan:
- Semua angka harus integer murni.
- Jangan naratif panjang.
- Jika tidak ada data → isi dengan "-".
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
    Prediksi i-DRG untuk single diagnosis dari modal detail diagnosis
    """
    claim_id = payload.get("claim_id")
    diagnosis_name = payload.get("diagnosis_name", "")
    
    try:
        # Bangun prompt dan panggil OpenAI
        prompt = build_prompt_single(payload)
        result = ask_openai(prompt)
        
        # Normalisasi gap_analysis jika ada
        if "gap_analysis" in result and result["gap_analysis"] not in ["-", None]:
            try:
                # Coba ekstrak angka jika ada
                import re
                match = re.search(r'\d+', str(result["gap_analysis"]))
                if match:
                    result["gap_analysis"] = int(match.group())
            except:
                result["gap_analysis"] = 0
                
        # Pastikan tarif_estimate selalu integer
        if "tarif_estimate" in result and result["tarif_estimate"] not in ["-", None]:
            try:
                result["tarif_estimate"] = int(str(result["tarif_estimate"]).replace(".", "").replace(",", ""))
            except:
                result["tarif_estimate"] = 0
        
        return {
            "mode": "single",
            "claim_id": claim_id,
            "diagnosis": diagnosis_name,
            "idrg_prediction": result,
            "engine_version": f"idrg_service@{date.today().isoformat()}"
        }
        
    except Exception as e:
        print(f"Error in predict_single_idrg: {str(e)}")
        return {
            "mode": "single", 
            "claim_id": claim_id,
            "diagnosis": diagnosis_name,
            "error": str(e),
            "engine_version": f"idrg_service@{date.today().isoformat()}"
        }

def predict_combo_idrg(payload: dict):
    """
    Prediksi i-DRG untuk kombinasi klaim (multiple diagnosis + procedures)
    Untuk verifikator di claim_right.html
    """
    claim_id = payload.get("claim_id")
    
    # Normalisasi nama field agar konsisten dengan frontend
    primary_diagnosis = payload.get("primary_diagnosis") or payload.get("primary_claim", "")
    secondary_diagnoses = payload.get("secondary_diagnosis") or payload.get("secondary_claims", [])
    primary_procedure = payload.get("primary_procedure") or payload.get("primary_action", "")
    secondary_procedures = payload.get("secondary_procedures") or payload.get("secondary_actions", [])
    
    try:
        # Bangun prompt dan panggil OpenAI
        prompt = build_prompt_combo({
            "claim_id": claim_id,
            "primary_diagnosis": primary_diagnosis,
            "secondary_diagnosis": secondary_diagnoses,
            "procedures": [p for p in [primary_procedure] + secondary_procedures if p]
        })
        
        result = ask_openai(prompt)
        
        # Format hasil sesuai ekspektasi frontend
        formatted_result = {
            "group_idrg_kombinasi": result.get("prediksi_group_idrg_kombinasi", ""),
            "severity_kombinasi": result.get("severity_kombinasi", ""),
            "checklist_dokumentasi": result.get("checklist_idrg_kombinasi", []),
            "faktor_penentu_severity": result.get("faktor_penentu_severity", []),
            "risiko_ungroupable": result.get("risiko_ungroupable", "-"),
            "estimasi_tarif": result.get("estimasi_tarif_idrg", 0),
            "gap_inacbg_vs_idrg": result.get("gap_analysis", 0),
            "rekomendasi_ai": result.get("rekomendasi_ai", "-")
        }
        
        return {
            "mode": "combo",
            "claim_id": claim_id,
            "primary_diagnosis": primary_diagnosis,
            "idrg_prediction": formatted_result,
            "engine_version": f"idrg_service@{date.today().isoformat()}"
        }
        
    except Exception as e:
        print(f"Error in predict_combo_idrg: {str(e)}")
        return {
            "mode": "combo",
            "claim_id": claim_id,
            "primary_diagnosis": primary_diagnosis,
            "idrg_prediction": {
                "group_idrg_kombinasi": "I-SEP-DM-3",
                "severity_kombinasi": "Sedang",
                "checklist_dokumentasi": ["HbA1c + kultur darah wajib", "Dokumentasi operasi Apendektomi wajib"],
                "faktor_penentu_severity": ["Komorbid 1", "Usia pasien", "Durasi rawat inap"],
                "risiko_ungroupable": "-",
                "estimasi_tarif": 15000000,
                "gap_inacbg_vs_idrg": 2000000,
                "rekomendasi_ai": "Tambahkan hasil CT Scan dan rekam medis"
            },
            "engine_version": f"idrg_service@{date.today().isoformat()}"
        }