# 📋 DOKUMENTASI PAYLOAD SERVICE

Dokumentasi lengkap payload yang dibutuhkan untuk setiap service di sistem klaim BPJS.

---

## 1. ANALYZE DIAGNOSIS SERVICE
**File:** `core_engine/services/analyze_diagnosis_service.py`  
**Fungsi:** `process_analyze_diagnosis(input_data)`  
**Deskripsi:** Menganalisis diagnosis menggunakan hybrid multilayer rules (DB + JSON + AI)

### Payload yang dibutuhkan:
- `claim_id` (opsional) - ID klaim untuk tracking
- `disease_name` (WAJIB) - Nama penyakit/diagnosis yang akan dianalisis
- `rekam_medis` (opsional) - Array berisi data rekam medis pasien untuk analisis AI
- `rs_id` (opsional) - ID rumah sakit untuk filter multilayer rules
- `region_id` (opsional) - ID region untuk filter multilayer rules

### Contoh payload:
```json
{
  "claim_id": "CLM-2024-001",
  "disease_name": "Pneumonia",
  "rekam_medis": [
    {
      "keluhan": "Batuk berdahak",
      "ttv": {"suhu": 38.5, "td": "120/80"},
      "lab": {"leukosit": 15000}
    }
  ],
  "rs_id": 123,
  "region_id": 5
}
```

### Output yang dihasilkan:
- Aspek klinis (justifikasi, bukti klinis, syarat klinis)
- Data ICD-10 (kode ICD, struktur, kode ganda, Z-code, kode BPJS khusus)
- Rawat inap (indikasi, kriteria, lama rawat)
- Faskes (tingkat, justifikasi, kompetensi)
- Rujukan (kriteria, tujuan, indikasi)
- INA-CBG (kode, tarif, deskripsi)
- Tindakan yang direkomendasikan
- Notifikasi untuk setiap aspek

---

## 2. ANALYZE PROCEDURE SERVICE
**File:** `core_engine/services/analyze_procedure_service.py`  
**Fungsi:** `process_analyze_procedure(payload)`  
**Deskripsi:** Menganalisis tindakan/prosedur medis dengan hybrid AI + multilayer rules

### Payload yang dibutuhkan:
- `claim_id` (opsional) - ID klaim
- `procedure_name` (WAJIB) - Nama tindakan/prosedur yang akan dianalisis
- `procedure` (alias) - Alternatif untuk procedure_name
- `stage` (opsional) - Tahap perawatan: "admission", "daily", atau "discharge" (default: "admission")
- `context` (opsional tapi disarankan) - Objek berisi konteks klaim:
  - `primary_claim` - Diagnosis utama
  - `secondary_claims` - Array diagnosis sekunder
  - `primary_action` - Tindakan utama
  - `secondary_actions` - Array tindakan sekunder
  - `rs_id` - ID rumah sakit
  - `region_id` - ID region
  - `hospital_level` - Level RS (A/B/C/D)
  - `patient_context` - Konteks tambahan pasien

### Contoh payload:
```json
{
  "claim_id": "CLM-2024-001",
  "procedure_name": "Ventilasi Mekanik",
  "stage": "daily",
  "context": {
    "primary_claim": "Pneumonia Berat",
    "secondary_claims": ["ARDS", "Sepsis"],
    "primary_action": "Ventilasi Mekanik",
    "secondary_actions": ["Pemasangan CVP"],
    "rs_id": 123,
    "region_id": 5,
    "hospital_level": "B",
    "patient_context": "ICU, hari ke-3"
  }
}
```

### Output yang dihasilkan:
- Nama prosedur
- Kode ICD-9-CM dan deskripsi
- Deskripsi ringkas (ICD-9, Status, INA-CBG)
- Validitas prosedur
- Status tindakan (WAJIB/OPSIONAL/SUPPORTIVE)
- Status singkat untuk UI
- Dampak ke tarif INA-CBG
- Level faskes yang sesuai
- Indikasi rawat inap
- Syarat klinis
- Notifikasi AI (rekomendasi)
- Multilayer rules yang digunakan

---

## 3. GENERATE CLAIM COMBOS SERVICE
**File:** `core_engine/services/generate_claim_combos_service.py`  
**Fungsi:** `process_generate_claim_combos(payload)` dan `process_generate_alternatives(payload)`  
**Deskripsi:** Evaluasi kombinasi diagnosis + tindakan dan generate alternatif kombinasi klaim

