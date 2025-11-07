import os, json
from datetime import date
from openai import OpenAI
from dotenv import load_dotenv
from .rules_loader import load_rules_multilayer
from .field_rule_mapping import FIELD_RULE_MAP, match_field_alias

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================
# 🔹 HELPER
# ============================================================
def _sv(x, default="-"):
    return x.strip() if isinstance(x, str) and x.strip() else default


# ============================================================
# 🔹 LOAD MULTILAYER RULE UNTUK IDRG
# ============================================================
def load_idrg_rules(diagnoses, rs_id=None, region_id=None):
    """Ambil rule multilayer scope=idrg"""
    try:
        return load_rules_multilayer(diagnoses, rs_id=rs_id, region_id=region_id, scope="idrg")
    except Exception as e:
        print(f"[IDRG] ⚠️ Error load multilayer rules: {e}")
        return {}


# ============================================================
# 🔹 HYBRID REASONER (SINGLE DIAGNOSIS MODE)
# ============================================================
def hybrid_reasoner_single(payload: dict) -> dict:
    """
    Mode i-DRG tunggal (modal detail diagnosis).
    Menggabungkan multilayer rules + data klinis klaim.
    """
    diagnosis_name = payload.get("diagnosis_name", "-")
    justifikasi = payload.get("justifikasi", "-")
    bukti_klinis = payload.get("bukti_klinis", "-")
    tindakan_names = payload.get("tindakan_names", [])
    rs_id = payload.get("rs_id")
    region_id = payload.get("region_id")

    multilayer_rules = load_idrg_rules([diagnosis_name], rs_id, region_id)

    # Buat prompt lebih kontekstual & realistis
    ai_prompt = f"""
    Anda adalah verifikator medis BPJS yang bertugas menentukan grouping i-DRG untuk diagnosis {diagnosis_name}.
    Gunakan Pedoman Nasional i-DRG 2025 dan multilayer rules di bawah ini:

    RULE MULTILAYER:
    {json.dumps(multilayer_rules, ensure_ascii=False)[:1500]}

    Data klaim:
    - Diagnosis utama: {diagnosis_name}
    - Justifikasi: {justifikasi}
    - Bukti klinis: {bukti_klinis}
    - Tindakan terkait: {', '.join(tindakan_names) if tindakan_names else '-'}

    Berikan hasil JSON valid dengan struktur:
    {{
      "group_idrg": "Kode & nama grup (mis. E-4-10-I Pneumonia w/o comp.)",
      "severity_index": "Minor / Moderate / Severe (angka 1-4)",
      "checklist_dokumentasi": ["Daftar butir dokumentasi wajib..."],
      "faktor_penentu_severity": ["Faktor severity: komorbid, ventilator, LOS..."],
      "ungroupable_alert": "Alasan jika risiko ungroupable, atau '-' jika aman",
      "estimasi_tarif": "Rp ... (estimasi tarif nasional)",
      "gap_analysis": "Selisih tarif vs INA-CBG (Rp)",
      "notification": {{
        "status": "success / warning / error / info",
        "message": "Kalimat singkat hasil evaluasi, misal:
          - Semua dokumentasi lengkap sesuai CP.
          - Hasil kultur sputum belum dilampirkan.
          - Rawat inap <3 hari, risiko ungroupable."
      }}
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Anda AI medis verifikator BPJS. Jawab hanya JSON valid."},
                {"role": "user", "content": ai_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        ai_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[IDRG_SINGLE] ⚠️ OpenAI error: {e}")
        ai_result = {}

    # Fallback multilayer
    for field in ["kode_idrg", "severity_index", "checklist_dokumentasi", "faktor_penentu_severity",
                  "ungroupable_alert", "estimasi_tarif", "gap_analysis"]:
        if field not in ai_result:
            # ambil rule pertama sesuai field
            for rule_field, ruleset in multilayer_rules.items():
                if match_field_alias(field, rule_field):
                    ai_result[field] = ruleset[0].get("isi", "-")

    ai_result.setdefault("notification", {
        "status": "info",
        "message": "Berdasarkan multilayer i-DRG (fallback rule)."
    })

    ai_result["engine_version"] = f"idrg_single@{date.today().isoformat()}"
    return ai_result


# ============================================================
# 🔹 HYBRID REASONER (COMBO MODE)
# ============================================================
def hybrid_reasoner_combo(payload: dict) -> dict:
    """
    Mode i-DRG kombinasi (panel evaluasi kombinasi).
    """
    primary_diagnosis = payload.get("primary_diagnosis", "-")
    secondary_diagnoses = payload.get("secondary_diagnoses", [])
    primary_action = payload.get("primary_action", "-")
    secondary_actions = payload.get("secondary_actions", [])
    rs_id = payload.get("rs_id")
    region_id = payload.get("region_id")

    diagnoses = [primary_diagnosis] + secondary_diagnoses
    multilayer_rules = load_idrg_rules(diagnoses, rs_id, region_id)

    ai_prompt = f"""
    Anda adalah konsultan medis BPJS yang menilai grouping i-DRG kombinasi kasus.
    Gunakan Pedoman Nasional i-DRG 2025 dan multilayer rules berikut.

    RULE MULTILAYER:
    {json.dumps(multilayer_rules, ensure_ascii=False)[:1800]}

    Data kombinasi klaim:
    - Diagnosis utama: {primary_diagnosis}
    - Diagnosis sekunder: {', '.join(secondary_diagnoses) if secondary_diagnoses else '-'}
    - Tindakan utama: {primary_action}
    - Tindakan sekunder: {', '.join(secondary_actions) if secondary_actions else '-'}

    Hasilkan JSON valid dengan struktur:
    {{
      "group_idrg_kombinasi": "Kode & nama grup (mis. E-4-10-II Pneumonia + DM)",
      "severity_kombinasi": "Minor / Moderate / Severe (angka 1-4)",
      "checklist_kombinasi": ["Checklist dokumen wajib kombinasi"],
      "faktor_severity_kombinasi": ["Faktor severity tambahan (komorbid, ventilasi, LOS)"],
      "risiko_ungroupable": "Deskripsi risiko grouping gagal, atau '-' jika aman.",
      "estimasi_tarif": "Rp ...",
      "gap_vs_cbg": "Selisih tarif INA-CBG vs i-DRG (Rp)",
      "rekomendasi_ai": "Kalimat ringkas rekomendasi medis/verifikasi."
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Anda AI medis verifikator BPJS. Jawab hanya JSON valid."},
                {"role": "user", "content": ai_prompt}
            ],
            temperature=0.35,
            response_format={"type": "json_object"}
        )
        ai_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[IDRG_COMBO] ⚠️ OpenAI error: {e}")
        ai_result = {}

    # Fallback multilayer rules
    for field in ["kode_idrg", "severity_index", "checklist_dokumentasi",
                  "faktor_penentu_severity", "ungroupable_alert", "estimasi_tarif"]:
        for rule_field, ruleset in multilayer_rules.items():
            if match_field_alias(field, rule_field) and field not in ai_result:
                ai_result[field] = ruleset[0].get("isi", "-")

    ai_result.setdefault("rekomendasi_ai", "Evaluasi kombinasi berdasarkan multilayer i-DRG (fallback).")
    ai_result["engine_version"] = f"idrg_combo@{date.today().isoformat()}"
    return ai_result

