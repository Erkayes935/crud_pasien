import random

def process_analyze_claim(data):
    # Dummy logic, bisa diganti AI
    return {
        "simulasi": {
            "diagnosis_utama": data.primary,
            "diagnosis_sekunder": data.secondary,
            "tindakan_utama": data.procedures[0] if data.procedures else "Infus cairan",
            "tindakan_sekunder": data.procedures[1:] if len(data.procedures) > 1 else ["Monitoring laboratorium"],
            "tarif_draft": random.randint(3_000_000, 8_000_000)
        },
        "summary": {
            "status": "valid",
            "message": "Kombinasi valid secara medis dan sesuai regulasi.",
            "confidence": 0.95,
            "target": "Klaim disetujui",
            "medis": ["Diagnosis dan tindakan sesuai PNPK"],
            "regulasi": ["Sesuai regulasi BPJS"],
            "tarif": ["Tarif sesuai standar"]
        }
    }