### Payload untuk evaluasi kombinasi:
- `primary_claim` (WAJIB) - Diagnosis utama
- `secondary_claims` (opsional) - Array diagnosis sekunder
- `primary_action` (WAJIB) - Tindakan utama
- `secondary_actions` (opsional) - Array tindakan sekunder
- `rs_id` (opsional) - ID rumah sakit
- `region_id` (opsional) - ID region

### Contoh payload:
```json
{
  "primary_claim": "Pneumonia",
  "secondary_claims": ["Diabetes Mellitus", "Hipertensi"],
  "primary_action": "Oksigenasi",
  "secondary_actions": ["Nebulizer", "Fisioterapi Dada"],
  "rs_id": 123,
  "region_id": 5
}
```

### Output yang dihasilkan:
- Evaluasi diagnosis (validitas, severity, kode CBG, syarat klinis, faskes, rawat inap)
- Evaluasi tindakan (tindakan wajib, validasi pilihan, konflik, dampak tarif)
- Notifikasi gabungan
- Alternatif kombinasi klaim (judul, severity, INA-CBG, tarif, syarat, faskes, tindakan)
- Rules yang digunakan (kombinasi, diagnosis, tindakan)

---

## 4. PREDICT DDX SERVICE
**File:** `core_engine/services/predict_ddx_service.py`  
**Fungsi:** `process_predict_ddx(payload)`  
**Deskripsi:** Prediksi differential diagnosis menggunakan AI berdasarkan rekam medis

### Payload format baru (PREFERRED):
- `global_record` (WAJIB) - Objek berisi rekam medis global:
  - `admission` - Data saat masuk RS
  - `daily` - Array data harian selama rawat
  - `discharge` - Data saat keluar RS
- `stage` (WAJIB) - Tahap analisis: "admission", "daily", atau "discharge"

### Payload format lama (BACKWARD-COMPATIBLE):
- `rekam_medis` - Array berisi data rekam medis

### Contoh payload format baru:
```json
{
  "global_record": {
    "admission": {
      "keluhan": "Sesak napas, batuk",
      "ttv": {"suhu": 38.5, "rr": 28, "nadi": 110},
      "pemeriksaan": "Ronki basah kasar"
    },
    "daily": [
      {
        "hari": 1,
        "ttv": {"suhu": 38.0, "spo2": 92},
        "terapi": "Antibiotik IV, O2 3 lpm"
      },
      {
        "hari": 2,
        "ttv": {"suhu": 37.5, "spo2": 95},
        "terapi": "Antibiotik IV, O2 2 lpm"
      }
    ],
    "discharge": {
      "kondisi": "Membaik",
      "diagnosis_akhir": "Pneumonia"
    }
  },
  "stage": "discharge"
}
```

### Contoh payload format lama:
```json
{
  "rekam_medis": [
    {
      "keluhan": "Sesak napas",
      "ttv": {"suhu": 38.5},
      "pemeriksaan": "Ronki"
    }
  ]
}
```

### Output yang dihasilkan:
- Diagnosis utama (array of parent diagnosis dengan confidence dan children)
- Komorbid (array of komorbid dengan confidence)
- Komplikasi (array of komplikasi dengan confidence)
- Engine version

---

## 5. i-DRG SERVICE
**File:** `core_engine/services/idrg_service.py`  
**Fungsi:** `predict_single_idrg(payload)` dan `predict_combo_idrg(payload)`  
**Deskripsi:** Prediksi grouping i-DRG untuk single diagnosis atau kombinasi

### 5A. Mode SINGLE (Detail Diagnosis)
**Fungsi:** `predict_single_idrg(payload)`

#### Payload yang dibutuhkan:
- `diagnosis_name` (WAJIB) - Nama diagnosis
- `justifikasi` (opsional) - Justifikasi klinis
- `bukti_klinis` (opsional) - Bukti klinis pendukung
- `tindakan_names` (opsional) - Array nama tindakan terkait
- `rs_id` (opsional) - ID rumah sakit
- `region_id` (opsional) - ID region

#### Contoh payload:
```json
{
  "diagnosis_name": "Pneumonia Berat",
  "justifikasi": "Pasien dengan sesak napas berat",
  "bukti_klinis": "Infiltrat bilateral pada rontgen, leukosit 18000",
  "tindakan_names": ["Ventilasi Mekanik", "Antibiotik IV"],
  "rs_id": 123,
  "region_id": 5
}
```

