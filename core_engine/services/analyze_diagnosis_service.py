import asyncio

def process_analyze_diagnosis(data):
    # Struktur modal detail sesuai kebutuhan frontend
    modal_map = {
        "Demam Berdarah Dengue": {
            "aspek_klinis": {
                "justifikasi": "Demam tinggi 3-5 hari, trombosit menurun, nyeri kepala",
                "bukti": "Laboratorium: trombosit <100.000, Ht naik",
                "syarat": "Gejala klasik DBD"
            },
            "icd10": {
                "struktur_kode": "A91",
                "kode_ganda": "A91.0, A91.1",
                "z_code": "Z20.9",
                "kode_bpjs_khusus": "BPJS-DBD-01"
            },
            "tindakan": "Infus cairan, monitoring laboratorium",
            "rawat_inap": {
                "indikasi": "Syok, trombosit <50.000",
                "lama_rawat": "3-5 hari",
                "perpanjangan": "Jika trombosit belum naik"
            },
            "faskes": {
                "kesesuaian_rs": "RS tipe B/C/D sesuai regulasi"
            },
            "rujukan": {
                "syarat": "Syok tidak membaik",
                "kelayakan": "Perlu ICU"
            }
        },
        "Hipertensi": {
            "aspek_klinis": {
                "justifikasi": "Tekanan darah >140/90 mmHg",
                "bukti": "Riwayat hipertensi, pengukuran TD",
                "syarat": "Pengukuran berulang"
            },
            "icd10": {
                "struktur_kode": "I10",
                "kode_ganda": "I10.0, I10.1",
                "z_code": "Z13.6",
                "kode_bpjs_khusus": "BPJS-HIP-02"
            },
            "tindakan": "Kontrol tekanan darah",
            "rawat_inap": {
                "indikasi": "TD tidak terkontrol",
                "lama_rawat": "2-3 hari",
                "perpanjangan": "Jika TD tetap tinggi"
            },
            "faskes": {
                "kesesuaian_rs": "RS tipe C/D"
            },
            "rujukan": {
                "syarat": "Komplikasi organ target",
                "kelayakan": "Perlu perawatan lanjutan"
            }
        },
        "Diabetes Mellitus": {
            "aspek_klinis": {
                "justifikasi": "Gula darah >200 mg/dL",
                "bukti": "Laboratorium: GDP/GDS tinggi",
                "syarat": "Riwayat DM"
            },
            "icd10": {
                "struktur_kode": "E11",
                "kode_ganda": "E11.0, E11.1",
                "z_code": "Z79.4",
                "kode_bpjs_khusus": "BPJS-DM-03"
            },
            "tindakan": "Kontrol gula darah",
            "rawat_inap": {
                "indikasi": "Hiperglikemia berat",
                "lama_rawat": "3 hari",
                "perpanjangan": "Jika belum stabil"
            },
            "faskes": {
                "kesesuaian_rs": "RS tipe C/D"
            },
            "rujukan": {
                "syarat": "Komplikasi akut",
                "kelayakan": "Perlu perawatan intensif"
            }
        },
        "Syok Dengue": {
            "aspek_klinis": {
                "justifikasi": "Syok, tekanan darah turun, tanda perdarahan",
                "bukti": "Laboratorium: Ht naik, trombosit turun",
                "syarat": "Syok refrakter"
            },
            "icd10": {
                "struktur_kode": "A91.1",
                "kode_ganda": "A91.1, A91.2",
                "z_code": "Z51.0",
                "kode_bpjs_khusus": "BPJS-DBD-02"
            },
            "tindakan": "Resusitasi cairan",
            "rawat_inap": {
                "indikasi": "Syok berat",
                "lama_rawat": "5 hari",
                "perpanjangan": "Jika belum stabil"
            },
            "faskes": {
                "kesesuaian_rs": "RS tipe B/C"
            },
            "rujukan": {
                "syarat": "Syok tidak membaik",
                "kelayakan": "Perlu ICU"
            }
        },
        "Perdarahan GI": {
            "aspek_klinis": {
                "justifikasi": "Perdarahan saluran cerna",
                "bukti": "Hematemesis/Melena",
                "syarat": "Endoskopi diperlukan"
            },
            "icd10": {
                "struktur_kode": "K92.2",
                "kode_ganda": "K92.2, K92.1",
                "z_code": "Z51.1",
                "kode_bpjs_khusus": "BPJS-GI-04"
            },
            "tindakan": "Transfusi darah",
            "rawat_inap": {
                "indikasi": "Perdarahan masif",
                "lama_rawat": "5 hari",
                "perpanjangan": "Jika perdarahan berulang"
            },
            "faskes": {
                "kesesuaian_rs": "RS tipe B/C"
            },
            "rujukan": {
                "syarat": "Perdarahan tidak berhenti",
                "kelayakan": "Perlu perawatan lanjutan"
            }
        },
    }
    detail = modal_map.get(data.diagnosis_text, {
        "aspek_klinis": {"justifikasi": "-", "bukti": "-", "syarat": "-"},
        "icd10": {"struktur_kode": "-", "kode_ganda": "-", "z_code": "-", "kode_bpjs_khusus": "-"},
        "tindakan": "-",
        "rawat_inap": {"indikasi": "-", "lama_rawat": "-", "perpanjangan": "-"},
        "faskes": {"kesesuaian_rs": "-"},
        "rujukan": {"syarat": "-", "kelayakan": "-"}
    })
    # Pastikan tindakan selalu array of object {nama: ...}
    if isinstance(detail.get("tindakan"), str):
        detail["tindakan"] = [{"nama": detail["tindakan"]}]
    elif isinstance(detail.get("tindakan"), list):
        detail["tindakan"] = [{"nama": td} if isinstance(td, str) else td for td in detail["tindakan"]]
    return detail
