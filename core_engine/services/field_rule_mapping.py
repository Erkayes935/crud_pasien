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
        "indikasi_rawat_inap": {
            "source": "Rule", "layers": [2, 3], "type": "rule",
            "desc": "Indikasi medis rawat inap."
        },
        "kriteria_rawat_inap": {
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
        "faskes_kompetensi": {
            "source": "AI", "layers": [1], "type": "rule",
            "desc": "Penjelasan AI mengapa perlu di faskes tertentu."
        },

        # --- Rujukan ---
        "rujukan_indikasi": {
            "source": "Rule", "layers": [1, 2, 4, 5], "type": "rule",
            "desc": "Syarat rujukan ke faskes lebih tinggi."
        },
        "rujukan_kriteria": {
            "source": "Rule", "layers": [1, 2, 4, 5], "type": "rule",
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
    # ⚙️ DOMAIN: KOMBINASI KLAIM (Evaluasi Diagnosis + Tindakan + i-DRG)
    # ==============================================================
    "kombinasi": {
       "validitas_klinis_kombinasi": {
            "alias": ["validitas", "validitas_kombinasi", "kombinasi.validitas"],
            "layers": [2, 3, 4, 5],  # CP/PNPK/Regional/RS
            "desc": "Menilai kesesuaian kombinasi diagnosis dengan aturan CP/RS."
        },
        "severity": {
            "alias": ["severity", "severity_index", "tingkat_keparahan"],
            "layers": [2, 8],  # Nasional + iDRG
            "desc": "Tingkat keparahan kombinasi diagnosis."
        },
        "kode_ina_cbg": {
            "alias": ["kode_cbg", "kode_ina_cbg", "cbg_code", "inacbg.kode"],
            "layers": [2, 6],  # Nasional + Bridging INA-CBG
            "desc": "Mapping kombinasi diagnosis terhadap kode INA-CBG."
        },
        "estimasi_tarif": {
            "alias": ["tarif", "estimasi_tarif", "tarif_idrg"],
            "layers": [2, 4, 5, 8],  # Nasional + Regional + RS + iDRG
            "desc": "Estimasi tarif kombinasi diagnosis."
        },
        "syarat_klinis_kombinasi": {
            "alias": ["syarat_klinis", "syarat_klinis_kombinasi", "syarat_klinis.diagnosis"],
            "layers": [2, 3, 4, 5],  # CP + PNPK + Regional + RS
            "desc": "Syarat klinis yang harus dipenuhi pada kombinasi diagnosis."
        },
        "evaluasi_faskes": {
            "alias": ["faskes", "evaluasi_faskes", "kewenangan_rs"],
            "layers": [1, 2, 5],  # Permenkes + Nasional + RS Lokal
            "desc": "Kewenangan RS sesuai klasifikasi faskes."
        },
        "rawat_inap": {
            "alias": ["rawat_inap", "rawat_inap.lama_rawat", "lama_rawat"],
            "layers": [2, 3, 5],  # CP/PNPK + RS Lokal
            "desc": "Lama rawat dan indikasi rawat inap kombinasi diagnosis."
        },

        # ---------------------------
        # 🔸 Bagian Evaluasi Tindakan
        # ---------------------------
        "tindakan_wajib_kombinasi": {
            "alias": ["tindakan.wajib", "tindakan.status", "tindakan_wajib"],
            "layers": [2, 3, 5],  # CP/PNPK/RS Lokal
            "desc": "Apakah tindakan wajib pada kombinasi diagnosis tertentu."
        },
        "validasi_pilihan": {
            "alias": ["tindakan.validasi", "validasi_pilihan", "tindakan.verifikasi"],
            "layers": [2, 3, 5],  # Nasional + PPK + RS
            "desc": "Validasi tindakan utama/sekunder oleh verifikator."
        },
        "dampak_tarif": {
            "alias": ["dampak_tarif", "tarif", "ina_cbg.tarif", "idrg.tarif"],
            "layers": [2, 4, 8],  # Nasional + Regional + iDRG
            "desc": "Dampak tindakan terhadap tarif INA-CBG/iDRG."
        },
        "konflik_duplikasi": {
            "alias": ["fraud", "konflik", "duplikasi"],
            "layers": [7],  # Fraud layer only
            "desc": "Deteksi potensi konflik atau duplikasi tindakan."
        }, 

        # ---------------------
        # 🏥 Evaluasi i-DRG Kombinasi
        # ---------------------
        "prediksi_group_idrg": {
            "source": "Hybrid", "layers": [2, 8],
            "type": "hybrid",
            "desc": "Group i-DRG hasil pairing ICD-10/9 dan severity."
        },
        "faktor_penentu_severity": {
            "source": "Hybrid", "layers": [2, 3],
            "type": "hybrid",
            "desc": "Faktor penentu severity (sepsis, ventilator > 96 jam, multi-komorbid, dll)."
        },
        "checklist_idrg_kombinasi": {
            "source": "Rule", "layers": [2, 8],
            "type": "rule",
            "desc": "Checklist dokumen wajib untuk grouping i-DRG (kultur, radiologi, resume medis)."
        },
        "ungroupable_alert": {
            "source": "Rule", "layers": [2, 8],
            "type": "rule",
            "desc": "Peringatan klaim tidak dapat dikelompokkan (i-DRG Ungroupable)."
        },
        "estimasi_tarif_idrg": {
            "source": "Rule", "layers": [2, 8],
            "type": "rule",
            "desc": "Estimasi tarif i-DRG nasional atau transisi."
        },
        "gap_tarif": {
            "source": "Hybrid", "layers": [2, 8],
            "type": "hybrid",
            "desc": "Analisis selisih tarif INA-CBG vs i-DRG (positif/negatif)."
        },

        # ---------------------
        # 🧠 Alternatif Kombinasi (AI Simulation)
        # ---------------------
        "alternatif_kombinasi": {
            "source": "AI", "layers": [], "type": "ai",
            "desc": "Simulasi kombinasi diagnosis + tindakan alternatif (what-if scenario)."
        },
        "rekomendasi_verifikator": {
            "source": "AI", "layers": [], "type": "ai",
            "desc": "Rekomendasi singkat AI untuk verifikator (flag success / warning / info)."
        },
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
            "alias": ["gap_analysis", "selisih_tarif"],
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
    "justifikasi": ["justifikasi", "justifikasi_klinis", "diagnosis.justifikasi", "diagnosis.terapi", "diagnosis.validitas"],
    "syarat_klinis": ["syarat_klinis", "syarat_klinis_tindakan", "diagnosis.syarat_klinis", "pemeriksaan.laboratorium", "pemeriksaan.ct_scan"],
    "bukti_klinis": ["bukti_klinis", "diagnosis.bukti_klinis", "diagnosis.pemeriksaan", "pemeriksaan.radiologi", "pemeriksaan.penunjang", "bukti"],
    # ICD-10
    "kode_icd": ["kode_icd10", "utama", "who", "kode", "icd10_kode"],
    "struktur_icd10": ["struktur", "nama", "desc", "deskripsi"],
    "kode_ganda": ["kode_ganda","kode_tambahan", "komorbid", "secondary"],
    "z_code": ["z_code","z_codes", "z"],
    "kode_bpjs_khusus": ["kode_bpjs_khusus","bpjs", "khusus", "kode_bpjs"],
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
    # Rawat Inap fields (shared names)
    "indikasi": ["indikasi", "indikasi_rawat_inap", "rawat_inap.indikasi", "indikasi_rujukan", "alasan", "sebab"],
    "kriteria": ["kriteria_rawat_inap", "kriteria", "rawat_inap.kriteria", "rawat_inap.monitoring", "rujukan_kriteria", "kriteria_rujukan", "syarat", "indikasi_rujuk"],
    # Faskes
    "tingkat": ["tingkat", "faskes_tingkat", "faskes.tipe_rs", "faskes.kewenangan", "level"],
    "justifikasi": ["justifikasi", "faskes_justifikasi", "justifikasi_faskes", "faskes.kesesuaian"],
    "kompetensi": ["kompetensi", "faskes_kompetensi", "kompetensi_faskes", "faskes.kualifikasi"],
    # Rujukan
    "rujukan_indikasi": ["rujukan_indikasi", "indikasi_rujukan", "rujukan.indikasi", "indikasi", "alasan_rujukan", "sebab_rujukan"],
    "rujukan_kriteria": ["rujukan_kriteria", "kriteria_rujukan", "rujukan.kriteria", "kriteria", "syarat_rujukan", "indikasi_rujuk"],
    "rujukan_tujuan": ["rujukan_tujuan", "tujuan_rujukan", "tujuan", "rujukan.tujuan", "kelayakan", "destinasi"],
    # INA-CBG / Tarif
    "kode": ["kode", "kode_inacbg", "ina_cbg_kode", "ina_cbg.kode", "grouper.kode"],
    "tarif": ["tarif", "tarif_inacbg", "ina_cbg_tarif", "tarif.ina_cbg", "tarif.idrg"],
    "deskripsi": ["deskripsi", "desc", "nama", "ina_cbg.deskripsi"],
    # Fraud & Temporary
    "fraud_alert": ["fraud_alert", "fraud.los_anomaly", "validasi.anomali", "fraud.pattern_detection"],
    "temporary_policy": ["temporary_policy", "temporary.emergency_extension", "temporary.pandemic_protocol"],

    # ======================================================
    # 💊 TINDAKAN / PROCEDURE
    # ======================================================
    "kode_icd9": ["kode_icd9", "icd9_code", "tindakan.kode_icd9", "teknis.kode_icd"],
    "deskripsi_icd9": ["deskripsi_icd9", "icd9_desc", "tindakan.deskripsi", "deskripsi"],
    "validitas": ["validitas", "tindakan.validitas", "pemeriksaan.kultur"],
    "status_tindakan": ["status_tindakan", "tindakan.status", "terapi.standar"],
    "syarat_klinis_tindakan": [
        "syarat_klinis_tindakan",
        "syarat_klinis",  # ✅ Tambahkan alias ini!
        "rawat_inap.lama_rawat", 
        "tindakan.syarat_klinis", 
        "pemeriksaan.kultur"
    ],
    "faskes": ["faskes", "faskes.tipe_rs", "faskes.kewenangan"],
    "rawat_inap": ["rawat_inap", "indikasi", "kriteria", "lama_rawat", "rawat_inap.indikasi", "rawat_inap.lama_rawat"],
    "ina_cbg_tarif": ["ina_cbg_tarif", "tarif", "ina_cbg", "tarif.ina_cbg", "tarif.idrg"],
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
