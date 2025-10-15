# services/generate_claim_combos_service.py
import os
import json
import random
from openai import OpenAI

# 🔹 Integrasi tambahan
from .rules_loader import load_rules_multilayer
from .field_rule_mapping import FIELD_RULE_MAP

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================
# 🔹 FUNGSI UTAMA KOMBINASI KLAIM
# ============================================================
def process_generate_claim_combos(payload: dict) -> dict:
    """
    Evaluasi kombinasi klaim berdasarkan mapping diagnosis & tindakan.
    """
    evaluation_result = process_generate_evaluations(payload)

    # Tetap jaga struktur lama
    result = {
        "evaluasi_diagnosis": evaluation_result["evaluasi_diagnosis"],
        "evaluasi_tindakan": evaluation_result["evaluasi_tindakan"],
        "alternatif": [],  # akan diisi lewat request terpisah
        "engine_version": evaluation_result["engine_version"]
    }
    return result


# ============================================================
# 🔹 EVALUASI KOMBINASI (RULE-BASED + AI REPHRASER)
# ============================================================
def process_generate_evaluations(payload: dict) -> dict:
    """
    Evaluasi diagnosis dan tindakan kombinasi + notifikasi AI.
    Sekarang sudah berbasis multilayer rule DB + JSON.
    """
    primary_claim = payload.get("primary_claim", "")
    secondary_claims = payload.get("secondary_claims", [])
    primary_action = payload.get("primary_action", "")
    secondary_actions = payload.get("secondary_actions", [])
    rs_id = payload.get("rs_id")
    region_id = payload.get("region_id")

    # ==========================================
    # 1️⃣ Ambil multilayer rules
    # ==========================================
    diagnoses = [primary_claim] + secondary_claims
    try:
        multilayer_rules = load_rules_multilayer(diagnoses, rs_id, region_id)
    except Exception as e:
        multilayer_rules = {}
        print(f"[WARN] Gagal load multilayer rules: {e}")

    def get_rule_text(field_key: str) -> str:
        """Ambil isi rule aktif dari multilayer hasil merge DB"""
        for rule_field, rule_list in multilayer_rules.items():
            if rule_field.endswith(field_key):
                isi = rule_list[0].get("isi")
                sumber = rule_list[0].get("sumber", "")
                if isi:
                    return f"{isi} ({sumber})"
        return ""

    # ==========================================
    # 2️⃣ Bentuk hasil rule-based mentah
    # ==========================================
    raw_eval_diagnosis = {
        "validitas": get_rule_text("validitas") or "Valid kombinasi diagnosis berdasarkan aturan RS.",
        "severity": get_rule_text("severity") or "Moderate (default rule).",
        "kode_cbg": get_rule_text("kode_icd") or "E-4-10",
        "estimasi_tarif": get_rule_text("tarif") or "Rp 4.800.000",
        "syarat_klinis": get_rule_text("syarat_klinis") or "SpO₂ < 90%, Rontgen infiltrat.",
        "evaluasi_faskes": get_rule_text("faskes.kewenangan") or "RS C – sesuai kewenangan.",
        "rawat_inap": get_rule_text("rawat_inap.lama_rawat") or "LOS ≥ 3 hari (valid)."
    }

    raw_eval_tindakan = {
        "wajib": get_rule_text("tindakan.status") or "Ventilasi Mekanik wajib untuk pneumonia berat.",
        "validasi": get_rule_text("tindakan.validasi") or "Disetujui menurut CP/PNPK.",
        "dampak": get_rule_text("tarif") or "Meningkatkan severity (naik 15%).",
        "konflik": get_rule_text("fraud") or "Tidak ada konflik atau duplikasi tindakan."
    }

    # ==========================================
    # 3️⃣ Compose dengan AI agar bahasanya rapi
    # ==========================================
    try:
        rules_context = json.dumps(multilayer_rules, ensure_ascii=False)[:1500]
        ai_prompt = f"""
        Kamu adalah AI medis yang bertugas menyusun ringkasan evaluasi kombinasi klaim BPJS/INA-CBG.
        Gunakan aturan multilayer berikut sebagai dasar penyusunan hasil (CP/PNPK/RS/Regional):
        {rules_context}

        Input:
        - Primary Claim: {primary_claim}
        - Secondary Claims: {secondary_claims}
        - Primary Action: {primary_action}
        - Secondary Actions: {secondary_actions}

        Tulis ulang hasil rule berikut menjadi kalimat yang rapi tapi tetap faktual:
        Diagnosis: {json.dumps(raw_eval_diagnosis, ensure_ascii=False)}
        Tindakan: {json.dumps(raw_eval_tindakan, ensure_ascii=False)}

        Keluaran berupa JSON:
        {{
          "evaluasi_diagnosis": {{"message": "..."}},
          "evaluasi_tindakan": {{"message": "..."}}
        }}
        """
        ai_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Kamu AI medis verifikator, jaga format JSON valid."},
                {"role": "user", "content": ai_prompt}
            ],
            temperature=0.2
        )
        ai_json = ai_resp.choices[0].message.content.strip()
        ai_summary = json.loads(ai_json)
        dx_note = ai_summary.get("evaluasi_diagnosis", {}).get("message", "")
        tdk_note = ai_summary.get("evaluasi_tindakan", {}).get("message", "")
    except Exception as e:
        dx_note = f"AI phrasing gagal: {e}"
        tdk_note = dx_note

    # ==========================================
    # 4️⃣ Bentuk struktur final (kompatibel dengan UI lama)
    # ==========================================
    evaluasi_diagnosis = raw_eval_diagnosis.copy()
    evaluasi_tindakan = raw_eval_tindakan.copy()

    evaluasi_diagnosis["notification"] = {
        "status": "info",
        "message": dx_note or "Hasil berdasarkan multilayer rule (AI phrasing)."
    }
    evaluasi_tindakan["notification"] = {
        "status": "info",
        "message": tdk_note or "Hasil berdasarkan multilayer rule (AI phrasing)."
    }

    return {
        "evaluasi_diagnosis": evaluasi_diagnosis,
        "evaluasi_tindakan": evaluasi_tindakan,
        "engine_version": "generate_claim_combos@2025-10-14"
    }


