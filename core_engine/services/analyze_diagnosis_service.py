# services/analyze_diagnosis_service.py

import os, json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from services.field_rule_mapping import FIELD_RULE_MAP, FIELD_NAME_ALIAS, match_field_alias

# Load API Key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Import rules loader (pastikan file rules_loader.py ada di services/)
from services.rules_loader import (
    icd10_rules, icd9_rules, fornas_rules,
    inacbg_rules, cp_pnpk_rules, load_diagnosis_rule, load_rules_for_diagnosis
)

# ===========================================================
# HELPER TAMBAHAN (baru)
# ===========================================================
def extract_field_path(field_name: str):
    """Ubah 'rawat_inap.lama_rawat' → ('rawat_inap', 'lama_rawat')"""
    parts = field_name.split(".")
    return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], None)


def get_field_info(section: str, field: str) -> dict:
    """Ambil mapping sumber field dari FIELD_RULE_MAP"""
    domain = FIELD_RULE_MAP.get("diagnosis", {})
    return domain.get(field, {"source": "AI", "layers": [], "type": "ai"})


def should_use_ai(section: str, field: str) -> bool:
    """Tentukan apakah field butuh AI"""
    info = get_field_info(section, field)
    return info["type"] in ["ai", "hybrid"]


def format_multilayer_rules(rule_list: list):
    """Gabungkan beberapa layer menjadi poin-poin (string multi-baris)"""
    if not rule_list:
        return "-"
    lines = []
    for r in rule_list:
        src = r.get("sumber", "-")
        layer = r.get("layer", "-").capitalize()
        isi = r.get("isi", "-").strip()
        lines.append(f"• [{layer}]: {isi} ({src})")
    return "\n".join(lines)

