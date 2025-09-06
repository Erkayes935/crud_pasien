def process_generate_claim_combos(data):
    # Dummy logic, bisa diganti AI
    return {
        "rekomendasi": [
            {
                "diagnosis_utama": "Demam Berdarah Dengue",
                "diagnosis_sekunder": ["Hipertensi"],
                "tindakan_utama": "Pemeriksaan Laboratorium",
                "tindakan_sekunder": [],
                "tarif_draft": 3500000,
                "status": "valid"
            },
            {
                "diagnosis_utama": "Demam Berdarah Dengue",
                "diagnosis_sekunder": ["Diabetes Mellitus"],
                "tindakan_utama": "Rawat Inap",
                "tindakan_sekunder": [],
                "tarif_draft": 4200000,
                "status": "warning"
            },
            {
                "diagnosis_utama": "Infeksi Virus Nonspesifik",
                "diagnosis_sekunder": [],
                "tindakan_utama": None,
                "tindakan_sekunder": [],
                "tarif_draft": 0,
                "status": "invalid"
            }
        ]
    }
