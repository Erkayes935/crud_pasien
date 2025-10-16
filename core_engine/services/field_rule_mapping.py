"""
Universal field-rule mapping untuk semua domain multilayer AI-Claim:
- Detail Diagnosis
- Detail Tindakan
- Detail Kombinasi Klaim (i-DRG / INA-CBG)
- Detail Regulasi

Update: 2025-10-13
"""

FIELD_RULE_MAP = {

    # ==============================================================
    # 🩺 DOMAIN: DIAGNOSIS
    # ==============================================================
    "diagnosis": {
        # --- Aspek Klinis ---
        "justifikasi": {
            "source": "AI", "layers": [], "type": "ai",
            "desc": "Justifikasi klinis diagnosis — bisa dari Permenkes, CP, RS, atau AI."
        },
        "syarat_klinis": {
            "source": "Rule", "layers": [2, 3, 4, 5], "type": "rule",
            "desc": "Syarat klinis diagnosis (gejala, tanda, hasil penunjang)."
        },
        "bukti_klinis": {
            "source": "AI", "layers": [], "type": "ai",
            "desc": "Daftar bukti yang diambil AI dari rekam medis (gejala, hasil lab, radiologi)."
        },

        # --- ICD-10 / Teknis ---
        "kode_icd": {
            "source": "Rule", "layers": [2], "type": "rule",
            "desc": "Kode ICD-10 nasional + bridging BPJS."
        }, 
        "struktur_icd10": {
            "source": "Rule", "layers": [2], "type": "rule",
            "desc": "Struktur/deskripsi resmi kode ICD-10."
        },
        "kode_ganda": {
            "source": "Rule", "layers": [2, 3], "type": "rule", 
            "desc": "Kode ICD-10 sekunder/komorbid yang relevan."
        },
        "kode_bpjs_khusus": {
            "source": "Rule", "layers": [1, 2], "type": "rule",
            "desc": "Kode ICD-10 versi BPJS untuk bridging."
        },
        "z_code": {
            "source": "Rule", "layers": [2, 3], "type": "rule",
            "desc": "Z-code tambahan dari aturan bridging INA-CBG."
        },

        # --- Rawat Inap ---
        "lama_rawat": {
            "source": "Hybrid", "layers": [2, 4, 5], "type": "hybrid",
            "desc": "Durasi rawat berdasarkan CP nasional + kebijakan RS."
        },
        "indikasi": {
            "source": "Rule", "layers": [2, 3], "type": "rule",
            "desc": "Indikasi medis rawat inap."
        },
        "kriteria": {
            "source": "Rule", "layers": [4, 5], "type": "rule",
            "desc": "Kriteria klinis rawat inap."
        },

        # --- Faskes ---
        "faskes_tingkat": {
            "source": "Rule", "layers": [1], "type": "rule",
            "desc": "Level faskes yang boleh menangani (RS A/B/C, puskesmas)."
        },
        "faskes_justifikasi": {
            "source": "AI", "layers": [], "type": "ai",
            "desc": "Penjelasan AI mengapa perlu di faskes tertentu."
        },

        # --- Rujukan ---
        "rujukan_kriteria": {
            "source": "Rule", "layers": [2, 4, 5], "type": "rule",
            "desc": "Syarat rujukan ke faskes lebih tinggi."
        },
        "rujukan_tujuan": {
            "source": "Rule", "layers": [2, 4], "type": "rule",
            "desc": "Tujuan rujukan yang direkomendasikan."
        },

        # --- INA-CBG / Tarif ---
        "ina_cbg_kode": {
            "source": "Rule", "layers": [2, 8], "type": "rule",
            "desc": "Kode INA-CBG resmi dari grouper nasional."
        },
        "ina_cbg_tarif": {
            "source": "Hybrid", "layers": [2, 5, 8], "type": "hybrid",
            "desc": "Tarif sesuai kombinasi nasional + RS."
        },

        # --- Fraud / Temporary ---
        "fraud_alert": {
            "source": "Rule", "layers": [7], "type": "rule",
            "desc": "Deteksi fraud untuk diagnosis ini."
        },
        "temporary_policy": {
            "source": "Rule", "layers": [8], "type": "rule",
            "desc": "Kebijakan sementara (masa transisi, pandemi, dll)."
        },
    },


    # ==============================================================
    # 💊 DOMAIN: TINDAKAN (PROCEDURE)
    # ==============================================================
    "tindakan": {
        "kode_icd9": {
            "source": "Rule", "layers": [2], "type": "rule",
            "desc": "Kode ICD-9 resmi sesuai WHO/BPJS."
        },
        "deskripsi_icd9": {
            "source": "Rule", "layers": [2], "type": "rule",
            "desc": "Deskripsi lengkap kode ICD-9-CM."
        },
        "validitas": {
            "source": "Hybrid", "layers": [2, 3], "type": "hybrid",
            "desc": "Validasi relevansi tindakan terhadap diagnosis (AI + Rule)."
        },
        "status_tindakan": {
            "source": "Rule", "layers": [2, 3, 5], "type": "rule",
            "desc": "Status wajib/opsional/minor tindakan (CP, PPK RS)."
        },
        "syarat_klinis_tindakan": {
            "source": "Rule", "layers": [2, 3, 5], "type": "rule",
            "desc": "Syarat pelaksanaan tindakan medis."
        },
        "faskes": {
            "source": "Rule", "layers": [1], "type": "rule",
            "desc": "Validasi kewenangan tindakan di level RS."
        },
        "rawat_inap": {
            "source": "Hybrid", "layers": [2, 5], "type": "hybrid",
            "desc": "Kebutuhan rawat inap dan lama LOS."
        },
        "ina_cbg_tarif": {
            "source": "Rule", "layers": [2, 8], "type": "rule",
            "desc": "Dampak terhadap tarif INA-CBG / i-DRG."
        },
        "ai_reason": {
            "source": "AI", "layers": [], "type": "ai",
            "desc": "Penjelasan AI mengapa tindakan dipilih."
        },
        "ai_confidence": {
            "source": "AI", "layers": [], "type": "ai",
            "desc": "Confidence level AI untuk tindakan ini."
        },
        "fraud_check": {
            "source": "Rule", "layers": [7], "type": "rule",
            "desc": "Pendeteksian tindakan berlebih atau tidak sesuai indikasi."
        },
        "policy_note": {
            "source": "Rule", "layers": [8], "type": "rule",
            "desc": "Kebijakan sementara terkait tarif i-DRG atau uji coba."
        },
    },

    # ==============================================================
    # ⚙️ DOMAIN: KOMBINASI KLAIM (Evaluasi Diagnosis + Tindakan + Alternatif)
    # ==============================================================
    "kombinasi": {
        # ----- Evaluasi Kombinasi Diagnosis -----
        "validitas_klinis": {
            "source": "Hybrid", "layers": [2, 3], "type": "hybrid",
            "desc": "Apakah kombinasi diagnosis utama + sekunder sah menurut CP/PNPK/PPK RS/Regional."
        },
        "severity": {
            "source": "Hybrid", "layers": [2, 8], "type": "hybrid",
            "desc": "Tingkat keparahan kombinasi (AI + rule severity i-DRG/INA-CBG)."
        },
        "kode_ina_cbg": {
            "source": "Rule", "layers": [2], "type": "rule",
            "desc": "Kode INA-CBG untuk kombinasi diagnosis/tindakan."
        },
        "estimasi_tarif": {
            "source": "Hybrid", "layers": [2, 5], "type": "hybrid",
            "desc": "Tarif klaim (rule dasar + penyesuaian AI/RS)."
        },
        "syarat_klinis": {
            "source": "Rule", "layers": [2, 3, 4, 5], "type": "rule",
            "desc": "Daftar syarat klinis kombinasi."
        },
        "evaluasi_faskes": {
            "source": "Rule", "layers": [1, 4], "type": "rule",
            "desc": "Validasi kewenangan faskes (Permenkes/Regional)."
        },
        "rawat_inap": {
            "source": "Hybrid", "layers": [2, 5], "type": "hybrid",
            "desc": "Durasi rawat yang sesuai severity."
        },

        # ----- Evaluasi Kombinasi Tindakan -----
        "tindakan_wajib": {
            "source": "Rule", "layers": [2, 3, 5], "type": "rule",
            "desc": "Tindakan wajib berdasarkan CP/PPK RS."
        },
        "validasi_pilihan": {
            "source": "Hybrid", "layers": [2, 3, 4, 5], "type": "hybrid",
            "desc": "Validasi tindakan yang dipilih oleh verifikator."
        },
        "dampak_tarif": {
            "source": "Hybrid", "layers": [2, 8], "type": "hybrid",
            "desc": "Pengaruh tindakan terhadap tarif (severity naik/turun)."
        },
        "konflik_duplikasi": {
            "source": "AI", "layers": [7], "type": "ai",
            "desc": "Pendeteksian duplikasi/konflik tindakan oleh AI Fraud Engine."
        },

        # ----- Alternatif Kombinasi -----
        "alternatif_klaim": {
            "source": "AI", "layers": [], "type": "ai",
            "desc": "Simulasi alternatif kombinasi klaim (what-if)."
        }
    },

    # ==============================================================
    # 📘 DOMAIN: REGULASI
    # ==============================================================
    "regulasi": {
        "sumber_dokumen": {
            "source": "Rule", "layers": [1, 2, 3, 4, 5, 6, 7, 8], "type": "rule",
            "desc": "Referensi regulasi (PNPK, CP, Permenkes, SE BPJS, dsb)."
        },
        "status_regulasi": {
            "source": "Rule", "layers": [1, 2, 8], "type": "rule",
            "desc": "Status regulasi: official / unverified / temporary."
        },
        "tanggal_update": {
            "source": "Rule", "layers": [1, 2, 3, 4, 5, 6, 7, 8], "type": "rule",
            "desc": "Tanggal terakhir update aturan."
        },
        "isi_regulasi": {
            "source": "Rule", "layers": [1, 2, 3, 4, 5], "type": "rule",
            "desc": "Isi aturan / pasal regulasi."
        },
        "cakupan": {
            "source": "Rule", "layers": [3, 4, 5], "type": "rule",
            "desc": "Cakupan penerapan (nasional, regional, RS)."
        },
        "ai_summary": {
            "source": "AI", "layers": [], "type": "ai",
            "desc": "Ringkasan singkat AI atas isi regulasi."
        },
    },

    # ==============================================================
    # 🏥 DOMAIN: i-DRG
    # ==============================================================
    "idrg": {
        "kode_idrg": {
            "source": "Rule", "layers": [2, 8], "type": "rule",
            "desc": "Kode i-DRG resmi dari grouper nasional."
        },
        "severity_index": {
            "source": "Hybrid", "layers": [2, 3, 8], "type": "hybrid",
            "desc": "Level keparahan kasus menurut i-DRG (1-4)."
        },
        "checklist_dokumentasi": {
            "source": "Rule", "layers": [2, 8], "type": "rule",
            "desc": "Syarat dokumen untuk validasi i-DRG."
        },
        "faktor_penentu_severity": {
            "source": "Hybrid", "layers": [2, 3], "type": "hybrid",
            "desc": "Faktor utama yang menentukan level severity i-DRG."
        },
        "ungroupable_alert": {
            "source": "Rule", "layers": [2, 8], "type": "rule",
            "desc": "Peringatan klaim tidak masuk group i-DRG."
        },
        "estimasi_tarif_idrg": {
            "source": "Rule", "layers": [2, 8], "type": "rule", 
            "desc": "Tarif sesuai i-DRG nasional."
        },
        "gap_analysis": {
            "source": "Hybrid", "layers": [2, 8], "type": "hybrid",
            "desc": "Selisih tarif i-DRG dengan INA-CBG lama."
        },
        "rekomendasi_ai": {
            "source": "AI", "layers": [], "type": "ai",
            "desc": "Rekomendasi AI untuk optimasi dokumentasi."
        },
    },
}

