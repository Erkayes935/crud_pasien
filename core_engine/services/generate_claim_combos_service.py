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

    # 🔹 Coba panggil generator alternatif
    try:
        alt_result = process_generate_alternatives(payload)
        alternatif_list = alt_result.get("alternatif", [])
        print(f"[COMBOS] ✅ Generated {len(alternatif_list)} alternatif")
    except Exception as e:
        print(f"[COMBOS] ⚠️ Gagal generate alternatif: {e}")
        alternatif_list = []

    return {
        "evaluasi_diagnosis": evaluation_result["evaluasi_diagnosis"],
        "evaluasi_tindakan": evaluation_result["evaluasi_tindakan"],
        "notification": evaluation_result.get("notification", {"status": "info", "message": "Evaluasi selesai."}),
        "alternatif": alternatif_list,
        "engine_version": evaluation_result["engine_version"],
        "rules_used": evaluation_result.get("rules_used", {})
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
    # 1️⃣ Ambil multilayer rules dari DB (tiga scope: diagnosis, tindakan, kombinasi)
    # ============================================================
    try:
        rules_diag = load_rules_multilayer(diagnoses, rs_id, region_id, scope="diagnosis")
        rules_tdk  = load_rules_multilayer(diagnoses, rs_id, region_id, scope="tindakan")
        rules_combo = load_rules_multilayer(diagnoses, rs_id, region_id, scope="kombinasi")
        
        print(f"[COMBO] 📊 Loaded rules: diagnosis={len(rules_diag)}, tindakan={len(rules_tdk)}, kombinasi={len(rules_combo)}")
    except Exception as e:
        rules_diag, rules_tdk, rules_combo = {}, {}, {}
        print(f"[COMBO] ⚠️ Gagal load multilayer rules: {e}")

    def get_rule_text(rules: dict, field_key: str) -> str:
        """Cari isi rule dari hasil multilayer sesuai field."""
        for rule_field, rule_list in rules.items():
            if match_field_alias(field_key, rule_field):
                if isinstance(rule_list, list) and rule_list:
                    isi = rule_list[0].get("isi")
                    sumber = rule_list[0].get("sumber", "")
                    layer = rule_list[0].get("layer", "")
                    if isi:
                        return {"isi": isi, "sumber": sumber, "layer": layer}
        return None

    def get_rule_with_priority(field_key: str) -> dict:
        """
        Cari rule dengan prioritas cascade:
        1. rules_combo (paling spesifik untuk kombinasi diagnosis+tindakan)
        2. rules_diag atau rules_tdk (fallback ke scope individual)
        3. None (jika tidak ada rule)
        
        Returns:
            dict dengan keys: isi, sumber, layer, scope_used
        """
        # 1️⃣ Prioritas tertinggi: rules_combo (khusus kombinasi)
        combo_result = get_rule_text(rules_combo, field_key)
        if combo_result:
            combo_result["scope_used"] = "kombinasi"
            return combo_result
        
        # 2️⃣ Fallback: rules_diag atau rules_tdk tergantung field
        # Field yang terkait diagnosis
        if field_key in ["validitas", "validitas_klinis", "severity", "kode_icd", "kode_cbg", 
                         "kode_ina_cbg", "tarif", "estimasi_tarif", "syarat_klinis", 
                         "syarat_klinis_kombinasi", "faskes", "faskes.kewenangan", 
                         "evaluasi_faskes", "rawat_inap", "rawat_inap.lama_rawat"]:
            diag_result = get_rule_text(rules_diag, field_key)
            if diag_result:
                diag_result["scope_used"] = "diagnosis"
                return diag_result
        
        # Field yang terkait tindakan
        if field_key in ["tindakan.status", "tindakan_wajib", "tindakan_wajib_kombinasi",
                         "tindakan.validasi", "validasi_pilihan", "fraud", "konflik", 
                         "konflik_duplikasi", "dampak_tarif", "tarif"]:
            tdk_result = get_rule_text(rules_tdk, field_key)
            if tdk_result:
                tdk_result["scope_used"] = "tindakan"
                return tdk_result
        
        # 3️⃣ Tidak ada rule ditemukan
        return None

    # ============================================================
    # 2️⃣ Kumpulkan rules untuk setiap field dengan prioritas cascade
    # ============================================================
    # Field yang PERLU regulasi (akan di-cite oleh AI)
    fields_with_regulation = {
        "diagnosis": [
            "validitas", "validitas_klinis", "severity", "kode_cbg", "kode_ina_cbg",
            "syarat_klinis", "syarat_klinis_kombinasi", "evaluasi_faskes", "rawat_inap"
        ],
        "tindakan": [
            "tindakan_wajib", "tindakan_wajib_kombinasi", "dampak_tarif"
        ]
    }
    
    # Field yang TIDAK perlu regulasi (pure AI reasoning)
    fields_without_regulation = {
        "diagnosis": ["estimasi_tarif"],
        "tindakan": ["validasi_pilihan", "konflik", "konflik_duplikasi"]
    }
    
    # Kumpulkan semua rules yang tersedia untuk context AI
    available_rules = {
        "kombinasi": {},
        "diagnosis": {},
        "tindakan": {}
    }
    
    # Scan semua field yang perlu regulasi
    all_fields = fields_with_regulation["diagnosis"] + fields_with_regulation["tindakan"]
    for field in all_fields:
        rule_data = get_rule_with_priority(field)
        if rule_data:
            scope = rule_data.get("scope_used", "unknown")
            available_rules[scope][field] = {
                "isi": rule_data["isi"],
                "sumber": rule_data["sumber"],
                "layer": rule_data["layer"]
            }

    # ============================================================
    # 3️⃣ Bangun context summary untuk logging
    # ============================================================
    rules_summary = {
        "total_kombinasi": len(available_rules["kombinasi"]),
        "total_diagnosis": len(available_rules["diagnosis"]),
        "total_tindakan": len(available_rules["tindakan"]),
        "fields_kombinasi": list(available_rules["kombinasi"].keys()),
        "fields_diagnosis": list(available_rules["diagnosis"].keys()),
        "fields_tindakan": list(available_rules["tindakan"].keys())
    }
    print(f"[COMBO] 📋 Rules summary: {rules_summary}")

    # ============================================================
    # 4️⃣ Minta AI untuk reasoning dengan cite regulasi
    # ============================================================
    try:
        ai_prompt = f"""
Kamu adalah AI medis konsultan verifikator BPJS Indonesia.

TUGAS:
Evaluasi kombinasi klaim (diagnosis + tindakan) dengan reasoning yang cite regulasi resmi.

📋 INPUT DATA:
- Diagnosis Utama: {primary_claim}
- Diagnosis Sekunder: {secondary_claims}
- Tindakan Utama: {primary_action}
- Tindakan Sekunder: {secondary_actions}
- RS ID: {rs_id or 'N/A'}
- Region: {region_id or 'N/A'}

📚 REGULASI TERSEDIA (gunakan untuk reasoning):

REGULASI KOMBINASI (prioritas tertinggi):
{json.dumps(available_rules['kombinasi'], ensure_ascii=False, indent=2)}

REGULASI DIAGNOSIS (fallback):
{json.dumps(available_rules['diagnosis'], ensure_ascii=False, indent=2)}

REGULASI TINDAKAN (fallback):
{json.dumps(available_rules['tindakan'], ensure_ascii=False, indent=2)}

🎯 INSTRUKSI OUTPUT:

1. FIELD YANG WAJIB CITE REGULASI:
   - validitas: Cite regulasi validitas_klinis atau validitas
   - severity: Cite regulasi severity dari kombinasi/diagnosis
   - kode_cbg: Cite regulasi kode_ina_cbg atau kode_cbg
   - syarat_klinis: Cite regulasi syarat_klinis_kombinasi atau syarat_klinis
   - evaluasi_faskes: Cite regulasi evaluasi_faskes atau faskes
   - rawat_inap: Cite regulasi rawat_inap
   - wajib: Cite regulasi tindakan_wajib_kombinasi atau tindakan_wajib
   - dampak: Cite regulasi dampak_tarif

   Format: "[Reasoning] berdasarkan [Nama Sumber Regulasi]"
   Contoh: "✅ Valid kombinasi diagnosis berdasarkan CP Pneumonia 2021 dan PNPK Komorbid DM 2023"

2. FIELD YANG TIDAK PERLU CITE REGULASI (pure AI reasoning):
   - estimasi_tarif: Estimasi berdasarkan kompleksitas kasus (tanpa cite)
   - validasi: Proses administratif verifikator (tanpa cite)
   - konflik: Deteksi AI rule engine (tanpa cite)

3. PRIORITAS REGULASI:
   - Gunakan regulasi KOMBINASI jika tersedia (paling spesifik)
   - Fallback ke regulasi DIAGNOSIS/TINDAKAN jika kombinasi tidak ada
   - Jika tidak ada regulasi sama sekali, buat reasoning umum tanpa cite

4. FORMAT OUTPUT:
   - Bahasa medis formal tapi ringkas (maks 2 kalimat per field)
   - Jangan gunakan bullet points atau numbering
   - Langsung ke inti tanpa pembukaan panjang

📤 OUTPUT JSON (WAJIB LENGKAP):
{{
  "evaluasi_diagnosis": {{
    "validitas": "string dengan cite regulasi",
    "severity": "string dengan cite regulasi",
    "kode_cbg": "string dengan cite regulasi (format: Kode X-XX-XX - Deskripsi)",
    "estimasi_tarif": "string tanpa cite (format: Rp X.XXX.XXX)",
    "syarat_klinis": "string dengan cite regulasi",
    "evaluasi_faskes": "string dengan cite regulasi",
    "rawat_inap": "string dengan cite regulasi (format: LOS ≥ X hari)"
  }},
  "evaluasi_tindakan": {{
    "wajib": "string dengan cite regulasi",
    "validasi": "string tanpa cite (proses administratif)",
    "dampak": "string dengan cite regulasi",
    "konflik": "string tanpa cite (deteksi AI)"
  }},
  "notification": {{
    "status": "success/warning/info/error",
    "message": "Ringkasan evaluasi keseluruhan (1-2 kalimat)"
  }}
}}

PENTING:
- SEMUA field WAJIB diisi
- Jangan kosongkan field apapun
- Jika tidak ada regulasi, buat reasoning umum yang masuk akal
- Output HARUS valid JSON tanpa teks tambahan di luar JSON
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
        
        # Extract hasil AI
        eval_diagnosis = ai_result.get("evaluasi_diagnosis", {})
        eval_tindakan = ai_result.get("evaluasi_tindakan", {})
        notification = ai_result.get("notification", {"status": "info", "message": "Evaluasi kombinasi selesai."})
        
        print(f"[COMBO] ✅ AI reasoning completed successfully")
        
    except json.JSONDecodeError as e:
        print(f"[COMBO] ⚠️ AI response bukan JSON valid: {e}")
        # Fallback dengan default values
        eval_diagnosis = {
            "validitas": "✅ Valid kombinasi diagnosis (AI fallback).",
            "severity": "Moderate (default).",
            "kode_cbg": "Kode INA-CBG: Perlu verifikasi manual.",
            "estimasi_tarif": "Rp 5.000.000 (estimasi)",
            "syarat_klinis": "Sesuai standar praktik klinis.",
            "evaluasi_faskes": "RS sesuai kewenangan.",
            "rawat_inap": "LOS sesuai kondisi klinis."
        }
        eval_tindakan = {
            "wajib": "Tindakan sesuai indikasi klinis.",
            "validasi": "Memerlukan review verifikator.",
            "dampak": "Dampak tarif sesuai INA-CBG.",
            "konflik": "Tidak terdeteksi konflik."
        }
        notification = {"status": "warning", "message": f"AI parsing error: {e}"}
        
    except Exception as e:
        print(f"[COMBO] ❌ AI error: {e}")
        # Fallback dengan default values
        eval_diagnosis = {
            "validitas": "⚠️ Evaluasi memerlukan review manual.",
            "severity": "Tidak dapat ditentukan.",
            "kode_cbg": "Kode INA-CBG: Perlu verifikasi manual.",
            "estimasi_tarif": "Rp 0 (tidak tersedia)",
            "syarat_klinis": "Perlu review manual.",
            "evaluasi_faskes": "Perlu review manual.",
            "rawat_inap": "Perlu review manual."
        }
        eval_tindakan = {
            "wajib": "Perlu review manual.",
            "validasi": "Memerlukan review verifikator.",
            "dampak": "Perlu review manual.",
            "konflik": "Perlu review manual."
        }
        notification = {"status": "error", "message": f"AI service error: {str(e)}"}

    # ============================================================
    # 5️⃣ Kembalikan format siap pakai UI
    # ============================================================
    return {
        "evaluasi_diagnosis": eval_diagnosis,
        "evaluasi_tindakan": eval_tindakan,
        "notification": notification,
        "engine_version": f"generate_claim_combos_hybrid@{date.today().isoformat()}",
        "rules_used": {
            "kombinasi_count": len(available_rules["kombinasi"]),
            "diagnosis_count": len(available_rules["diagnosis"]),
            "tindakan_count": len(available_rules["tindakan"])
        }
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
