# services/idrg_service.py
import os
import re
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
Anda adalah sistem prediksi i-DRG Indonesia yang juga memberikan *notifikasi AI* kepada dokter/verifikator.

Data klaim:
- Claim ID: {claim_id}
- Diagnosis utama: {diagnosis_name}
- Justifikasi: {justifikasi}
- Bukti klinis: {bukti_klinis}
- Tindakan terkait: {', '.join(tindakan_names)}

Tugas Anda:
1. Prediksi i-DRG sesuai aturan resmi (kode, severity, estimasi tarif, dsb)
2. Tambahkan notifikasi AI klinis yang bersifat rekomendatif seperti contoh berikut:
   - "Severity konsisten, gap tarif wajar" (🟢 success)
   - "HbA1c tidak tercatat — dokumentasi perlu dilengkapi" (🟡 warning)
   - "Durasi rawat < 3 hari — risiko ungroupable" (🔴 error)

Jawab hanya JSON valid dengan struktur berikut:

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
  "gap_analysis": "Selisih tarif i-DRG dengan tarif INA-CBG (angka integer saja)",
  "notification": {{
    "status": "success/warning/error/info",
    "message": "Pesan singkat rekomendasi seperti contoh di atas"
  }}
}}

Aturan tambahan:
- Semua angka harus integer murni.
- Jangan naratif panjang.
- Jika tidak ada data → isi dengan "-".
- Status notifikasi berdasarkan kondisi:
  - success → gap wajar dan severity sesuai
  - warning → data sebagian belum lengkap
  - error → risiko ungroupable atau gap terlalu tinggi
  - info → rekomendasi tambahan umum
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

Tugas Anda:
1. Berikan prediksi i-DRG kombinasi sesuai struktur resmi.
2. Tambahkan notifikasi AI klinis yang kontekstual seperti:
   - "Severity konsisten, gap tarif wajar" (success)
   - "HbA1c tidak tercatat di rekam medis" (warning)
   - "Gap INA-CBG terlalu tinggi, verifikasi kelengkapan data" (error)

Jawab hanya JSON valid.
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
  "rekomendasi_ai": "Saran singkat dokumentasi tambahan. Contoh: Tambahkan HbA1c di rekam medis",
  "notification": {{
    "status": "success/warning/error/info",
    "message": "Pesan singkat rekomendasi seperti contoh di atas"
  }}
}}

Aturan tambahan:
- Semua angka harus integer murni.
- Jangan naratif panjang.
- Jika tidak ada data → isi dengan "-".
- Status notifikasi:
  - success → gap wajar dan severity sesuai kombinasi
  - warning → data sebagian belum lengkap
  - error → risiko ungroupable atau selisih besar
  - info → rekomendasi umum tambahan
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
    claim_id = payload.get("claim_id")
    diagnosis_name = payload.get("diagnosis_name", "")

    try:
        prompt = build_prompt_single(payload)
        result = ask_openai(prompt)

        # Normalize field names for consistency
        formatted_result = {
            "group_idrg": result.get("group_idrg") or result.get("kode_idrg") or "-",
            "severity_index": result.get("severity_index") or "-",
            "checklist_dokumentasi": result.get("checklist_dokumentasi") or [],
            "faktor_penentu_severity": result.get("faktor_penentu_severity") or [],
            "ungroupable_alert": result.get("ungroupable_alert") or "-",
            "estimasi_tarif_idrg": result.get("estimasi_tarif_idrg") or result.get("estimasi_tarif") or 0,
            "gap_analysis": result.get("gap_analysis") or 0,
            "notifications": {
                "idrg": result.get("notification") or {
                    "status": "info",
                    "message": "Belum ada notifikasi untuk bagian IDRG."
                }
            },
        }

        return {
            "status": "success",
            "mode": "single",
            "claim_id": claim_id,
            "diagnosis": diagnosis_name,
            "idrg_prediction": formatted_result,
            "engine_version": f"idrg_service@{date.today().isoformat()}",
        }
    except Exception as e:
        print(f"❌ Error in predict_single_idrg: {e}")
        return {
            "status": "error",
            "message": str(e),
            "mode": "single",
            "claim_id": claim_id,
            "diagnosis": diagnosis_name,
        }

def predict_combo_idrg(payload: dict):
    """
    Prediksi i-DRG untuk kombinasi diagnosis & tindakan (mode combo).
    Hasil diformat agar cocok dengan FE (claim.modals.js) + menambahkan field rekomendasi_ai.
    """
    claim_id = payload.get("claim_id")
    primary_dx = payload.get("primary_diagnosis") or payload.get("primary_claim")
    secondary_dx = payload.get("secondary_diagnosis") or payload.get("secondary_claims", [])
    primary_tx = payload.get("primary_action")
    secondary_tx = payload.get("secondary_actions", [])

    try:
        # 🔹 Build prompt & panggil OpenAI (sesuai logikamu sebelumnya)
        prompt = build_prompt_combo(payload)
        result = ask_openai(prompt)

        # 🔹 Format hasil sesuai FE
        formatted_result = {
            "group_idrg": result.get("kode_idrg") or result.get("group_idrg") or "-",
            "severity_index": result.get("severity_index") or "-",
            "checklist_dokumentasi": result.get("checklist_dokumentasi") or [],
            "faktor_penentu_severity": result.get("faktor_penentu_severity") or [],
            "ungroupable_alert": result.get("ungroupable_alert") or "-",
            "estimasi_tarif_idrg": (
                result.get("estimasi_tarif_idrg")
                or result.get("estimasi_tarif")
                or 0
            ),
            "gap_analysis": result.get("gap_analysis") or 0,

            # 🧠 Tambahan field rekomendasi AI
            "rekomendasi_ai": result.get("rekomendasi_ai")
                or result.get("ai_recommendation")
                or result.get("ai_summary")
                or "Tidak ada rekomendasi khusus dari AI untuk kombinasi ini.",

            # 🔔 Notifikasi
            "notifications": result.get("notifications") or {
                "idrg": {
                    "status": "info",
                    "message": "Belum ada notifikasi untuk bagian IDRG kombinasi."
                }
            },
        }

        # 🔹 Return response akhir
        return {
            "status": "success",
            "mode": "combo",
            "claim_id": claim_id,
            "primary_diagnosis": primary_dx,
            "secondary_diagnoses": secondary_dx,
            "primary_action": primary_tx,
            "secondary_actions": secondary_tx,
            "idrg_prediction": formatted_result,
            "engine_version": f"idrg_service@{date.today().isoformat()}",
        }

    except Exception as e:
        print(f"❌ Error in predict_combo_idrg: {e}")
        return {
            "status": "error",
            "message": str(e),
            "mode": "combo",
            "claim_id": claim_id,
            "primary_diagnosis": primary_dx,
            "secondary_diagnoses": secondary_dx,
        }