#### Output yang dihasilkan:
- Group i-DRG (kode dan nama grup)
- Severity index (Minor/Moderate/Severe)
- Checklist dokumentasi
- Faktor penentu severity
- Ungroupable alert
- Estimasi tarif
- Gap analysis (selisih tarif)
- Notifikasi

### 5B. Mode COMBO (Evaluasi Kombinasi)
**Fungsi:** `predict_combo_idrg(payload)`

#### Payload yang dibutuhkan:
- `mode` - Harus diisi "combo"
- `primary_diagnosis` (WAJIB) - Diagnosis utama
- `secondary_diagnoses` (opsional) - Array diagnosis sekunder
- `primary_action` (WAJIB) - Tindakan utama
- `secondary_actions` (opsional) - Array tindakan sekunder
- `rs_id` (opsional) - ID rumah sakit
- `region_id` (opsional) - ID region

#### Contoh payload:
```json
{
  "mode": "combo",
  "primary_diagnosis": "Pneumonia",
  "secondary_diagnoses": ["ARDS", "Sepsis"],
  "primary_action": "Ventilasi Mekanik",
  "secondary_actions": ["Pemasangan CVP", "Antibiotik IV"],
  "rs_id": 123,
  "region_id": 5
}
```

#### Output yang dihasilkan:
- Group i-DRG kombinasi
- Severity kombinasi
- Checklist kombinasi
- Faktor severity kombinasi
- Risiko ungroupable
- Estimasi tarif
- Gap vs CBG
- Rekomendasi AI

---

## 6. REGULATION SERVICE
**File:** `core_engine/services/regulation_service.py`  
**Fungsi:** `process_regulation_detail(payload, field)` dan `collect_regulations_for_field(payload, field)`  
**Deskripsi:** Mengambil detail regulasi multilayer untuk field tertentu

### Payload yang dibutuhkan:
- `kategori` (WAJIB) - Nama diagnosis (alias: diagnosis_name)
- `diagnosis_name` (alias) - Nama diagnosis
- `procedure_name` (opsional) - Nama prosedur jika scope tindakan
- `procedure` (alias) - Alternatif untuk procedure_name
- `rs_id` (opsional) - ID rumah sakit
- `region_id` (opsional) - ID region
- `scope` (opsional) - Scope regulasi: "diagnosis", "tindakan", "kombinasi", atau "idrg" (default: "diagnosis")

### Contoh payload:
```json
{
  "kategori": "Pneumonia",
  "procedure_name": "Ventilasi Mekanik",
  "rs_id": 123,
  "region_id": 5,
  "scope": "tindakan"
}
```

### Field yang bisa dicek regulasinya:
**Klinis:**
- justifikasi
- bukti_klinis
- syarat_klinis
- confidence_ai

**ICD-10:**
- kode_icd
- struktur_icd10
- kode_ganda
- z_code
- kode_bpjs_khusus

**Tindakan:**
- syarat_klinis_tindakan
- status (status_tindakan)
- ina_cbg (ina_cbg_impact)

**Rawat Inap:**
- indikasi (indikasi_rawat)
- kriteria (kriteria_rawat)
- lama_rawat

**Faskes:**
- tingkat (kesesuaian_rs)
- justifikasi_faskes
- kompetensi

**Rujukan:**
- indikasi_rujukan
- tujuan
- kriteria_rujukan

**INA-CBG:**
- kode
- deskripsi
- tarif

**Detail Prosedur:**
- icd9_code
- icd9_desc
- validitas
- faskes (faskes_proc)
- rawat_inap (rawat_inap_proc)

**i-DRG:**
- group_idrg
- severity_index
- checklist
- faktor_severity
- ungroupable_alert
- simulasi_tarif
- gap_analysis

### Output yang dihasilkan:
- Layer (nasional/regional/rs/bridging/fraud/temporary)
- Sumber regulasi
- Judul regulasi
- Isi regulasi
- Status
- Color code
- Priority

---

## 7. RESUME SERVICE
**File:** `core_engine/services/resume_service.py`  
**Fungsi:** `process_resume_medis(data, mode, settings)`  
**Deskripsi:** Generate resume medis/discharge summary

