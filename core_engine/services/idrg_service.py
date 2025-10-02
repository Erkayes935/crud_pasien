# services/idrg_service.py
import os
import json
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def predict_idrg(mode: str, payload: dict):
    """
    Prediksi i-DRG berdasarkan mode:
    - mode="single": untuk detail diagnosis individual
    - mode="combo": untuk kombinasi klaim (multiple diagnosis + procedures)
    """
    
    if mode == "single":
        return predict_single_idrg(payload)
    elif mode == "combo":
        return predict_combo_idrg(payload)
    else:
        return {"error": f"Invalid mode: {mode}"}

def predict_single_idrg(payload: dict):
    """
    Prediksi i-DRG untuk single diagnosis dari modal detail diagnosis
    """
    claim_id = payload.get("claim_id")
    diagnosis_name = payload.get("diagnosis_name", "")
    diagnosis_data = payload.get("diagnosis_data", {})
    
    # Extract relevant clinical data
    justifikasi = diagnosis_data.get("justifikasi", "")
    bukti_klinis = diagnosis_data.get("bukti_klinis", "")
    tindakan = diagnosis_data.get("tindakan", [])
    
    tindakan_names = [t.get("nama", "") for t in tindakan if isinstance(t, dict)]
    
    prompt = f"""
    Kamu adalah expert casemix i-DRG Indonesia.
    
    Data diagnosis:
    - Diagnosis: {diagnosis_name}
    - Justifikasi: {justifikasi}
    - Bukti Klinis: {bukti_klinis}
    - Tindakan: {', '.join(tindakan_names)}
    
    Prediksi i-DRG untuk diagnosis ini dengan format JSON:
    {{
        "kode_idrg": "G-4-13-I",
        "deskripsi": "Prosedur Bedah Saraf Mayor dengan CC",
        "mdc": "04 - Diseases and Disorders of Respiratory System",
        "severity": "Moderate",
        "los_estimate": "4-6 hari",
        "tarif_estimate": 15750000,
        "justifikasi_idrg": "Berdasarkan diagnosis dan tindakan invasif",
        "gap_analysis": "Sesuai kriteria severity dan prosedur"
    }}
    
    Berikan hanya JSON valid tanpa penjelasan tambahan.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Kamu adalah expert i-DRG casemix Indonesia. Respond only in JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        return {
            "mode": "single",
            "claim_id": claim_id,
            "diagnosis": diagnosis_name,
            "idrg_prediction": result,
            "engine_version": f"idrg_service@{date.today().isoformat()}"
        }
        
    except Exception as e:
        return {
            "mode": "single", 
            "claim_id": claim_id,
            "error": str(e),
            "engine_version": f"idrg_service@{date.today().isoformat()}"
        }

def predict_combo_idrg(payload: dict):
    """
    Prediksi i-DRG untuk kombinasi klaim (multiple diagnosis + procedures)
    Untuk verifikator di claim_right.html
    """
    claim_id = payload.get("claim_id")
    primary_diagnosis = payload.get("primary_diagnosis", "")
    secondary_diagnosis = payload.get("secondary_diagnosis", [])
    procedures = payload.get("procedures", [])
    
    prompt = f"""
    Kamu adalah expert casemix i-DRG Indonesia.
    
    Data kombinasi klaim:
    - Diagnosis Utama: {primary_diagnosis}
    - Diagnosis Sekunder: {', '.join(secondary_diagnosis)}
    - Tindakan: {', '.join(procedures)}
    
    Analisis kombinasi ini dan berikan prediksi i-DRG:
    {{
        "kode_idrg": "...",
        "deskripsi": "...",
        "mdc": "...",
        "severity": "...",
        "los_estimate": "...",
        "tarif_estimate": 0,
        "justifikasi_combo": "Berdasarkan kombinasi diagnosis dan prosedur",
        "impact_analysis": "Analisis dampak terhadap grouping",
        "recommendations": ["Rekomendasi 1", "Rekomendasi 2"]
    }}
    
    Berikan hanya JSON valid.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Kamu adalah expert i-DRG casemix Indonesia. Respond only in JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        return {
            "mode": "combo",
            "claim_id": claim_id,
            "primary_diagnosis": primary_diagnosis,
            "idrg_prediction": result,
            "engine_version": f"idrg_service@{date.today().isoformat()}"
        }
        
    except Exception as e:
        return {
            "mode": "combo",
            "claim_id": claim_id, 
            "error": str(e),
            "engine_version": f"idrg_service@{date.today().isoformat()}"
        }