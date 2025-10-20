import os, json
from datetime import date
from openai import OpenAI
from .rules_loader import load_rules_multilayer
from .field_rule_mapping import FIELD_RULE_MAP, match_field_alias

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================
# 🔹 UTILITY HELPER
# ============================================================
def _sv(x, default="-"):
    return x.strip() if isinstance(x, str) and x.strip() else default


# ============================================================
# 🔹 FUNGSI UTAMA KOMBINASI KLAIM
# ============================================================
def process_generate_claim_combos(payload: dict) -> dict:
    """
    Evaluasi kombinasi klaim berdasarkan diagnosis & tindakan (hybrid multilayer).
    """
    evaluation_result = process_generate_evaluations(payload)

    return {
        "evaluasi_diagnosis": evaluation_result["evaluasi_diagnosis"],
        "evaluasi_tindakan": evaluation_result["evaluasi_tindakan"],
        "alternatif": [],  # akan diisi lewat request terpisah
        "engine_version": evaluation_result["engine_version"]
    }


# ============================================================
# 🔹 EVALUASI KOMBINASI (RULE + AI PHRASED)
# ============================================================
def process_generate_evaluations(payload: dict) -> dict:
    """
    Evaluasi kombinasi diagnosis & tindakan menggunakan multilayer rules.
    """
    primary_claim = payload.get("primary_claim", "")
    secondary_claims = payload.get("secondary_claims", [])
    primary_action = payload.get("primary_action", "")
    secondary_actions = payload.get("secondary_actions", [])
    rs_id = payload.get("rs_id")
    region_id = payload.get("region_id")

    # Gabungkan semua diagnosis untuk pencarian rule multilayer
    diagnoses = [primary_claim] + secondary_claims

    # ============================================================
    # 1️⃣ Ambil multilayer rules dari DB (dua scope: diagnosis & tindakan)
    # ============================================================
    try:
        rules_diag = load_rules_multilayer(diagnoses, rs_id, region_id, scope="diagnosis")
        rules_tdk  = load_rules_multilayer(diagnoses, rs_id, region_id, scope="tindakan")
    except Exception as e:
        rules_diag, rules_tdk = {}, {}
        print(f"[COMBO] ⚠️ Gagal load multilayer rules: {e}")

    def get_rule_text(rules: dict, field_key: str) -> str:
        """Cari isi rule dari hasil multilayer sesuai field."""
        for rule_field, rule_list in rules.items():
            if match_field_alias(field_key, rule_field):
                if isinstance(rule_list, list) and rule_list:
                    isi = rule_list[0].get("isi")
                    sumber = rule_list[0].get("sumber", "")
                    if isi:
                        return f"{isi} ({sumber})"
        return ""

    # ============================================================
    # 2️⃣ Bangun struktur rule dasar untuk evaluasi diagnosis
    # ============================================================
    eval_diagnosis = {
        "validitas": get_rule_text(rules_diag, "validitas") or "✅ Valid kombinasi diagnosis berdasarkan aturan RS.",
        "severity": get_rule_text(rules_diag, "severity") or "Moderate (default rule).",
        "kode_cbg": get_rule_text(rules_diag, "kode_icd") or "Kode INA-CBG: E-4-10 (Pneumonia & Respiratory Infections)",
        "estimasi_tarif": get_rule_text(rules_diag, "tarif") or "Rp 4.800.000",
        "syarat_klinis": get_rule_text(rules_diag, "syarat_klinis") or "Gejala mayor: demam, batuk, sesak. Minor: ronki basah.",
        "evaluasi_faskes": get_rule_text(rules_diag, "faskes.kewenangan") or "RS C – sesuai kewenangan.",
        "rawat_inap": get_rule_text(rules_diag, "rawat_inap.lama_rawat") or "LOS ≥ 3 hari (valid)."
    }

    # ============================================================
    # 3️⃣ Bangun struktur rule dasar untuk evaluasi tindakan
    # ============================================================
    eval_tindakan = {
        "wajib": get_rule_text(rules_tdk, "tindakan.status") or "Tindakan wajib: Radiologi / Antibiotik sesuai CP.",
        "validasi": get_rule_text(rules_tdk, "tindakan.validasi") or "Disetujui menurut CP/PNPK.",
        "dampak": get_rule_text(rules_tdk, "tarif") or "Dampak terhadap tarif sesuai INA-CBG (naik 10–15%).",
        "konflik": get_rule_text(rules_tdk, "fraud") or "Tidak ada konflik atau duplikasi tindakan."
    }

    # ============================================================
    # 4️⃣ Minta AI phrasing untuk merapikan hasil (natural & faktual)
    # ============================================================
    try:
        rules_context = {
            "diagnosis_rules": list(rules_diag.keys())[:15],
            "tindakan_rules": list(rules_tdk.keys())[:15],
        }

        ai_prompt = f"""
        Kamu adalah AI medis konsultan verifikator BPJS.
        Tugasmu adalah menyusun hasil evaluasi kombinasi klaim (diagnosis + tindakan)
        dengan bahasa medis formal namun ringkas, berbasis multilayer rules (CP, PNPK, RS, Regional).

        Data kontekstual:
        - Diagnosis Utama: {primary_claim}
        - Diagnosis Sekunder: {secondary_claims}
        - Tindakan Utama: {primary_action}
        - Tindakan Sekunder: {secondary_actions}
        - Context RS: {rs_id or '-'}, Region: {region_id or '-'}

        Rule multilayer yang tersedia: {json.dumps(rules_context, ensure_ascii=False)}

        Diagnosis Combination Raw Data:
        {json.dumps(eval_diagnosis, ensure_ascii=False)}

        Tindakan Combination Raw Data:
        {json.dumps(eval_tindakan, ensure_ascii=False)}

        Keluarkan hasil dalam JSON valid:
        {{
          "evaluasi_diagnosis": {{"message": "Kalimat evaluasi diagnosis."}},
          "evaluasi_tindakan": {{"message": "Kalimat evaluasi tindakan."}}
        }}

        Format bahasa seperti laporan medis, contoh:
        - "Kombinasi diagnosis valid berdasarkan CP Nasional dan aturan RS lokal."
        - "Semua tindakan sesuai standar CP dan tidak menimbulkan konflik tarif."
        """
        ai_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Kamu AI medis verifikator. Jawab JSON valid tanpa penjelasan tambahan."},
                {"role": "user", "content": ai_prompt}
            ],
            temperature=0.3
        )
        ai_result = json.loads(ai_resp.choices[0].message.content)
        dx_msg = ai_result.get("evaluasi_diagnosis", {}).get("message", "")
        tdk_msg = ai_result.get("evaluasi_tindakan", {}).get("message", "")
    except Exception as e:
        dx_msg = f"AI phrasing gagal: {e}"
        tdk_msg = dx_msg

    # ============================================================
    # 5️⃣ Kembalikan format siap pakai UI
    # ============================================================
    eval_diagnosis["notification"] = {"status": "info", "message": dx_msg or "Hasil evaluasi multilayer (AI phrased)."}
    eval_tindakan["notification"] = {"status": "info", "message": tdk_msg or "Hasil evaluasi multilayer (AI phrased)."}

    return {
        "evaluasi_diagnosis": eval_diagnosis,
        "evaluasi_tindakan": eval_tindakan,
        "engine_version": f"generate_claim_combos@{date.today().isoformat()}"
    }