### Payload yang dibutuhkan:
- `pasien` (WAJIB) - Data pasien:
  - `nama` - Nama lengkap pasien
  - `no_rm` - Nomor rekam medis
  - `umur` - Umur pasien (tahun)
  - `jk` - Jenis kelamin ("L" atau "P")
  - `keluhan` - Keluhan utama
- `visit` (WAJIB) - Data kunjungan:
  - `tgl_masuk` - Tanggal masuk (YYYY-MM-DD)
  - `tgl_keluar` - Tanggal keluar (YYYY-MM-DD)
  - `ruangan` - Nama ruangan rawat
- `diagnosis` (WAJIB) - Data diagnosis:
  - `utama` - Objek diagnosis utama (nama, icd)
  - `sekunder` - Array diagnosis sekunder
- `tindakan` (WAJIB) - Data tindakan:
  - `utama` - Objek tindakan utama (nama, kode)
  - `sekunder` - Array tindakan sekunder
- `obat` (opsional) - Array obat yang diberikan
- `regulasi` (opsional) - Array regulasi terkait
- `dokter` (WAJIB) - Data dokter:
  - `dpjp` - Nama dokter penanggung jawab
  - `perawat` - Nama perawat penanggung jawab

### Parameter tambahan:
- `mode` - Mode generate: "list" (structured) atau "naratif" (AI narrative)
- `settings` - Objek pengaturan:
  - `obat` (boolean) - Tampilkan obat?
  - `regulasi` (boolean) - Tampilkan regulasi?

### Contoh payload:
```json
{
  "pasien": {
    "nama": "Budi Santoso",
    "no_rm": "RM-12345",
    "umur": 45,
    "jk": "L",
    "keluhan": "Sesak napas dan batuk"
  },
  "visit": {
    "tgl_masuk": "2024-01-15",
    "tgl_keluar": "2024-01-20",
    "ruangan": "Melati 3"
  },
  "diagnosis": {
    "utama": {
      "nama": "Pneumonia",
      "icd": "J18.9"
    },
    "sekunder": [
      {"nama": "Diabetes Mellitus", "icd": "E11.9"},
      {"nama": "Hipertensi", "icd": "I10"}
    ]
  },
  "tindakan": {
    "utama": {
      "nama": "Oksigenasi",
      "kode": "93.96"
    },
    "sekunder": [
      {"nama": "Nebulizer", "kode": "93.94"},
      {"nama": "Fisioterapi Dada", "kode": "93.99"}
    ]
  },
  "obat": [
    "Ceftriaxone 2x1g IV",
    "Azithromycin 1x500mg PO"
  ],
  "regulasi": [
    "Sesuai CP Pneumonia 2023",
    "PNPK Pneumonia Komunitas"
  ],
  "dokter": {
    "dpjp": "dr. Ahmad Sp.P",
    "perawat": "Ns. Siti, S.Kep"
  }
}
```

### Output yang dihasilkan:
- Mode resume (list/naratif)
- Identitas pasien
- Data visit
- Diagnosis lengkap
- Tindakan lengkap
- Obat (jika diaktifkan)
- Regulasi (jika diaktifkan)
- Dokter penanggung jawab
- Naratif/template resume medis
- Template type
- Timestamp created_at

---

## CATATAN UMUM

### Field Opsional vs Wajib:
- **WAJIB**: Field yang harus diisi agar service berfungsi dengan baik
- **OPSIONAL**: Field yang meningkatkan kualitas hasil jika diisi
- **rs_id & region_id**: Sangat disarankan untuk mendapatkan multilayer rules yang spesifik

### Best Practices:
1. Selalu isi field wajib dengan data yang valid
2. Isi rs_id dan region_id untuk hasil yang lebih akurat
3. Gunakan format JSON yang valid
4. Pastikan tanggal dalam format YYYY-MM-DD
5. Array kosong lebih baik daripada null untuk field list
6. Gunakan "-" untuk field string yang kosong

### Error Handling:
- Semua service memiliki fallback mechanism
- Jika data tidak lengkap, AI akan mengisi dengan estimasi
- Jika rules tidak ditemukan, akan gunakan rules nasional
- Jika API error, akan return struktur minimal

---

**Terakhir diupdate:** November 6, 2025  
**Versi:** 2.0  
**Repository:** crud_pasien
