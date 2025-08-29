# ========================
# Config Fields for Forms
# ========================

# ------------------------
# Patient
# ------------------------
patient_fields = [
    {"name": "no_ktp", "label": "Nomor KTP", "type": "text"},
    {"name": "no_bpjs", "label": "Nomor BPJS", "type": "text"},
    {"name": "no_rm", "label": "Nomor Rekam Medis", "type": "text"},
    {"name": "nama", "label": "Nama", "type": "text"},
    {"name": "tanggal_lahir", "label": "Tanggal Lahir", "type": "date"},
    {"name": "jenis_kelamin", "label": "Jenis Kelamin", "type": "select",
     "options": [("L", "Laki-laki"), ("P", "Perempuan")]},
    {"name": "alamat", "label": "Alamat", "type": "textarea"},
    {"name": "email", "label": "Email", "type": "email"},
    {"name": "no_hp", "label": "No HP", "type": "text"},
]

# ------------------------
# Claim
# ------------------------
claim_fields = [
    {"name": "obat", "label": "Obat", "type": "text"},
    {"name": "diagnosis_awal", "label": "Diagnosis Awal", "type": "text"},
    {"name": "tanggal_kunjungan", "label": "Tanggal Kunjungan", "type": "date"},
    {"name": "tindakan", "label": "Tindakan", "type": "text"},
    {"name": "kode_icd", "label": "Kode ICD", "type": "text"},
    {"name": "status", "label": "Status", "type": "select",
     "options": [("draft", "Draft"), ("verified", "Verified"), ("submitted", "Submitted")]},
    {"name": "hasil", "label": "Hasil", "type": "text"},
]

# ------------------------
# Hospital
# ------------------------
hospital_fields = [
    {"name": "kode_rs", "label": "Kode RS", "type": "text"},
    {"name": "nama", "label": "Nama Rumah Sakit", "type": "text"},
    {"name": "tipe_rs", "label": "Tipe RS", "type": "text"},
    {"name": "jenis_rs", "label": "Jenis RS", "type": "text"},
    {"name": "alamat", "label": "Alamat", "type": "text"},
    {"name": "telepon", "label": "Telepon", "type": "text"},
    {"name": "email", "label": "Email", "type": "email"},
    {"name": "status_akreditasi", "label": "Status Akreditasi", "type": "text"},
    {"name": "status_bridging", "label": "Status Bridging", "type": "text"},
    {"name": "jumlah_tempat_tidur", "label": "Jumlah Tempat Tidur", "type": "number"},
]

# ------------------------
# Visit
# ------------------------
visit_fields = [
    {"name": "tanggal_kunjungan", "label": "Tanggal Kunjungan", "type": "date"},
    {"name": "jenis_kunjungan", "label": "Jenis Kunjungan", "type": "select",
     "options": [
        ("rawat_jalan", "Rawat Jalan"),
        ("rawat_inap", "Rawat Inap"),
        ("igd", "IGD"),
    ]},
    {"name": "hospital_name", "label": "Rumah Sakit", "type": "text", "readonly_roles": ["admin_rs"]},
    {"name": "doctor_name", "label": "Dokter", "type": "text", "readonly_roles": ["admin_rs"]},
    {"name": "eksternal_id", "label": "ID Eksternal", "type": "text"},
    {"name": "sumber", "label": "Sumber", "type": "text"},
    {"name": "poli", "label": "Poli", "type": "text"},
    {"name": "patient_id", "label": "Pasien", "type": "select", "options": []},  # options diisi backend
]