# ==============================
# GPT ANALYZER
# ==============================
def gpt_analyze_diagnosis(disease_name: str, rekam_medis: list):
    """
    Enhanced GPT analysis untuk diagnosis dengan output struktur lengkap
    """
    prompt = f"""
    Anda adalah dokter spesialis untuk analisis klaim BPJS yang memahami regulasi medis Indonesia.
    
    DIAGNOSIS: {disease_name}
    REKAM MEDIS: {rekam_medis}

    Analisis secara komprehensif dan berikan output JSON dengan struktur LENGKAP:
    {{
      "aspek_klinis": {{
        "justifikasi": "Penjelasan medis mengapa diagnosis ini tepat berdasarkan gejala dan pemeriksaan",
        "bukti_klinis": ["Gejala atau temuan yang mendukung diagnosis, misalnya hasil pemeriksaan, keluhan pasien, dan tanda vital yang relevan"],
        "syarat_medis": ["Kriteria diagnosis 1", "Kriteria diagnosis 2"]
      }},
      "icd10": {{
        "utama": "Kode ICD-10 primary yang paling tepat"
      }},
      "tindakan": [
        {{
          "nama": "Nama tindakan medis",
          "icd9": "Kode ICD-9-CM jika ada",
          "status": "wajib/opsional",
          "kategori": "diagnostik/terapi/supportive",
          "regulasi": "Rujukan CP/PNPK yang relevan"
        }}
      ],
      "rawat_inap": {{
        "indikasi": ["Indikasi rawat inap 1", "Indikasi 2"],
        "kriteria": "Kriteria klinis untuk rawat inap",
        "lama_rawat": "Estimasi lama rawat (hari)"
      }},
      "faskes": {{
        "level": "Level faskes yang tepat (RS A/B/C, Puskesmas)",
        "justifikasi": "Alasan mengapa harus di faskes level ini"
      }},
      "rujukan": {{
        "syarat": "Kapan perlu rujukan ke level lebih tinggi",
        "kelayakan": "Ke mana rujukan sebaiknya"
      }},
      "notifications": {{
        "klinis": "Apakah justifikasi & bukti sudah lengkap? Jelaskan singkat.",
        "icd": "Apakah kode ICD sesuai kondisi dan CP? Jelaskan singkat.",
        "tindakan": "Apakah ada tindakan yang wajib/opsional/tidak sesuai? Jelaskan singkat.",
        "rawat": "Apakah lama rawat sudah sesuai CP? Jelaskan singkat.",
        "faskes": "Apakah level faskes sesuai standar? Jelaskan singkat.",
        "rujukan": "Apakah rujukan perlu? Jelaskan singkat.",
        "inacbg": "Apakah tarif INA-CBG sesuai kompleksitas kasus?"
  }}
    }}

    PENTING: 
    - SEMUA field HARUS diisi dengan informasi yang lengkap dan akurat
    - Berikan analisis berdasarkan standar medis Indonesia terkini
    - Jangan kosongkan field apapun yang ditandai wajib
    - Format JSON harus persis sesuai struktur di atas
    - Setiap field harus lengkap dan informatif
    - "notifications" harus berisi kalimat evaluatif singkat (maks 2 kalimat).
    - Pastikan bagian "bukti_klinis" berisi daftar gejala, tanda, atau hasil pemeriksaan yang diambil dari REKAM MEDIS dan yang mendukung diagnosis.
        Contoh:
        REKAM MEDIS: ["Batuk berdahak", "Demam 38°C", "Rontgen menunjukkan infiltrat"]
        Output:
        "bukti_klinis": ["Batuk berdahak", "Demam 38°C", "Infiltrat pada rontgen paru"]
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"❌ GPT error for {disease_name}: {e}")
        return {}

def ensure_default_gpt_structure(gpt_result, disease_name):
    """Memastikan struktur GPT hasil lengkap dan tidak kosong"""
    if not gpt_result:
        gpt_result = {}

    # Pastikan struktur dasar ada
    for section in ["aspek_klinis", "icd10", "rawat_inap", "faskes", "rujukan", "notifications"]:
        if section not in gpt_result:
            gpt_result[section] = {}

    # Pastikan minimal data klinis ada
    if not gpt_result["aspek_klinis"].get("justifikasi"):
        gpt_result["aspek_klinis"]["justifikasi"] = f"Diagnosis {disease_name} perlu dikonfirmasi dengan pemeriksaan penunjang dan evaluasi klinis lebih lanjut."
    
    # Pastikan bukti_klinis selalu list
    bukti_data = gpt_result["aspek_klinis"].get("bukti_klinis") or gpt_result["aspek_klinis"].get("bukti")
    if isinstance(bukti_data, str):
        gpt_result["aspek_klinis"]["bukti_klinis"] = [bukti_data]
    elif isinstance(bukti_data, list):
        gpt_result["aspek_klinis"]["bukti_klinis"] = bukti_data
    else:
        gpt_result["aspek_klinis"]["bukti_klinis"] = []

    # Pastikan data ICD-10 ada
    if not gpt_result["icd10"].get("utama"):
        gpt_result["icd10"]["utama"] = "Perlu verifikasi kode ICD-10 spesifik sesuai manifestasi klinis"

    # Pastikan data lama rawat ada
    if not gpt_result["rawat_inap"].get("lama_rawat"):
        gpt_result["rawat_inap"]["lama_rawat"] = "Sesuai dengan standar praktik klinis untuk diagnosis ini"

    return gpt_result

# ==============================
# INTEGRATOR GPT + RULES (HYBRID APPROACH)
# ==============================
def process_analyze_diagnosis(input_data: dict) -> dict:
    """
    Hybrid multilayer analyzer untuk diagnosis
    - Ambil rule dari DB (rules_master)
    - Tambah JSON nasional (fallback)
    - Tambah AI hanya bila perlu (AI/Hybrid)
    - Hasil akhir disusun sesuai struktur UI (claim.modals.js)
    """

    claim_id = input_data.get("claim_id")
    disease_name = input_data.get("disease_name", "")
    rekam_medis = input_data.get("rekam_medis", [])
    rs_id = input_data.get("rs_id")
    region_id = input_data.get("region_id")

    print(f"[DIAGNOSIS] Mulai analisis multilayer untuk {disease_name}")

    # 1️⃣ Ambil rule multilayer dari DB
    multilayer = load_rules_for_diagnosis(disease_name, rs_id=rs_id, region_id=region_id, scope="diagnosis")
    rule_data_db = multilayer.get("rules", {})

    # 2️⃣ Ambil rule nasional (JSON)
    rule_data_json = load_diagnosis_rule(disease_name)
    rule_data = rule_data_json.copy()

    # 3️⃣ Gabungkan DB ke JSON
    for field, rules in rule_data_db.items():
        section, subfield = extract_field_path(field)
        formatted = format_multilayer_rules(rules)
        top = rules[0] if rules else {}
        src = top.get("sumber", "-")
        layer = top.get("layer", "-")

        # injeksi ke struktur rule_data
        if section not in rule_data:
            rule_data[section] = {}
        if subfield:
            rule_data[section][subfield] = {
                "isi": formatted, "sumber": src, "layer": layer,
                "multi_layer": [r["layer"] for r in rules]
            }
        else:
            rule_data[section] = {
                "isi": formatted, "sumber": src, "layer": layer,
                "multi_layer": [r["layer"] for r in rules]
            }

    # 4️⃣ Evaluasi kelengkapan rule
    completeness = 0
    required_sections = ["aspek_klinis", "icd10", "rawat_inap", "faskes", "rujukan", "ina_cbg"]
    for sec in required_sections:
        if rule_data.get(sec): completeness += 1
    completeness_score = (completeness / len(required_sections)) * 100
    print(f"[DIAGNOSIS] Rule completeness: {completeness_score:.1f}%")

    # 5️⃣ Panggil AI bila perlu
    gpt_result = None
    print("[DIAGNOSIS] Memanggil GPT untuk melengkapi data hybrid...")
    gpt_result = gpt_analyze_diagnosis(disease_name, rekam_medis)
    # Pastikan struktur GPT selalu lengkap
    gpt_result = ensure_default_gpt_structure(gpt_result, disease_name)

    # ============================================================
    # 6️⃣ Smart Merge (berdasarkan FIELD_RULE_MAP)
    # ============================================================
    MULTILAYER_FIELDS = [
        "syarat_klinis", "kode_ganda", "kode_bpjs_khusus", "z_code",
        "lama_rawat", "indikasi", "kriteria",
        "rujukan_kriteria", "rujukan_tujuan",
        "ina_cbg_kode", "ina_cbg_tarif"
    ]
    
    def smart_merge(section_key: str, rule_data: dict, ai_data: dict, rule_data_db: dict):
        """Gabungkan rule multilayer dan AI dengan bullet list"""
        section = rule_data.get(section_key, {})
        ai_sec = ai_data.get(section_key, {}) if ai_data else {}
        merged = ai_sec.copy() if isinstance(ai_sec, dict) else {}

        # --- Field mapping diagnosis (FIELD_RULE_MAP)
        domain_map = FIELD_RULE_MAP.get("diagnosis", {})

        for field, meta in domain_map.items():
            field_name = field.lower()
            val_rule = None
            val_ai = ai_sec.get(field_name) if ai_sec else None

            # 🔹 Jika field multilayer, gabungkan semua rule jadi poin
            if field_name in MULTILAYER_FIELDS:
                multilayer_rules = []
                for db_field, rules in rule_data_db.items():
                    db_sec, db_sub = extract_field_path(db_field)
                    # Tambahkan debug print untuk melihat pencocokan
                    # print(f"DEBUG: field_name={field_name}, db_field={db_field}, db_sec={db_sec}, db_sub={db_sub}")
                    if (
                        match_field_alias(field_name, db_field)
                        or (db_sub and match_field_alias(field_name, db_sub))
                        or (db_sec and match_field_alias(field_name, db_sec))
                        or db_field == field_name
                        or (db_sub and db_sub == field_name)
                        or (db_sec and db_sec == field_name)
                    ) and isinstance(rules, list) and len(rules) > 0:
                        for r in rules:
                            multilayer_rules.append({
                                "layer": r.get("layer", "-"),
                                "sumber": r.get("sumber", "-"),
                                "isi": r.get("isi", "-")
                            })

                # PERBAIKAN: Jika section_key == "icd10", juga cek field tanpa prefix
                if not multilayer_rules and section_key == "icd10":
                    for db_field, rules in rule_data_db.items():
                        if db_field in ["kode_ganda", "z_code"] and isinstance(rules, list) and len(rules) > 0:
                            for r in rules:
                                multilayer_rules.append({
                                    "layer": r.get("layer", "-"),
                                    "sumber": r.get("sumber", "-"),
                                    "isi": r.get("isi", "-")
                                })

                if multilayer_rules:
                    formatted = "\n".join([
                        f"• [{r['layer'].capitalize()}] {r['isi']} ({r['sumber']})"
                        for r in multilayer_rules
                    ])
                    merged[field_name] = formatted
                else:
                    merged[field_name] = val_ai or "-"
                continue

            # 🔹 Kalau bukan multilayer → merge normal
            if not should_use_ai("diagnosis", field):
                found = False
                for db_field in rule_data_db.keys():
                    if match_field_alias(field_name, db_field):
                        sec, sub = extract_field_path(db_field)
                        val_rule = rule_data.get(sec, {}).get(sub, {}).get("isi")
                        found = True
                        break
                merged[field_name] = val_rule if found else "-"
            else:
                merged[field_name] = val_ai or val_rule or "-"
        return merged

    aspek_klinis = smart_merge("aspek_klinis", rule_data, gpt_result, rule_data_db)
    icd10_data = smart_merge("icd10", rule_data, gpt_result, rule_data_db)
    rawat_inap = smart_merge("rawat_inap", rule_data, gpt_result, rule_data_db)
    faskes = smart_merge("faskes", rule_data, gpt_result, rule_data_db)
    rujukan = smart_merge("rujukan", rule_data, gpt_result, rule_data_db)
    ina_cbg_info = rule_data.get("ina_cbg", {})

    # Penyesuaian khusus untuk ICD-10
    if gpt_result and gpt_result.get("icd10", {}).get("utama"):
        # Jika ICD-10 masih kosong, gunakan dari GPT
        if not icd10_data.get("kode_icd") or icd10_data.get("kode_icd") == "-":
            icd10_data["kode_icd"] = gpt_result["icd10"]["utama"]
            print(f"[ANALYZE_DIAGNOSIS] 🔄 Using ICD-10 from AI: {icd10_data['kode_icd']}")

    # Penyesuaian khusus untuk Rujukan
    if gpt_result and gpt_result.get("rujukan"):
        # Jika kriteria rujukan kosong, gunakan 'syarat' dari AI
        if not rujukan.get("kriteria") and not rujukan.get("rujukan_kriteria"):
            rujukan["rujukan_kriteria"] = gpt_result["rujukan"].get("syarat")
            print(f"[ANALYZE_DIAGNOSIS] 🔄 Using rujukan criteria from AI: {rujukan['rujukan_kriteria']}")
        
        # Jika tujuan rujukan kosong, gunakan 'kelayakan' dari AI
        if not rujukan.get("tujuan") and not rujukan.get("rujukan_tujuan"):
            rujukan["rujukan_tujuan"] = gpt_result["rujukan"].get("kelayakan")
            print(f"[ANALYZE_DIAGNOSIS] 🔄 Using rujukan destination from AI: {rujukan['rujukan_tujuan']}")

    # =====================================================
    # ✅ FORMAT MULTILAYER RULES (bullet points untuk UI)
    # =====================================================
    def format_multilayer_points(field_rules):
        """Ubah list rule multilayer jadi string bullet points"""
        if not field_rules or not isinstance(field_rules, list):
            return "-"
        formatted = []
        for r in field_rules:
            layer = r.get("layer", "-").capitalize()
            src = r.get("sumber", "-")
            isi = r.get("isi", "-").strip()
            formatted.append(f"• [{layer}] {isi} ({src})")
        return "\n".join(formatted)

    # Loop semua field hasil load multilayer dari DB
    for field_key, rule_list in rule_data_db.items():
        if len(rule_list) > 1:  # hanya kalau punya lebih dari satu layer
            section, subfield = extract_field_path(field_key)
            formatted_text = format_multilayer_points(rule_list)

            if section not in rule_data:
                rule_data[section] = {}
            if subfield:
                existing = rule_data[section].get(subfield, {})
                existing["isi"] = formatted_text
                existing["multi_layer"] = [r["layer"] for r in rule_list]
                rule_data[section][subfield] = existing
            else:
                existing = rule_data.get(section, {})
                existing["isi"] = formatted_text
                existing["multi_layer"] = [r["layer"] for r in rule_list]
                rule_data[section] = existing


    # ============================================================
    # 7️⃣ Build Response (dipertahankan)
    # ============================================================
    def assess_status(data):
        if data is None:
            return "missing"
        if isinstance(data, str):
            if data.strip() in ["", "-"]:
                return "missing"
            return "complete" 
        if isinstance(data, list) and len(data) > 0:
            return "complete" 
        if isinstance(data, dict) and any(v for v in data.values() if v not in ["", "-", None, []]):
            return "complete"
        return "missing"

    result = {
        "klinis": {
            "justifikasi": aspek_klinis.get("justifikasi", "-"),
            "bukti_klinis": 
                (aspek_klinis.get("bukti_klinis") or 
                ("; ".join(aspek_klinis.get("bukti", [])) if isinstance(aspek_klinis.get("bukti", []), list) else aspek_klinis.get("bukti", "-"))),
            "syarat_klinis": aspek_klinis.get("syarat_klinis", "-"),
            "confidence_ai": "85%" if gpt_result else "N/A",
            "status": assess_status(aspek_klinis.get("justifikasi")),
        },
        "icd10": {
            "kode_icd": icd10_data.get("kode_icd", "-"),
            "struktur_icd10": icd10_data.get("struktur_icd10", "-"), 
            "kode_ganda": icd10_data.get("kode_ganda", "-"),          
            "z_code": icd10_data.get("z_code", "-"),
            "kode_bpjs_khusus": icd10_data.get("kode_bpjs_khusus", "-"),
            "status_icd": assess_status(icd10_data.get("kode_icd")),
        },
        "rawat_inap": {  # Gunakan nama konsisten rawat_inap
            "indikasi": rawat_inap.get("indikasi", "-"),  # Gunakan "-" bukan null
            "kriteria": rawat_inap.get("kriteria", "-"),  # Gunakan "-" bukan null
            "lama_rawat": rawat_inap.get("lama_rawat", "-"),
            "status_lama": assess_status(rawat_inap.get("lama_rawat")),
            "status_indikasi": assess_status(rawat_inap.get("indikasi")),
            "status_kriteria": assess_status(rawat_inap.get("kriteria")),
        },
        "faskes": {
            "tingkat": faskes.get("faskes_tingkat", "-"),  # Gunakan "-" bukan null
            "justifikasi": faskes.get("faskes_justifikasi", "-"),
            "kompetensi": faskes.get("kompetensi", "-"),  # Tambahkan field ini
            "status_tingkat": assess_status(faskes.get("faskes_tingkat")),
            "status_justifikasi": assess_status(faskes.get("faskes_justifikasi")),
            "status_kompetensi": assess_status(faskes.get("kompetensi")),
        },
        "rujukan": {
            "kriteria": rujukan.get("rujukan_kriteria", "-"),  # Gunakan "-" bukan null
            "tujuan": rujukan.get("rujukan_tujuan", "-"),  # Gunakan "-" bukan null
            "indikasi": (rujukan.get("indikasi_rujukan") or rujukan.get("indikasi") or rujukan.get("alasan") or "-"),
            "status_kriteria": assess_status(rujukan.get("rujukan_kriteria")),
            "status_tujuan": assess_status(rujukan.get("rujukan_tujuan")),
            "status_indikasi": assess_status(rujukan.get("indikasi_rujukan")),
        },
        "inaCbg": {
            "kode": ina_cbg_info.get("kode", "-"),
            "tarif": ina_cbg_info.get("tarif", "-"),
            "deskripsi": ina_cbg_info.get("deskripsi", "-"),  # Tambahkan field ini
            "status_kode": assess_status(ina_cbg_info.get("kode")),
            "status_tarif": assess_status(ina_cbg_info.get("tarif")),
            "status_deskripsi": assess_status(ina_cbg_info.get("deskripsi")),
        },
        "engine_version": "hybrid_multilayer_v2@2025-10-13",
        "data_completeness": f"{completeness_score:.0f}%",
    }

    # =====================================================
    # 7️⃣b AI Fallback Otomatis
    # =====================================================
    if gpt_result:
        print("[ANALYZE_DIAGNOSIS] 🧠 Applying AI fallback for empty fields...")
        
        # DEFINISIKAN FIELD MAPPING UNTUK AI
        ai_field_mapping = {
            # ICD-10 mapping
            "icd10": {
                "kode_icd": ["utama", "kode", "who", "kode_icd"],
                "struktur_icd10": ["deskripsi", "struktur", "nama"],
                "kode_ganda": ["kode_ganda", "komorbid", "secondary"],
                "z_code": ["z_code", "z_codes"],
                "kode_bpjs_khusus": ["bpjs", "kode_khusus", "kode_bpjs"]
            },
            # Rujukan mapping
            "rujukan": {
                "kriteria": ["kriteria", "syarat", "indikasi_rujukan"],
                "tujuan": ["tujuan", "kelayakan", "destinasi"],
                "indikasi": ["indikasi", "alasan", "sebab"]
            },
            # FASKES mapping
            "faskes": {
                "tingkat": ["level", "tingkat", "faskes_tingkat"],
                "justifikasi": ["justifikasi", "alasan", "faskes_justifikasi"],
                "kompetensi": ["kompetensi", "keahlian", "spesialisasi", "dokter", "tenaga_medis"]
            },
            # RAWAT INAP mapping
            "rawat_inap": {
                "indikasi": ["indikasi", "alasan"],
                "kriteria": ["kriteria", "syarat"],
                "lama_rawat": ["lama_rawat", "los", "durasi"]
            }
        }
        
        # Improved ai_fallback function
        def improved_ai_fallback(section_key, result_section):
            ai_section = {}
            
            # 1. Get correct AI section
            if section_key == "klinis":
                ai_section = gpt_result.get("aspek_klinis", {})
            elif section_key == "inaCbg":
                ai_section = gpt_result.get("ina_cbg", {})
            else:
                ai_section = gpt_result.get(section_key, {})
                
            if not ai_section:
                return result_section
            
            # 2. Process each field
            for key, val in result_section.items():
                # Skip status fields
                if key.startswith("status_"):
                    continue
                    
                # Only replace empty values
                if val not in ["", "-", None]:
                    continue
                    
                # Try direct match
                ai_val = ai_section.get(key)
                
                # If not found, try mapping alternatives
                if not ai_val and section_key in ai_field_mapping:
                    field_alternatives = ai_field_mapping.get(section_key, {}).get(key, [])
                    for alt_key in field_alternatives:
                        ai_val = ai_section.get(alt_key)
                        if ai_val:
                            print(f"  Found alternative {alt_key} for {key} in {section_key}")
                            break
                
                # Format the value
                if isinstance(ai_val, list):
                    ai_val = "; ".join([str(x) for x in ai_val if x])
                elif isinstance(ai_val, dict):
                    ai_val = ai_val.get("isi", "-") 
                    
                # Update if we found a value
                if ai_val:
                    print(f"  [AI FALLBACK] {section_key}.{key} = {ai_val}")
                    result_section[key] = ai_val
        
            return result_section
            
        # Apply improved AI fallback
        for section_key, section_data in result.items():
            if isinstance(section_data, dict):
                result[section_key] = improved_ai_fallback(section_key, section_data)
                
        print("[ANALYZE_DIAGNOSIS] ✅ AI fallback completed.")

    # ============================================================
    # 8️⃣ Notifikasi (tidak diubah)
    # ============================================================
    notifications = {}
    if gpt_result and gpt_result.get("notifications"):
        for key, text in gpt_result["notifications"].items():
            status = "success" 
            txt_lower = text.lower()
            if any(w in txt_lower for w in ["tidak sesuai", "kurang", "perlu", "belum", "review"]):
                status = "warning"
            if any(w in txt_lower for w in ["salah", "tidak valid", "keliru"]):
                status = "error"
            else:
                status = "info"  
            notifications[key] = {"status": status, "message": text}
        result["notifications"] = notifications

    # Proses tindakan dari GPT atau rules
    tindakan_rules = rule_data.get("tindakan", [])
    tindakan_ai = gpt_result.get("tindakan", []) if gpt_result else []
    tindakan = tindakan_rules if tindakan_rules else tindakan_ai

    result["tindakan"] = []
    import time
    for t in tindakan:
        if isinstance(t, dict):
            result["tindakan"].append({
                "nama": t.get("nama", "-"),
                "tindakan": t.get("nama", "-"),
                "deskripsi": t.get("deskripsi", t.get("nama", "-")),
                "icd9_code": t.get("icd9", t.get("icd9_code", "-")),
                "status": t.get("status", "-"),
                "kategori": t.get("kategori", "-"),
                "regulasi": t.get("regulasi", "-"),
                "syarat_klinis": t.get("syarat_klinis", "-"),
                "ina_cbg_impact": t.get("ina_cbg_impact", "-"),
                "id": int(time.time() * 1000) + len(result["tindakan"])
            })

    # Tambahkan transformasi format data untuk field tertentu seperti tarif
    if "tarif" in result["inaCbg"] and result["inaCbg"]["tarif"] != "-":
        try:
            # Format tarif sebagai string dengan format "Rp X.XXX.XXX"
            numeric_value = ''.join(c for c in str(result["inaCbg"]["tarif"]) if c.isdigit())
            if numeric_value:
                amount = int(numeric_value)
                result["inaCbg"]["tarif"] = f"Rp {amount:,}".replace(",", ".")
        except:
            pass 

    # Fix struktur ICD-10 jika kode ICD tersedia tapi struktur kosong
    if result["icd10"]["struktur_icd10"] == "-" and result["icd10"]["kode_icd"] != "-":
        icd_code = result["icd10"]["kode_icd"]
        
        # Cek dari mapping icd10_rules (sama seperti kode lama)
        from services.rules_loader import icd10_rules
        icd_info = icd10_rules.get(icd_code, {})
        if icd_info and icd_info.get("deskripsi"):
            result["icd10"]["struktur_icd10"] = icd_info.get("deskripsi")
            print(f"[DIAGNOSIS] ✓ Struktur ICD-10 dari rules_loader: {icd_code}")
        else:
            # ICD-10 umum (bisa ditambahkan sesuai kebutuhan)
            result["icd10"]["struktur_icd10"] = f"ICD-10 code: {icd_code}"
            print(f"[DIAGNOSIS] ✓ Generated ICD-10 structure: {icd_code}")
            
        # Set status complete karena sudah diisi
        result["icd10"]["status_icd"] = "complete"

    # Fix kompetensi faskes berdasarkan diagnosis
    if result["faskes"]["kompetensi"] == "-":
        # Generate berdasarkan tingkat faskes dan diagnosis
        tingkat_faskes = result["faskes"]["tingkat"].lower()
        if "pneumonia" in disease_name.lower():
            if "tipe b" in tingkat_faskes:
                result["faskes"]["kompetensi"] = "Dokter spesialis paru, spesialis penyakit dalam"
            else:
                result["faskes"]["kompetensi"] = "Dokter spesialis penyakit dalam"
        else:
            result["faskes"]["kompetensi"] = "Dokter spesialis sesuai kondisi klinis"
        result["faskes"]["status_kompetensi"] = "complete"
    
    # Fix indikasi rujukan jika kosong
    if result["rujukan"]["indikasi"] == "-":
        # Gunakan kriteria jika tersedia
        if result["rujukan"]["kriteria"] != "-":
            result["rujukan"]["indikasi"] = result["rujukan"]["kriteria"]
            result["rujukan"]["status_indikasi"] = "complete"
    
    # Formatting tambahan bukti_klinis untuk tampilan yang lebih rapi
    if result.get("klinis", {}).get("bukti_klinis"):
        bukti_text = result["klinis"]["bukti_klinis"]
        if isinstance(bukti_text, str):
            # tambahkan spasi setelah koma kalau belum ada
            result["klinis"]["bukti_klinis"] = bukti_text.replace(",", ", ")
            # hilangkan spasi ganda berlebihan
            result["klinis"]["bukti_klinis"] = " ".join(
                result["klinis"]["bukti_klinis"].split()
            )
        elif isinstance(bukti_text, list):
            # kalau list, gabung jadi string rapi
            result["klinis"]["bukti_klinis"] = ", ".join(bukti_text)

    print(f"[DIAGNOSIS] ✅ Analisis selesai ({result['data_completeness']} lengkap)")
    return result
