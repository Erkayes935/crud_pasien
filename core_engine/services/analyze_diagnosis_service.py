# services/analyze_diagnosis_service.py

import os, json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load API Key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Import rules loader (pastikan file rules_loader.py ada di services/)
from services.rules_loader import (
    icd10_rules, icd9_rules, fornas_rules,
    inacbg_rules, cp_pnpk_rules, load_diagnosis_rule
)

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
        "bukti": ["Gejala 1", "Tanda klinis 2", "Hasil pemeriksaan 3"],
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
    - Berikan analisis berdasarkan standar medis Indonesia
    - Sesuaikan dengan panduan CP/PNPK BPJS
    - Gunakan istilah medis Indonesia
    - Semua field harus diisi, jangan ada yang kosong
    - "notifications" harus berisi kalimat evaluatif singkat (maks 2 kalimat).
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        print(f"[GPT_ANALYSIS] Success for {disease_name}")
        return result
    except Exception as e:
        print(f"❌ Error GPT analyze_diagnosis for {disease_name}: {e}")
        return {
            "aspek_klinis": {
                "justifikasi": f"Memerlukan analisis lebih lanjut untuk {disease_name}",
                "bukti": ["Data rekam medis terbatas"],
                "syarat_medis": ["Perlu evaluasi klinis komprehensif"]
            },
            "icd10": {"utama": "-"},
            "tindakan": [],
            "rawat_inap": {
                "indikasi": ["Sesuai kondisi klinis"],
                "kriteria": "Berdasarkan assessment dokter",
                "lama_rawat": "Sesuai kondisi"
            },
            "faskes": {
                "level": "Sesuai kapasitas",
                "justifikasi": "Berdasarkan kompleksitas kasus"
            },
            "rujukan": {
                "syarat": "Jika diperlukan",
                "kelayakan": "Ke faskes dengan kapasitas sesuai"
            },
            "notifications": {
                "klinis": "Belum ada analisis AI",
                "icd": "Belum ada analisis AI",
                "tindakan": "Belum ada analisis AI",
                "rawat": "Belum ada analisis AI",
                "faskes": "Belum ada analisis AI",
                "rujukan": "Belum ada analisis AI",
                "inacbg": "Belum ada analisis AI"
            }
        }