# ------------------------
# Medical Record
# ------------------------
medical_record_fields = {
    "Umum": [
        {"name": "record_type", "label": "Tipe Rekam Medis", "type": "select",
         "options": [
            ("admission", "Admission Note"),
            ("daily", "Progress / Daily Note"),
            ("discharge", "Discharge Summary"),
        ]},
        {"name": "notes_date", "label": "Tanggal Catatan", "type": "date"},
        {"name": "doctor_name", "label": "Nama Dokter", "type": "text"},
        {"name": "is_final", "label": "Sudah Final", "type": "checkbox"},
    ],
    "Riwayat": [
        {"name": "riwayat_penyakit", "label": "Riwayat Penyakit", "type": "textarea"},
        {"name": "riwayat_pengobatan", "label": "Riwayat Pengobatan", "type": "textarea"},
        {"name": "riwayat_operasi", "label": "Riwayat Operasi", "type": "textarea"},
        {"name": "alergi", "label": "Alergi", "type": "textarea"},
        {"name": "keluhan", "label": "Keluhan", "type": "textarea"},
        {"name": "gejala_lain", "label": "Gejala Lain", "type": "textarea"},
    ],
    "Pemeriksaan": [
        {"name": "td", "label": "Tekanan Darah", "type": "text"},
        {"name": "nadi", "label": "Nadi", "type": "text"},
        {"name": "pernapasan", "label": "Pernapasan", "type": "text"},
        {"name": "suhu", "label": "Suhu", "type": "text"},
        {"name": "spo2", "label": "Saturasi O2", "type": "text"},
        {"name": "berat_badan", "label": "Berat Badan", "type": "text"},
        {"name": "tinggi_badan", "label": "Tinggi Badan", "type": "text"},
    ],
    "Lab & Penunjang": [
        {"name": "hemoglobin", "label": "Hemoglobin", "type": "text"},
        {"name": "leukosit", "label": "Leukosit", "type": "text"},
        {"name": "trombosit", "label": "Trombosit", "type": "text"},
        {"name": "gula_darah", "label": "Gula Darah", "type": "text"},
        {"name": "creatinin", "label": "Creatinin", "type": "text"},
        {"name": "rontgen_thorax", "label": "Rontgen Thorax", "type": "textarea"},
        {"name": "ct_scan", "label": "CT Scan", "type": "textarea"},
        {"name": "usg", "label": "USG", "type": "textarea"},
    ],
    "Diagnosis & Tindakan": [
        {"name": "diagnosis_awal", "label": "Diagnosis Awal", "type": "textarea"},
        {"name": "komorbid", "label": "Komorbid", "type": "textarea"},
        {"name": "komplikasi", "label": "Komplikasi", "type": "textarea"},
        {"name": "diagnosis_akhir", "label": "Diagnosis Akhir", "type": "textarea"},
        {"name": "tindakan", "label": "Tindakan", "type": "textarea"},
    ],
    "Obat & Validasi": [
        {"name": "obat", "label": "Obat", "type": "textarea"},
        {"name": "validasi_fornas", "label": "Validasi Fornas", "type": "textarea"},
        {"name": "notes_doctor", "label": "Catatan Dokter", "type": "textarea"},
    ],
}


# ------------------------
# User (special RBAC)
# ------------------------
user_fields = [
    {"name": "email", "label": "Email", "type": "email"},
    {"name": "name", "label": "Nama Lengkap", "type": "text"},
    {
        "name": "role", "label": "Role", "type": "select",
        "options": [
            ("superadmin", "Super Admin"),
            ("admin_rs", "Admin RS"),
            ("doctor", "Dokter"),
            ("coder", "Coder"),
            ("verifikator", "Verifikator"),
            ("costing", "Costing"),
            ("manajemen", "Manajemen"),
            ("validator", "Validator"),
        ],
        "roles": ["superadmin","admin_rs"], 
        "readonly_roles": ["superadmin"]
    },
    {
        "name": "hospital_id", "label": "Rumah Sakit", "type": "select",
        "options": [],  # akan diisi dinamis di route
    }
]


# ------------------------
# Global Dict
# ------------------------
form_configs = {
    "patient": patient_fields,
    "claim": claim_fields,
    "hospital": hospital_fields,
    "visit": visit_fields,
    "medical_record": medical_record_fields,
    "user": user_fields,
}