# ==============================================================
# 🔁 FIELD NAME ALIAS MAP
# ==============================================================
# Menjembatani nama field di backend/UI ↔ nama field di database (rules_master.field)
# Digunakan oleh semua domain: diagnosis, tindakan, kombinasi, regulasi.
# ==============================================================
FIELD_NAME_ALIAS = {

    # ======================================================
    # 🩺 DIAGNOSIS
    # ======================================================
    "justifikasi": ["justifikasi", "diagnosis.justifikasi", "diagnosis.terapi", "diagnosis.validitas"],
    "syarat_klinis": ["syarat_klinis", "diagnosis.syarat_klinis", "pemeriksaan.laboratorium", "pemeriksaan.ct_scan"],
    "bukti_klinis": ["bukti_klinis", "diagnosis.bukti_klinis", "diagnosis.pemeriksaan", "pemeriksaan.radiologi", "pemeriksaan.penunjang", "bukti"],
    # ICD-10
    "kode_icd": ["utama", "who", "kode", "icd10_kode"],
    "struktur_icd10": ["struktur", "nama", "desc", "deskripsi"],
    "kode_ganda": ["kode_tambahan", "komorbid", "secondary"],
    "z_code": ["z_codes", "z"],
    "kode_bpjs_khusus": ["bpjs", "khusus", "kode_bpjs"],
    # Rawat Inap
    "lama_rawat": [
        "lama_rawat", 
        "rawat_inap.lama_rawat", 
        "rawat_inap.durasi", 
        "los",  # Common hospital term
        "length_of_stay",
        "duration",
        "days",
        "rawat.lama"  # Additional possible path
    ],
    "indikasi": ["indikasi", "rawat_inap.indikasi"],
    "kriteria": ["kriteria", "rawat_inap.kriteria", "rawat_inap.monitoring"],
    # Faskes
    "faskes_tingkat": ["faskes_tingkat", "faskes.tipe_rs", "faskes.kewenangan"],
    "faskes_justifikasi": ["faskes_justifikasi", "faskes.kesesuaian"],
    # Rujukan
    "rujukan_kriteria": ["kriteria", "syarat", "indikasi_rujuk"],
    "rujukan_tujuan": ["tujuan", "kelayakan", "destinasi"],
    "indikasi_rujukan": ["indikasi", "alasan", "sebab"],
    # INA-CBG / Tarif
    "ina_cbg_kode": ["ina_cbg_kode", "ina_cbg.kode", "grouper.kode"],
    "ina_cbg_tarif": ["ina_cbg_tarif", "tarif.ina_cbg", "tarif.idrg"],
    # Fraud & Temporary
    "fraud_alert": ["fraud_alert", "fraud.los_anomaly", "validasi.anomali", "fraud.pattern_detection"],
    "temporary_policy": ["temporary_policy", "temporary.emergency_extension", "temporary.pandemic_protocol"],

    # ======================================================
    # 💊 TINDAKAN / PROCEDURE
    # ======================================================
    "kode_icd9": ["kode_icd9", "tindakan.kode_icd9", "teknis.kode_icd"],
    "deskripsi_icd9": ["deskripsi_icd9", "tindakan.deskripsi", "deskripsi"],
    "validitas": ["validitas", "tindakan.validitas", "pemeriksaan.kultur"],
    "status_tindakan": ["status_tindakan", "tindakan.status", "terapi.standar"],
    "syarat_klinis_tindakan": [
        "syarat_klinis_tindakan", 
        "rawat_inap.lama_rawat", 
        "tindakan.syarat_klinis", 
        "pemeriksaan.kultur"
    ],
    "faskes": ["faskes", "faskes.tipe_rs", "faskes.kewenangan"],
    "rawat_inap": ["rawat_inap", "rawat_inap.indikasi", "rawat_inap.lama_rawat"],
    "ina_cbg_tarif": ["ina_cbg_tarif", "tarif.ina_cbg", "tarif.idrg"],
    "ai_reason": ["ai_reason", "ai.reasoning", "alasan_ai"],
    "ai_confidence": ["ai_confidence", "confidence_ai"],
    "fraud_check": ["fraud_check", "fraud.los_anomaly", "validasi.anomali"],
    "policy_note": ["policy_note", "temporary.idrg_transition", "temporary.pandemic_protocol"],

    # ======================================================
    # ⚙️ KOMBINASI KLAIM (i-DRG / INA-CBG)
    # ======================================================
    "validitas_klinis": ["validitas_klinis", "diagnosis.validitas", "kombinasi.validitas"],
    "severity": ["severity", "kombinasi.severity"],
    "kode_ina_cbg": ["kode_ina_cbg", "grouper.kode"],
    "estimasi_tarif": ["estimasi_tarif", "tarif.ina_cbg"],
    "syarat_klinis": ["syarat_klinis", "diagnosis.syarat_klinis", "kombinasi.syarat_klinis"],
    "evaluasi_faskes": ["evaluasi_faskes", "faskes.kewenangan"],
    "rawat_inap": ["rawat_inap", "rawat_inap.lama_rawat"],
    "tindakan_wajib": ["tindakan_wajib", "tindakan.status"],
    "validasi_pilihan": ["validasi_pilihan", "tindakan.validasi"],
    "dampak_tarif": ["dampak_tarif", "tarif.ina_cbg"],
    "konflik_duplikasi": ["konflik_duplikasi", "fraud.pattern"],

    # ======================================================
    # 📘 REGULASI
    # ======================================================
    "sumber_dokumen": ["sumber_dokumen", "regulasi.sumber", "dokumen.sumber"],
    "status_regulasi": ["status_regulasi", "regulasi.status", "status"],
    "tanggal_update": ["tanggal_update", "regulasi.tanggal_update", "updated_at"],
    "isi_regulasi": ["isi_regulasi", "regulasi.isi", "aturan.detail"],
    "cakupan": ["cakupan", "regulasi.cakupan", "ruang_lingkup"],
    "ai_summary": ["ai_summary", "regulasi.ringkasan", "summary_ai"],

    # ======================================================
    # 🏥 i-DRG
    # ======================================================
    "kode_idrg": [
        "kode_idrg", "group_idrg", "idrg_code", "prediksi_group_idrg", 
        "prediksi_group_idrg_kombinasi", "group_idrg_kombinasi"
    ],
    "severity_index": [
        "severity_index", "severity", "tingkat_keparahan", "severity_level", 
        "severity_kombinasi"
    ],
    "checklist_dokumentasi": [
        "checklist_dokumentasi", "checklist_idrg", "syarat_dokumentasi",
        "checklist_idrg_kombinasi"
    ],
    "faktor_penentu_severity": [
        "faktor_penentu_severity", "severity_factors", "faktor_severity"
    ],
    "ungroupable_alert": [
        "ungroupable_alert", "risiko_ungroupable", "ungroupable_risk", "ungroupable"
    ],
    "estimasi_tarif_idrg": [
        "estimasi_tarif_idrg", "tarif_idrg", "estimasi_tarif", "tarif", 
        "idrg_tariff", "tarif.idrg"
    ],
    "gap_analysis": [
        "gap_analysis", "gap_with_inacbg", "selisih_tarif"
    ],
    "rekomendasi_ai": [
        "rekomendasi_ai", "ai_recommendation", "ai_summary", "rekomendasi"
    ],
}

def match_field_alias(field_name: str, db_field: str) -> bool:
    """Cek apakah nama field backend cocok dengan salah satu alias di database."""
    aliases = FIELD_NAME_ALIAS.get(field_name, [field_name])
    return any(db_field.endswith(alias) or db_field == alias for alias in aliases)