# ============================================================
# 🔹 ENTRYPOINT UNTUK ROUTER / UI
# ============================================================
def predict_single_idrg(payload: dict) -> dict:
    """
    Endpoint untuk prediksi i-DRG tunggal (modal detail diagnosis).
    """
    try:
        print(f"[PREDICT_SINGLE_IDRG] Running for diagnosis: {payload.get('diagnosis_name')}")
        result = hybrid_reasoner_single(payload)
        return {
            "mode": "single",
            "diagnosis": payload.get("diagnosis_name", "-"),
            "data": result,
            "engine_version": result.get("engine_version", "idrg_single@local")
        }
    except Exception as e:
        print(f"[PREDICT_SINGLE_IDRG] ⚠️ Error: {e}")
        return {
            "mode": "single",
            "diagnosis": payload.get("diagnosis_name", "-"),
            "error": str(e)
        }


def predict_combo_idrg(payload: dict) -> dict:
    """
    Endpoint untuk prediksi i-DRG kombinasi (panel evaluasi kombinasi).
    """
    try:
        print(f"[PREDICT_COMBO_IDRG] Running for combo: {payload.get('primary_diagnosis')} + {payload.get('primary_action')}")
        result = hybrid_reasoner_combo(payload)
        return {
            "mode": "combo",
            "diagnosis_combo": [
                payload.get("primary_diagnosis"),
                *(payload.get("secondary_diagnoses") or [])
            ],
            "action_combo": [
                payload.get("primary_action"),
                *(payload.get("secondary_actions") or [])
            ],
            "data": result,
            "engine_version": result.get("engine_version", "idrg_combo@local")
        }
    except Exception as e:
        print(f"[PREDICT_COMBO_IDRG] ⚠️ Error: {e}")
        return {
            "mode": "combo",
            "error": str(e)
        }

def predict_idrg(payload: dict) -> dict:
    """
    Compatibility wrapper expected by endpoints.py.
    If payload['mode'] == 'combo' -> use combo predictor, else single predictor.
    """
    mode = (payload or {}).get("mode", "single")
    if mode == "combo":
        result = predict_combo_idrg(payload)
    else:
        result = predict_single_idrg(payload)

    # 🔧 Tambahkan wrapper ini
    print("[CORE_ENGINE DEBUG] Final IDRG payload:", json.dumps(result, indent=2, ensure_ascii=False))

    return {
        "status": "success",
        "idrg_prediction": result.get("data", result),  # <--- penting
        "mode": result.get("mode", mode),
        "engine_version": result.get("engine_version", "idrg_service@local")
    }

    print("[CORE_ENGINE DEBUG] Returned to web:", json.dumps({
        "status": "success",
        "idrg_prediction": result.get("data", result),
        "mode": result.get("mode", mode)
    }, indent=2, ensure_ascii=False))

# ============================================================
# 🔹 END OF FILE