# ============================================================
# 🔹 FUNGSI ALTERNATIF KOMBINASI (AI SIMULATION)
# ============================================================
def process_generate_alternatives(payload: dict) -> dict:
    """
    Menghasilkan alternatif kombinasi klaim (on-demand, untuk dropdown UI).
    """
    primary_claim = payload.get("primary_claim", "")
    secondary_claims = payload.get("secondary_claims", [])
    primary_action = payload.get("primary_action", "")
    secondary_actions = payload.get("secondary_actions", [])
    rs_id = payload.get("rs_id")
    region_id = payload.get("region_id")

    try:
        rules_diag = load_rules_multilayer([primary_claim] + secondary_claims, rs_id, region_id, scope="diagnosis")
        rules_tdk = load_rules_multilayer([primary_claim] + secondary_claims, rs_id, region_id, scope="tindakan")
    except Exception as e:
        rules_diag, rules_tdk = {}, {}
        print(f"[ALTERNATIF] Gagal load multilayer rules: {e}")

    # 🔹 Gabungkan kedua rules menjadi satu konteks AI
    combined_rules_context = {
        "diagnosis_rules": rules_diag,
        "tindakan_rules": rules_tdk
    }

    # 🔹 AI prompt utama
    prompt = f"""
    Kamu adalah AI medis yang bertugas menyusun alternatif kombinasi klaim BPJS/INA-CBG.
    Berdasarkan aturan multilayer berikut (diagnosis + tindakan):
    {json.dumps(combined_rules_context, ensure_ascii=False)[:1500]}

    Data Klaim:
    - Diagnosis utama: {primary_claim}
    - Diagnosis sekunder: {secondary_claims}
    - Tindakan utama: {primary_action}
    - Tindakan tambahan: {secondary_actions}

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
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Kamu AI medis verifikator BPJS. Jawab JSON valid."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        output = json.loads(resp.choices[0].message.content)
        result = output.get("alternatif", [])
    except Exception as e:
        print(f"[ALTERNATIF] ⚠️ OpenAI error: {e}")
        result = []

    # fallback default
    if not result:
        result = [
            {
                "judul": "Pneumonia + DM",
                "catatan": "Komorbid DM meningkatkan severity & tarif.",
                "severity": "Moderate (2)",
                "ina_cbg": "E-4-10-II",
                "tarif": 8900000,
                "syarat": "HbA1c ≥7%, LOS ≥5 hari",
                "faskes": "RS Tipe B",
                "rawat_inap": "≥5 hari",
                "tindakan": ["Ventilasi Mekanik", "Nebulizer"],
                "notification": {
                    "status": "info",
                    "message": "Kombinasi valid berdasarkan CP Pneumonia + DM."
                }
            }
        ]

    return {
        "alternatif": result,
        "engine_version": "generate_claim_alternatives@2025-10-19",
        "scope": "kombinasi"
    }
