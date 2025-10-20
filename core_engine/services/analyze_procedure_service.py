import os, json
from datetime import date
from typing import Any, Dict
from openai import OpenAI
from .rules_loader import load_rules_for_diagnosis
from .field_rule_mapping import FIELD_RULE_MAP
from .field_rule_mapping import match_field_alias

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def _sv(x: Any, default: str = "-") -> str:
    return x.strip() if isinstance(x, str) and x.strip() else default


def process_analyze_procedure(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    HYBRID Procedure Analysis (AI + Multilayer Rules)
    Hasil akhir: ringkasan AI yang sudah mempertimbangkan rules multilayer.
    Rules DB dipakai sebagai konteks reasoning, bukan ditampilkan mentah.
    """
    claim_id = payload.get("claim_id")
    procedure = payload.get("procedure_name") or payload.get("procedure") or ""
    stage = (payload.get("stage") or "admission").strip()
    ctx = payload.get("context") or {}
    dx_pri = ctx.get("primary_claim", "")
    rs_id = ctx.get("rs_id")
    region_id = ctx.get("region_id")
    hospital_level = ctx.get("hospital_level", "")

    print(f"[ANALYZE_PROCEDURE] Processing: {procedure}")

    # ================================================================
    # 1️⃣ LOAD MULTILAYER RULES (DARI DB)
    # ================================================================
    multilayer = load_rules_for_diagnosis(dx_pri, rs_id=rs_id, region_id=region_id, scope="tindakan", procedure=procedure)
    all_rules = multilayer.get("rules", {})
    tindakan_map = FIELD_RULE_MAP.get("tindakan", {})

    LAYER_ORDER = {
        "permenkes": 1, "nasional": 2, "ppk": 3, "regional": 4,
        "rs": 5, "bridging": 6, "fraud": 7, "temporary": 8
    }

    multilayer_output = {}
    for field_name, meta in tindakan_map.items():
        layers = meta.get("layers", [])
        field_rules = []

        # Ambil semua rule yang sesuai dengan mapping layer
        for db_field, db_rules in all_rules.items():
            if match_field_alias(field_name, db_field):
                for r in db_rules:
                    layer_num = LAYER_ORDER.get(r["layer"])
                    if layer_num in layers:
                        field_rules.append(r)

        if field_rules:
            field_rules.sort(key=lambda x: x["priority"])
            combined_layers = ", ".join(
                sorted({r["layer"] for r in field_rules}, key=lambda x: LAYER_ORDER.get(x, 99))
            )
            multilayer_output[field_name] = {
                "items": [
                    {"isi": r["isi"], "sumber": r["sumber"], "layer": r["layer"]}
                    for r in field_rules
                ],
                "combined_label": combined_layers,
            }
    # ================================================================
    # 2️⃣ BENTUK RULES CONTEXT UNTUK PROMPT AI
    # ================================================================
    rule_contexts = []
    for field, group in multilayer_output.items():
        rule_text = "\n".join(
            [f"- [{r['layer']}] {r['isi']} (Sumber: {r['sumber']})" for r in group["items"]]
        )
        rule_contexts.append(f"📘 {field.upper()}:\n{rule_text}\n")

    rules_summary = "\n".join(rule_contexts) if rule_contexts else "Tidak ada aturan multilayer."

    # ================================================================
    # 2️⃣ REQUEST OPENAI (PROMPT LENGKAP)
    # ================================================================
    print(f"[ANALYZE_PROCEDURE] Requesting OpenAI analysis for: {procedure}")

    dx_sec = ctx.get("secondary_claims", [])
    act_pri = ctx.get("primary_action", "")
    act_sec = ctx.get("secondary_actions", [])
    patient_context = ctx.get("patient_context", "")

    prompt = f"""
    Anda adalah konsultan coding medis dan spesialis klaim BPJS Indonesia.

    Langkah Anda:
    1. Baca dan pahami semua aturan multilayer di bawah ini.
    2. Untuk setiap field (Validitas, Status, INA-CBG, dst), simpulkan hasil akhir
       berdasarkan isi aturan tersebut.
    3. Jika suatu field tidak punya aturan, gunakan pengetahuan medis umum.
    4. Hasilkan ringkasan singkat berbahasa medis yang mudah dipahami dokter/verifikator.

    ====== KUMPULAN ATURAN MULTILAYER ======
    {rules_summary}

    ====== KONTEKS KLAIM ======
    Diagnosis: {dx_pri}
    Tindakan: {procedure}
    RS level: {hospital_level}
    Stage: {stage}
    Context JSON: {json.dumps(ctx, ensure_ascii=False)}
    
    Tentukan apakah tindakan ini:
    - Sesuai dengan Clinical Pathway (CP) dan Panduan Nasional (PNPK)
    - Sudah didukung oleh data rekam medis (hasil lab, radiologi, durasi rawat, indikasi klinis)
    - Memerlukan tambahan pemeriksaan atau lama rawat tertentu
    - Perlu penyesuaian tarif atau kelayakan level RS

    Keluarkan hasil akhir ringkas seperti contoh berikut:
    {{
      "procedure": "{procedure}",
      "icd9_code": "Kode ICD-9-CM yang akurat sesuai WHO/BPJS",
      "icd9_desc": "Deskripsi lengkap ICD-9-CM Indonesia",
      "deskripsi": "Ringkasan singkat: Kode ICD-9, Status, INA-CBG",
      "validitas": "VALID/TIDAK VALID/PERLU REVIEW + alasan klinis yang jelas",
      "status_tindakan": "WAJIB/OPSIONAL/SUPPORTIVE + justifikasi berdasarkan CP/PNPK",
      "status": "Status singkat untuk tampilan UI",
      "ina_cbg_tarif": "Dampak ke tarif INA-CBG atau estimasi biaya Rp",
      "ina_cbg": "Impact grouping ringkas",
      "faskes": "Level RS yang sesuai (A/B/C/Puskesmas) + alasan kapasitas",
      "rawat_inap": "Indikasi rawat inap: WAJIB/TIDAK/CONDITIONAL + syarat",
      "syarat_klinis": "Persyaratan medis/lab/imaging yang diperlukan sebelum tindakan",
      "notification": {{
          "status": "success/warning/error/info",
          "message": "Kalimat singkat yang berupa rekomendasi AI untuk dokter, contoh:
          - 'Belum ditemukan hasil radiologi — mohon lengkapi sebelum klaim.'
          - 'Durasi rawat 1 hari — CP mensyaratkan minimal 3 hari.'
          - 'Kode ICD sudah sesuai hasil Lab dan CP.'
          - 'Perlu pemeriksaan kultur darah untuk melengkapi klaim.'
      }}
    }}

    PEDOMAN ANALISIS:
    - ICD-9-CM harus sesuai standar internasional dan mapping BPJS
    - Validitas berdasarkan kesesuaian dengan diagnosis dan indikasi medis
    - Status tindakan mengacu pada CP/PNPK dan panduan klinis nasional
    - Tarif mengacu pada INA-CBG terbaru dan realitas biaya RS Indonesia
    - Level faskes sesuai Permenkes tentang klasifikasi dan kapasitas RS
    - Syarat klinis harus spesifik dan dapat diverifikasi
    - Semua field wajib diisi dengan informasi yang berguna, hindari "-" atau kosong

    Pedoman untuk 'notification.message':
    - Gunakan gaya *rekomendatif*, bukan deskriptif.
    - Sebutkan tindakan apa yang harus dilakukan dokter (lengkapi lab, tambah durasi rawat, dsb).
    - Status:
      - 'error' → dokumentasi penting hilang.
      - 'warning' → data ada tapi belum lengkap / durasi rawat kurang.
      - 'success' → semua sudah sesuai CP/PNPK dan kelayakan RS.
      - 'info' → tindakan tidak memengaruhi tarif klaim.

    Output harus valid JSON tanpa penjelasan tambahan.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Anda adalah konsultan medis dan coding specialist BPJS. Jawab hanya dalam format JSON yang valid."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        raw = (response.choices[0].message.content or "").strip()
        ai_data = json.loads(raw)
        print(f"[ANALYZE_PROCEDURE] ✅ OpenAI JSON parsed successfully")

    except Exception as e:
        print(f"[ANALYZE_PROCEDURE] ⚠️ OpenAI API error: {e}")
        ai_data = {}
    
    # ================================================================
    # 3️⃣ BUILD RESPONSE (tetap sama + tambahan multilayer)
    # ================================================================
    
    # Extract fields for description formatting
    icd9_code = _sv(ai_data.get("icd9_code", ""))
    status = _sv(ai_data.get("status_tindakan", ""))
    ina_cbg_tarif = _sv(ai_data.get("ina_cbg_tarif", ""))
    
    # Format description like manual entries: "ICD-9: code, Status: value, INA-CBG: price"
    formatted_description = ""
    if icd9_code:
        formatted_description += f"ICD-9: {icd9_code}"
        
    if status:
        if formatted_description:
            formatted_description += ", "
        formatted_description += f"Status: {status}"
        
    if ina_cbg_tarif:
        if formatted_description:
            formatted_description += ", "
        formatted_description += f"INA-CBG: {ina_cbg_tarif}"

    # Check if this is an explicit procedure view request (not just from diagnosis analysis)
    is_explicit_procedure_request = payload.get("procedure_name") and procedure
    
    # Don't expose the formatted description in the API response
    # We'll only set it to deskripsi when explicitly viewing procedure details
    result = {
        "procedure": _sv(ai_data.get("procedure", procedure), procedure or "-"),
        "icd9_code": icd9_code,
        "icd9": icd9_code,
        "icd9_desc": _sv(ai_data.get("icd9_desc", "")),
        "deskripsi": formatted_description if is_explicit_procedure_request else "",
        "validitas": _sv(ai_data.get("validitas", "")),
        "status_tindakan": _sv(ai_data.get("status_tindakan", "")),
        "status": _sv(ai_data.get("status", ai_data.get("status_tindakan", ""))),
        "ina_cbg_tarif": _sv(ai_data.get("ina_cbg_tarif", "")),
        "ina_cbg": _sv(ai_data.get("ina_cbg", ai_data.get("ina_cbg_tarif", ""))),
        "faskes": _sv(ai_data.get("faskes", "")),
        "rawat_inap": _sv(ai_data.get("rawat_inap", "")),
        "syarat_klinis": _sv(ai_data.get("syarat_klinis", "")),
        "source": "AI reasoning (rule-based)",
        "data_completeness": "100%" if ai_data else "0%",
        "engine_version": f"rule_based_analyze_procedure@{date.today().isoformat()}",
        "notification": ai_data.get("notification", {
            "status": "info",
            "message": "Belum ada notifikasi untuk bagian TINDAKAN."
        }),
        "multilayer_rules": multilayer_output,
    }

    print(f"[ANALYZE_PROCEDURE] ✅ Response built successfully for: {procedure}")
    print(f"[ANALYZE_PROCEDURE] Diagnosis: {dx_pri}")
    print(f"[ANALYZE_PROCEDURE] All rule fields from DB: {list(all_rules.keys())}")
    print(f"[ANALYZE_PROCEDURE] Matched multilayer fields: {list(multilayer_output.keys())}")
    return result
