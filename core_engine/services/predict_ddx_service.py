import asyncio
import random

def process_predict_ddx(data):
    # Dummy logic, bisa diganti AI
    admission = {
        "diagnosis": [
            {
                "kategori": "Diagnosis",
                "klinis": "Demam Berdarah Dengue",
                "icd": "A91",
                "score": 0.92,
                "tindakan": "Infus cairan, monitoring laboratorium",
                "detail_modal": {
                    "aspek_klinis": ["Demam tinggi 3-5 hari", "Trombosit menurun", "Nyeri kepala"],
                    "tindakan_disarankan": ["Cairan IV", "Monitoring Ht & Trombosit"],
                    "referensi": {"PNPK": "PNPK-DBD-2022", "Fornas": "FORNAS-2023", "Permenkes": "PMK 52/2016"}
                }
            },
            {
                "kategori": "Diagnosis",
                "klinis": "Tifoid",
                "icd": "A01.0",
                "score": 0.75,
                "tindakan": "Antibiotik, monitoring suhu",
                "detail_modal": {
                    "aspek_klinis": ["Demam >5 hari", "Nyeri perut", "Tes Widal positif"],
                    "tindakan_disarankan": ["Antibiotik", "Monitoring suhu"],
                    "referensi": {"PNPK": "PNPK-Tifoid-2022"}
                }
            },
            {
                "kategori": "Diagnosis",
                "klinis": "Infeksi Virus Nonspesifik",
                "icd": "B34.9",
                "score": 0.60,
                "tindakan": "Observasi, istirahat cukup",
                "detail_modal": {
                    "aspek_klinis": ["Demam ringan", "Tidak ada tanda spesifik"],
                    "tindakan_disarankan": ["Istirahat", "Cairan cukup"],
                    "referensi": {"PNPK": "PNPK-InfeksiVirus-2022"}
                }
            }
        ],
        "komorbid": [
            {
                "kategori": "Komorbid",
                "klinis": "Hipertensi",
                "icd": "I10",
                "score": 0.65,
                "tindakan": "Kontrol tekanan darah",
                "detail_modal": {
                    "aspek_klinis": ["Tekanan darah >140/90 mmHg", "Riwayat hipertensi"],
                    "tindakan_disarankan": ["Monitoring tekanan darah", "Obat antihipertensi"],
                    "referensi": {"PNPK": "PNPK-Hipertensi-2022"}
                }
            },
            {
                "kategori": "Komorbid",
                "klinis": "Diabetes Mellitus",
                "icd": "E11",
                "score": 0.58,
                "tindakan": "Kontrol gula darah",
                "detail_modal": {
                    "aspek_klinis": ["Gula darah >200 mg/dL", "Riwayat DM"],
                    "tindakan_disarankan": ["Monitoring gula darah", "Obat antidiabetik"],
                    "referensi": {"PNPK": "PNPK-DM-2022"}
                }
            },
            {
                "kategori": "Komorbid",
                "klinis": "Penyakit Ginjal Kronis",
                "icd": "N18",
                "score": 0.40,
                "tindakan": "Monitoring fungsi ginjal",
                "detail_modal": {
                    "aspek_klinis": ["GFR <60 ml/min", "Riwayat penyakit ginjal"],
                    "tindakan_disarankan": ["Monitoring fungsi ginjal", "Diet rendah protein"],
                    "referensi": {"PNPK": "PNPK-Ginjal-2022"}
                }
            }
        ],
        "komplikasi": [
            {
                "kategori": "Komplikasi",
                "klinis": "Syok Dengue",
                "icd": "A91.1",
                "score": 0.55,
                "tindakan": "Resusitasi cairan",
                "detail_modal": {
                    "aspek_klinis": ["Syok", "Tekanan darah turun", "Tanda perdarahan"],
                    "tindakan_disarankan": ["Resusitasi cairan", "Transfusi darah"],
                    "referensi": {"PNPK": "PNPK-DBD-2022"}
                }
            },
            {
                "kategori": "Komplikasi",
                "klinis": "Perdarahan GI",
                "icd": "K92.2",
                "score": 0.35,
                "tindakan": "Transfusi darah",
                "detail_modal": {
                    "aspek_klinis": ["Perdarahan saluran cerna", "Hematemesis/Melena"],
                    "tindakan_disarankan": ["Transfusi darah", "Endoskopi"],
                    "referensi": {"PNPK": "PNPK-GI-2022"}
                }
            }
        ]
    }
    return {
        "admission": admission,
        "daily": [],
        "discharge": { "diagnosis": [], "komorbid": [], "komplikasi": [] }
    }