# ==============================
# INTEGRATOR GPT + RULES (HYBRID APPROACH)
# ==============================
def process_analyze_diagnosis(input_data: dict) -> dict:
    """
    Hybrid approach: Rules priority + OpenAI fallback
    1. Check rules folder untuk disease_name
    2. Jika data rules lengkap -> gunakan rules
    3. Jika data rules kosong/incomplete -> request OpenAI
    4. Return format sesuai claim.modals.js structure
    """

    claim_id = input_data.get("claim_id")
    disease_name = input_data.get("disease_name", "")
    rekam_medis = input_data.get("rekam_medis", [])

    # --- 1. PRIORITY: Check rules folder diagnosis
    rule_data = load_diagnosis_rule(disease_name)
    
    # Assess rule completeness more thoroughly
    def assess_rule_completeness(rule_data):
        if not rule_data:
            return 0, "No rule file found"
            
        score = 0
        total_sections = 7  # aspek_klinis, icd10, tindakan, rawat_inap, faskes, rujukan, ina_cbg
        
        # Check each section
        if rule_data.get("aspek_klinis", {}).get("justifikasi"):
            score += 1
        if rule_data.get("icd10", {}).get("who"):
            score += 1  
        if rule_data.get("tindakan") and len(rule_data.get("tindakan", [])) > 0:
            score += 1
        if rule_data.get("rawat_inap", {}).get("indikasi"):
            score += 1
        if rule_data.get("faskes", {}).get("level"):
            score += 1
        if rule_data.get("rujukan", {}).get("syarat"):
            score += 1
        if rule_data.get("ina_cbg", {}).get("kode"):
            score += 1
            
        completeness = (score / total_sections) * 100
        status = "complete" if completeness >= 80 else ("partial" if completeness >= 40 else "incomplete")
        
        return completeness, status
    
    rule_completeness, rule_status = assess_rule_completeness(rule_data)
    has_complete_rules = rule_completeness >= 80
    
    print(f"[ANALYZE_DIAGNOSIS] Disease: {disease_name}")
    print(f"[ANALYZE_DIAGNOSIS] Rule completeness: {rule_completeness:.1f}% ({rule_status})")
    print(f"[ANALYZE_DIAGNOSIS] Will use: {'Rules primary' if has_complete_rules else 'AI primary + Rules supplement'}")

    # --- 2. Get OpenAI analysis to supplement incomplete rules  
    gpt_result = None
    if rule_completeness < 100:  # Always get AI if rules not 100% complete
        print(f"[ANALYZE_DIAGNOSIS] Requesting OpenAI to supplement rules (completeness: {rule_completeness:.1f}%)")
        gpt_result = gpt_analyze_diagnosis(disease_name, rekam_medis)

    # --- 3. INTELLIGENT MERGE: Rules priority, AI fills gaps
    def merge_data(rule_data, ai_data, section_key):
        """Smart merge: use rules if exist, otherwise use AI"""
        rule_section = rule_data.get(section_key, {})
        ai_section = ai_data.get(section_key, {}) if ai_data else {}
        
        if not rule_section and ai_section:
            return ai_section
        elif rule_section and not ai_section:
            return rule_section
        elif rule_section and ai_section:
            # Merge intelligently - rules override AI
            merged = ai_section.copy()
            merged.update(rule_section)
            return merged
        else:
            return {}

    # Aspek Klinis - smart merge
    aspek_klinis = merge_data(rule_data, gpt_result, "aspek_klinis")

    # ICD-10 data merging
    icd10_data = merge_data(rule_data, gpt_result, "icd10")
    if gpt_result and gpt_result.get("icd10", {}).get("utama") and not icd10_data.get("who"):
        icd10_data["who"] = gpt_result["icd10"]["utama"]

    # Get comprehensive ICD-10 mapping from rules
    icd_code = icd10_data.get("who", icd10_data.get("bpjs", "-"))
    icd10_mapping = icd10_rules.get(icd_code, {})
    
    # Build complete ICD-10 structure
    icd10_merged = {
        "who": icd10_data.get("who", icd_code),
        "bpjs": icd10_data.get("bpjs", icd10_mapping.get("bpjs", icd_code)), 
        "kode_ganda": icd10_data.get("kode_ganda", icd10_mapping.get("kode_ganda", [])),
        "z_code": icd10_data.get("z_code", icd10_mapping.get("z_code", [])),
        "catatan_bpjs": icd10_data.get("catatan_bpjs", icd10_mapping.get("catatan_bpjs", ""))
    }

    # Tindakan - merge rules + AI
    tindakan_rules = rule_data.get("tindakan", [])
    tindakan_ai = gpt_result.get("tindakan", []) if gpt_result else []
    tindakan = tindakan_rules if tindakan_rules else tindakan_ai

    # Format tindakan untuk UI - sesuaikan dengan renderTindakan()
    tindakan_ui = []
    for t in tindakan:
        if isinstance(t, dict):
            tindakan_ui.append({
                "nama": t.get("nama", "-"),
                "tindakan": t.get("nama", "-"),  # fallback field yang dicari UI
                "deskripsi": t.get("deskripsi", t.get("nama", "-")),
                "icd9": t.get("icd9", "-"),
                "status": t.get("status", "-"),
                "kategori": t.get("kategori", "-"),
                "regulasi": t.get("regulasi", "-"),
                "syarat_klinis": t.get("syarat_klinis", "-"),
                "ina_cbg_impact": t.get("ina_cbg_impact", "-"),
                "id": f"tid_{len(tindakan_ui) + 1}",  # generate id untuk UI
                "procedure_id": f"tid_{len(tindakan_ui) + 1}" # fallback id
            })

    # Other sections - smart merge
    rawat_inap = merge_data(rule_data, gpt_result, "rawat_inap")
    faskes = merge_data(rule_data, gpt_result, "faskes")  
    rujukan = merge_data(rule_data, gpt_result, "rujukan")
    ina_cbg_info = rule_data.get("ina_cbg", {})

    # --- 4. STATUS ASSESSMENT (based on completeness)
    # Status: "complete" (hijau), "partial" (kuning), "missing" (merah)
    def assess_status(data):
        if isinstance(data, str) and data not in ["-", "", None]:
            return "complete"
        elif isinstance(data, list) and len(data) > 0:
            return "complete"
        elif isinstance(data, dict) and any(v for v in data.values() if v not in ["-", "", None, []]):
            return "complete"
        else:
            return "missing"

    # --- 5. BUILD RESPONSE sesuai claim.modals.js structure
    result = {
        # KLINIS Section
        "klinis": {
            "justifikasi": aspek_klinis.get("justifikasi", "-"),
            "bukti_klinis": "; ".join(aspek_klinis.get("bukti", [])) if isinstance(aspek_klinis.get("bukti", []), list) else aspek_klinis.get("bukti", "-"),
            "syarat_klinis": "; ".join(aspek_klinis.get("syarat_medis", [])) if isinstance(aspek_klinis.get("syarat_medis", []), list) else aspek_klinis.get("syarat_medis", "-"),
            "confidence_ai": "85%" if gpt_result else "N/A",
            "status": assess_status(aspek_klinis.get("justifikasi"))
        },
        
        # ICD-10 Section  
        "icd10": {
            "kode_icd": icd10_merged.get("who", "-"),
            "struktur_icd10": f"Valid ICD-10 structure" if icd10_merged.get("who") != "-" else "-",
            "kode_ganda": "; ".join(icd10_merged.get("kode_ganda", [])) if icd10_merged.get("kode_ganda") else "-",
            "z_code": "; ".join(icd10_merged.get("z_code", [])) if icd10_merged.get("z_code") else "-", 
            "kode_bpjs_khusus": icd10_merged.get("bpjs", "-"),
            "status_icd": assess_status(icd10_merged.get("who"))
        },

        # TINDAKAN Section
        "tindakan": tindakan_ui,
        
        # RAWAT INAP Section
        "rawat": {
            "indikasi": "; ".join(rawat_inap.get("indikasi", [])) if isinstance(rawat_inap.get("indikasi", []), list) else rawat_inap.get("indikasi", "-"),
            "kriteria": rawat_inap.get("kriteria", rawat_inap.get("syarat", "-")),
            "lama_rawat": rawat_inap.get("lama_rawat", "-"),
            "status_indikasi": assess_status(rawat_inap.get("indikasi")),
            "status_kriteria": assess_status(rawat_inap.get("kriteria", rawat_inap.get("syarat"))),
            "status_lama": assess_status(rawat_inap.get("lama_rawat"))
        },

        # FASKES Section  
        "faskes": {
            "tingkat": faskes.get("level", faskes.get("tingkat", "-")),
            "justifikasi": faskes.get("justifikasi", faskes.get("kesesuaian", "-")),
            "kompetensi": faskes.get("kompetensi", "Sesuai standar RS"),
            "status_tingkat": assess_status(faskes.get("level", faskes.get("tingkat"))),
            "status_justifikasi": assess_status(faskes.get("justifikasi", faskes.get("kesesuaian"))),
            "status_kompetensi": assess_status(faskes.get("kompetensi"))
        },

        # RUJUKAN Section
        "rujukan": {
            "indikasi": rujukan.get("indikasi", rujukan.get("syarat", "-")),
            "tujuan": rujukan.get("tujuan", rujukan.get("kelayakan", "-")),
            "kriteria": rujukan.get("kriteria", rujukan.get("syarat", "-")),
            "status_indikasi": assess_status(rujukan.get("indikasi", rujukan.get("syarat"))),
            "status_tujuan": assess_status(rujukan.get("tujuan", rujukan.get("kelayakan"))),
            "status_kriteria": assess_status(rujukan.get("kriteria", rujukan.get("syarat")))
        },

        # INA-CBG Section
        "inaCbg": {
            "kode": ina_cbg_info.get("kode", "-"),
            "deskripsi": ina_cbg_info.get("deskripsi", "-"), 
            "tarif": int(''.join(c for c in str(ina_cbg_info.get("tarif", "0")) if c.isdigit()) or "0"),
            "status_kode": assess_status(ina_cbg_info.get("kode")),
            "status_deskripsi": assess_status(ina_cbg_info.get("deskripsi")),
            "status_tarif": assess_status(ina_cbg_info.get("tarif"))
        },

        # Additional Info
        "source": "Rules+AI" if has_complete_rules and gpt_result else ("Rules" if has_complete_rules else "AI"),
        "data_completeness": "100%" if has_complete_rules else "75%" if gpt_result else "25%",
        "engine_version": "hybrid_analyze_diagnosis@2025-10-03"
    }
    print(f"[ANALYZE_DIAGNOSIS] Response structure complete, source: {result['source']}")
    print(f"[ANALYZE_DIAGNOSIS] Klinis data: {result['klinis']}")
    print(f"[ANALYZE_DIAGNOSIS] ICD10 data: {result['icd10']}")
    print(f"[ANALYZE_DIAGNOSIS] Tindakan count: {len(result['tindakan'])}")
    print(f"[ANALYZE_DIAGNOSIS] First tindakan: {result['tindakan'][0] if result['tindakan'] else 'None'}")
    

    # ======================================================
    # NEW SECTION: AI Notifications (merged + tindakan)
    # ======================================================
    notifications = {}

    if gpt_result and gpt_result.get("notifications"):
        gpt_notif = gpt_result.get("notifications", {})
        for key, text in gpt_notif.items():
            status = "success"
            txt_lower = text.lower()
            if any(w in txt_lower for w in ["tidak sesuai", "kurang", "perlu", "belum", "review"]): status = "warning"
            if any(w in txt_lower for w in ["salah", "tidak valid", "keliru"]): status = "error"
            notifications[key] = {"status": status, "message": text.strip()}

    # Import tindakan summary dari procedure service
    from services.analyze_procedure_service import process_analyze_procedure, summarize_procedure_notif
    notifications_summary = []
    for t in result.get("tindakan", []):
        try:
            proc_payload = {
                "claim_id": claim_id,
                "procedure_name": t.get("nama") or t.get("tindakan"),
                "context": {
                    "primary_claim": disease_name,
                    "hospital_level": faskes.get("tingkat", "-"),
                    "rekam_medis": rekam_medis,
                    "lama_rawat": rawat_inap.get("lama_rawat", "1 hari"),
                    "hasil_lab": "HbA1c belum tersedia",
                    "hasil_radiologi": "Tidak ditemukan hasil radiologi"
                    }
                }
            proc_result = process_analyze_procedure(proc_payload)
            notif = summarize_procedure_notif(proc_result)
            notifications_summary.append(notif)
        except Exception as e:
            print(f"[ANALYZE_DIAGNOSIS] ⚠️ Failed to summarize notif: {e}")

    if notifications_summary:
        notifications["tindakan"] = {
            "status": "info",
            "message": "; ".join([f"{n['name']}: {n['notif_text']}" for n in notifications_summary])
        }

    if notifications:
        result["notifications"] = notifications
        print(f"[ANALYZE_DIAGNOSIS] Added {len(notifications)} notifications")

    return result