# ============================================================
# 🔹 ALTERNATIF KOMBINASI (MASIH AI-BASED)
# ============================================================
def process_generate_alternatives(payload: dict) -> dict:
    """
    Fungsi terpisah untuk menghasilkan alternatif kombinasi saja.
    Tetap berbasis AI (simulasi what-if).
    """
    primary_claim = payload.get("primary_claim", "")
    secondary_claims = payload.get("secondary_claims", [])
    primary_action = payload.get("primary_action", "")
    secondary_actions = payload.get("secondary_actions", [])

    prompt = f"""
    Kamu adalah AI medis yang bertugas menghasilkan alternatif kombinasi klaim BPJS/INA-CBG.
    Input:
    - Primary Claim: {primary_claim}
    - Secondary Claims: {secondary_claims}
    - Primary Action: {primary_action}
    - Secondary Actions: {secondary_actions}

    Buat minimal 2 alternatif kombinasi valid (berdasarkan CP/PNPK/RS/Regional)
    dengan struktur JSON:
    - judul: nama singkat alternatif kombinasi (mis. "Sepsis + ARDS")
    - catatan: penjelasan singkat alternatif ini
    - severity: penilaian severity (mis. "Medium (Sepsis + DM)")
    - ina_cbg: kode INA-CBG (mis. "D-04-13")
    - tarif: estimasi tarif dalam rupiah (mis. 12500000)
    - syarat: syarat klinis (mis. "Ventilasi Mekanik + catatan ICU")
    - faskes: evaluasi faskes (mis. "RS Type B")
    - rawat_inap: informasi lama rawat (mis. "≥ 3 hari + ICU ≥ 2 hari")
    - tindakan: array tindakan yang diperlukan (mis. ["Ventilasi Mekanik"])
    - notification: harus berisi kalimat evaluatif singkat (maks 2 kalimat)

    Keluaran HARUS dalam format JSON valid tanpa teks tambahan di luar JSON.
    Contoh struktur:
    {{
      "alternatif": [
        {{
          "judul": "string",
          "catatan": "string",
          "severity": "string",
          "ina_cbg": "string",
          "tarif": 0,
          "syarat": "string",
          "faskes": "string",
          "rawat_inap": "string",
          "tindakan": ["string", ...],
          "notification": {{
             "status": "success/warning/info",
             "message": "catatan AI"
          }}
        }}
      ]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Kamu AI medis. Jawab hanya JSON valid."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        raw_output = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] Gagal generate alternatif: {e}")
        raw_output = "{}"

    print("==== RAW OUTPUT GENERATE_CLAIM_ALTERNATIVES ====")
    print(raw_output)
    print("===============================================")

    try:
        ai_result = json.loads(raw_output)
    except json.JSONDecodeError:
        ai_result = {"alternatif": []}

    ai_result.setdefault("alternatif", [])

    def safe_val(val, default="-"):
        return val if isinstance(val, str) and val.strip() else default

    alts = ai_result["alternatif"]
    fixed_alts = []
    if isinstance(alts, list):
        for alt in alts[:3]:
            fixed_alts.append({
                "judul": safe_val(alt.get("judul", "")),
                "catatan": safe_val(alt.get("catatan", "")),
                "severity": safe_val(alt.get("severity", "")),
                "ina_cbg": safe_val(alt.get("ina_cbg", "")),
                "tarif": alt.get("tarif") if isinstance(alt.get("tarif"), (int, float)) else 0,
                "syarat": safe_val(alt.get("syarat", "")),
                "faskes": safe_val(alt.get("faskes", "")),
                "rawat_inap": safe_val(alt.get("rawat_inap", "")),
                "tindakan": alt.get("tindakan", []) if isinstance(alt.get("tindakan"), list) else [],
                "notification": alt.get("notification", {
                    "status": "info",
                    "message": "AI suggestion (simulasi alternatif klaim)."
                })
            })
    
    if not fixed_alts:
        # fallback default tetap ada
        fixed_alts = [
            {
                "judul": "Kombinasi Klaim Apendektomi dengan CT Scan",
                "catatan": "Kombinasi ini mencakup tindakan operasi dan pemeriksaan penunjang.",
                "severity": "Medium",
                "ina_cbg": "D-04-13",
                "tarif": 12500000,
                "syarat": "Diagnosis utama harus terkonfirmasi.",
                "faskes": "RS Type B",
                "rawat_inap": "≥ 3 hari",
                "tindakan": ["Operasi Apendektomi", "CT Scan Abdomen"],
                "notification": {"status": "info", "message": "Contoh fallback default."}
            },
            {
                "judul": "Kombinasi Klaim Apendektomi dengan Komorbid",
                "catatan": "Mempertimbangkan adanya komorbiditas pasca operasi.",
                "severity": "Medium",
                "ina_cbg": "D-04-13",
                "tarif": 13500000,
                "syarat": "Pasien memiliki diagnosis komorbid relevan.",
                "faskes": "RS Type B/C",
                "rawat_inap": "≥ 3 hari",
                "tindakan": ["Operasi Apendektomi"],
                "notification": {"status": "info", "message": "Contoh fallback default."}
            }
        ]

    result = {
        "alternatif": fixed_alts,
        "engine_version": "generate_claim_alternatives@2025-10-14"
    }
    return result
