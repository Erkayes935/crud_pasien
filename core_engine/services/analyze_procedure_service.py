# services/analyze_procedure_service.py
import os, json
from datetime import date
from typing import Any, Dict, List, Optional
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def _sv(x: Any, default: str = "-") -> str:
    return x.strip() if isinstance(x, str) and x.strip() else default

def process_analyze_procedure(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    HYBRID Procedure Analysis: Rules priority + OpenAI fallback
    
    Input:
      { "claim_id": 56, "procedure_name": "Ventilasi Mekanik" }

    Output untuk claim.modals.js renderProcBox():
      {
        "icd9_code": "...",        # renderProcBox("Kode ICD-9", d.icd9_code || d.icd9, "icd9_code")
        "icd9_desc": "...",        # renderProcBox("Deskripsi", d.icd9_desc || d.deskripsi, "deskripsi") 
        "deskripsi": "...",        # fallback untuk icd9_desc
        "validitas": "...",        # renderProcBox("Validitas", d.validitas, "validitas")
        "status": "...",           # renderProcBox("Status", d.status_tindakan || d.status, "status")
        "status_tindakan": "...",  # primary status field
        "ina_cbg": "...",          # renderProcBox("INA-CBG", d.ina_cbg_tarif || d.ina_cbg, "ina_cbg")
        "ina_cbg_tarif": "...",    # primary ina_cbg field
        "faskes": "...",           # renderProcBox("Faskes", d.faskes, "faskes")
        "rawat_inap": "...",       # renderProcBox("Rawat Inap", d.rawat_inap, "rawat_inap")
        "syarat_klinis": "...",    # renderProcBox("Syarat Klinis", d.syarat_klinis, "syarat_klinis")
        "engine_version": "hybrid_analyze_procedure@YYYY-MM-DD"
      }
    """
    claim_id = payload.get("claim_id")
    procedure = payload.get("procedure_name") or payload.get("procedure") or ""
    stage = (payload.get("stage") or "admission").strip()

    print(f"[ANALYZE_PROCEDURE] Processing: {procedure}")

    # --- 1. CHECK RULES: Load procedure rules jika ada
    # TODO: Implementasi rules_loader untuk procedures
    # rule_data = load_procedure_rule(procedure)
    rule_data = {}  # Sementara kosong, bisa ditambah nanti

    # --- 2. ALWAYS GET AI ANALYSIS (karena rules procedure belum ada)
    print(f"[ANALYZE_PROCEDURE] Requesting OpenAI analysis for: {procedure}")
    
    # konteks opsional (boleh kosong)
    ctx = payload.get("context") or {}
    dx_pri = ctx.get("primary_claim", "")
    dx_sec = ctx.get("secondary_claims", [])
    act_pri = ctx.get("primary_action", "")
    act_sec = ctx.get("secondary_actions", [])
    hospital_level = ctx.get("hospital_level", "")
    patient_context = ctx.get("patient_context", "")

    # Enhanced prompt untuk hasil yang sesuai dengan modal structure
    prompt = f"""
    Anda adalah spesialis coding medis dan konsultan BPJS Indonesia.
    
    ANALISIS TINDAKAN: {procedure}
    DIAGNOSIS PRIMER: {dx_pri}
    KONTEKS: Claim {claim_id}, Stage: {stage}, RS: {hospital_level}
    
    Berikan analisis komprehensif dalam format JSON:
    {{
      "procedure": "{procedure}",
      "icd9_code": "Kode ICD-9-CM yang akurat sesuai WHO/BPJS",
      "icd9_desc": "Deskripsi lengkap ICD-9-CM Indonesia",
      "deskripsi": "Penjelasan detail tindakan medis",
      "validitas": "VALID/TIDAK VALID/PERLU REVIEW + alasan klinis yang jelas",
      "status_tindakan": "WAJIB/OPSIONAL/SUPPORTIVE + justifikasi berdasarkan CP/PNPK",
      "status": "Status singkat untuk tampilan UI",
      "ina_cbg_tarif": "Dampak ke tarif INA-CBG atau estimasi biaya Rp",
      "ina_cbg": "Impact grouping ringkas",
      "faskes": "Level RS yang sesuai (A/B/C/Puskesmas) + alasan kapasitas",
      "rawat_inap": "Indikasi rawat inap: WAJIB/TIDAK/CONDITIONAL + syarat",
      "syarat_klinis": "Persyaratan medis/lab/imaging yang diperlukan sebelum tindakan"
    }}

    PEDOMAN ANALISIS:
    - ICD-9-CM harus sesuai standar internasional dan mapping BPJS
    - Validitas berdasarkan kesesuaian dengan diagnosis dan indikasi medis
    - Status tindakan mengacu pada CP/PNPK dan panduan klinis nasional
    - Tarif mengacu pada INA-CBG terbaru dan realitas biaya RS Indonesia
    - Level faskes sesuai Permenkes tentang klasifikasi dan kapasitas RS
    - Syarat klinis harus spesifik dan dapat diverifikasi
    - Semua field wajib diisi dengan informasi yang berguna, hindari "-" atau kosong
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Anda adalah konsultan medis dan coding specialist BPJS. Jawab hanya dalam format JSON yang valid."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}  # Ensure JSON output
        )

        raw = (response.choices[0].message.content or "").strip()
        print(f"[ANALYZE_PROCEDURE] OpenAI response received for: {procedure}")
        print(f"[DEBUG] Raw OpenAI response: {raw[:500]}...")
        
        try:
            ai_data = json.loads(raw)
            print(f"[ANALYZE_PROCEDURE] JSON parsed successfully")
            print(f"[DEBUG] ina_cbg_tarif from OpenAI: '{ai_data.get('ina_cbg_tarif')}' (type: {type(ai_data.get('ina_cbg_tarif'))})")
            print(f"[DEBUG] ina_cbg from OpenAI: '{ai_data.get('ina_cbg')}' (type: {type(ai_data.get('ina_cbg'))})")
        except Exception as parse_error:
            print(f"[ANALYZE_PROCEDURE] JSON parse error: {parse_error}")
            ai_data = {}

    except Exception as api_error:
        print(f"[ANALYZE_PROCEDURE] OpenAI API error: {api_error}")
        ai_data = {}

    # --- 3. BUILD RESPONSE sesuai claim.modals.js structure
    # Ensure all fields that modal expects are present
    result = {
        # Core procedure info
        "procedure": _sv(ai_data.get("procedure", procedure), procedure or "-"),
        
        # ICD-9 fields (both primary and fallback)
        "icd9_code": _sv(ai_data.get("icd9_code", "")),
        "icd9": _sv(ai_data.get("icd9_code", "")),  # fallback for d.icd9
        "icd9_desc": _sv(ai_data.get("icd9_desc", "")),
        "deskripsi": _sv(ai_data.get("deskripsi", ai_data.get("icd9_desc", ""))),  # fallback
        
        # Status fields (both primary and fallback)
        "validitas": _sv(ai_data.get("validitas", "")),
        "status_tindakan": _sv(ai_data.get("status_tindakan", "")),
        "status": _sv(ai_data.get("status", ai_data.get("status_tindakan", ""))),  # fallback
        
        # INA-CBG fields (both primary and fallback)
        "ina_cbg_tarif": _sv(ai_data.get("ina_cbg_tarif", "")),
        "ina_cbg": _sv(ai_data.get("ina_cbg", ai_data.get("ina_cbg_tarif", ""))),  # fallback
        
        # Other fields
        "faskes": _sv(ai_data.get("faskes", "")),
        "rawat_inap": _sv(ai_data.get("rawat_inap", "")),
        "syarat_klinis": _sv(ai_data.get("syarat_klinis", "")),
        
        # Metadata
        "source": "AI" if ai_data else "Fallback",
        "data_completeness": "100%" if ai_data else "0%",
        "engine_version": f"hybrid_analyze_procedure@{date.today().isoformat()}",
    }
    
    print(f"[ANALYZE_PROCEDURE] Response built successfully for: {procedure}")
    print(f"[DEBUG] Final result ina_cbg_tarif: '{result.get('ina_cbg_tarif')}' | ina_cbg: '{result.get('ina_cbg')}'")
    return result
