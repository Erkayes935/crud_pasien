-- ===================================================
-- DUMMY MULTILAYER RULES - Sample Data untuk Testing
-- Sesuai Sistem 8-Layer AI-CLAIM Rules
-- ===================================================

-- Clear existing data
DELETE FROM rules_master WHERE diagnosis IN ('Pneumonia', 'Hipertensi', 'Diabetes Melitus');

-- ================ PNEUMONIA RULES ================

-- 1. PERMENKES Layer (Priority 1)
INSERT INTO rules_master (diagnosis, field, layer, isi, sumber, status, created_by, approved_by, approved_date) VALUES
('Pneumonia', 'justifikasi', 'permenkes', 'Sesuai Permenkes 52/2016, diagnosis pneumonia harus berdasarkan gejala klinis dan penunjang radiologi', 'Permenkes No. 52 Tahun 2016', 'official', 'ai_meta_pusat', 'ai_meta_pusat', NOW()),
('Pneumonia', 'lama_rawat', 'permenkes', 'Lama rawat pneumonia sesuai standar pelayanan rumah sakit: dewasa 3-5 hari, anak 5-7 hari', 'Permenkes No. 52 Tahun 2016', 'official', 'ai_meta_pusat', 'ai_meta_pusat', NOW());

-- 2. NASIONAL Layer (Priority 2)

INSERT INTO rules_master (diagnosis, field, layer, isi, sumber, rs_id, region_id, status, created_by) VALUES
('Pneumonia', 'pemeriksaan.radiologi', 'nasional', 'Foto thorax PA wajib dilakukan dalam 24 jam', 'PNPK Pneumonia 2023', NULL, NULL, 'official', 'ai_meta_medis'),
('Pneumonia', 'terapi.antibiotik', 'nasional', 'Antibiotik empiris sesuai guideline PDPI', 'CP Pneumonia PDPI 2023', NULL, NULL, 'official', 'ai_meta_medis'),
('DM Tipe 2', 'pemeriksaan.hba1c', 'nasional', 'Pemeriksaan HbA1c setiap 3 bulan', 'PNPK Diabetes Mellitus 2023', NULL, NULL, 'official', 'ai_meta_medis'),
('DM Tipe 2', 'target.glikemik', 'nasional', 'Target HbA1c < 7% untuk pasien usia produktif', 'CP DM Tipe 2 PERKENI 2023', NULL, NULL, 'official', 'ai_meta_medis'),
('Stroke', 'pemeriksaan.ct_scan', 'nasional', 'CT Scan kepala wajib dalam 1 jam', 'PNPK Stroke 2023', NULL, NULL, 'official', 'ai_meta_medis'),
('Stroke', 'terapi.trombolitik', 'nasional', 'Trombolitik dalam 4.5 jam jika tidak ada kontraindikasi', 'CP Stroke Akut PERDOSSI 2023', NULL, NULL, 'official', 'ai_meta_medis');

-- ====================================================================
-- LAYER 3: PPK RS - Pedoman Praktik Klinis RS (PRIORITY OVERRIDE ⭐)
-- ====================================================================

INSERT INTO rules_master (diagnosis, field, layer, isi, sumber, rs_id, region_id, status, created_by) VALUES
('Pneumonia', 'rawat_inap.lama_rawat', 'ppk', 'LOS ≥ 3 hari, antibiotik IV wajib (PPK RS Notopuro)', 'PPK RS Notopuro 2024', 'rs_notopuro', NULL, 'official', 'admin_rs_notopuro'),
('Pneumonia', 'pemeriksaan.kultur', 'ppk', 'Kultur darah dan sputum untuk pneumonia berat', 'PPK RS Notopuro 2024', 'rs_notopuro', NULL, 'official', 'admin_rs_notopuro'),
('DM Tipe 2', 'edukasi.pasien', 'ppk', 'Edukasi diabetes self-management wajib sebelum pulang', 'PPK RS Haji 2024', 'rs_haji', NULL, 'official', 'admin_rs_haji');

-- ====================================================================
-- LAYER 4: REGIONAL - Wilayah/SE BPJS Cabang
-- ====================================================================

INSERT INTO rules_master (diagnosis, field, layer, isi, sumber, rs_id, region_id, status, created_by) VALUES
('Pneumonia', 'administrasi.lampiran', 'regional', 'Lampirkan hasil laboratorium lengkap untuk wilayah Jatim', 'SE BPJS Jatim-01/2023', NULL, 'jatim', 'official', 'ai_meta_regional'),
('Pneumonia', 'rujukan.kriteria', 'regional', 'Rujukan ke RS tipe A jika pneumonia dengan sepsis', 'SE BPJS Jatim-02/2023', NULL, 'jatim', 'official', 'ai_meta_regional'),
('DM Tipe 2', 'prolanis.wajib', 'regional', 'Pendaftaran Prolanis wajib untuk pasien DM di Jateng', 'SE BPJS Jateng-03/2023', NULL, 'jateng', 'official', 'ai_meta_regional'),
('Stroke', 'transport.ambulans', 'regional', 'Koordinasi ambulans stroke untuk wilayah Jabodetabek', 'SE BPJS Jakarta-01/2024', NULL, 'jabodetabek', 'official', 'ai_meta_regional');

-- ====================================================================
-- LAYER 5: RS LOKAL - BA/SOP Internal RS (PRIORITY OVERRIDE ⭐)
-- ====================================================================

INSERT INTO rules_master (diagnosis, field, layer, isi, sumber, rs_id, region_id, status, created_by) VALUES
('Pneumonia', 'administrasi.kultur', 'rs', 'Kultur sputum bila LOS > 5 hari (SOP Internal)', 'BA RS Notopuro 2024', 'rs_notopuro', NULL, 'official', 'admin_rs_notopuro'),
('Pneumonia', 'konsultasi.spesialis', 'rs', 'Konsul paru wajib untuk pneumonia komunitas berat', 'SOP RS Notopuro 2024', 'rs_notopuro', NULL, 'official', 'admin_rs_notopuro'),
('DM Tipe 2', 'konseling.gizi', 'rs', 'Konseling gizi oleh ahli gizi setiap rawat inap DM', 'BA RS Haji 2024', 'rs_haji', NULL, 'official', 'admin_rs_haji'),
('Stroke', 'fisioterapi.dini', 'rs', 'Fisioterapi dimulai H+1 jika kondisi stabil', 'SOP RS Soetomo 2024', 'rs_soetomo', NULL, 'official', 'admin_rs_soetomo');

-- ====================================================================
-- LAYER 6: BRIDGING - Teknis SIMRS/BPJS
-- ====================================================================

INSERT INTO rules_master (diagnosis, field, layer, isi, sumber, rs_id, region_id, status, created_by) VALUES
('Pneumonia', 'teknis.kode_icd', 'bridging', 'Gunakan kode ICD-10 J18.9 untuk pneumonia unspecified', 'Panduan Teknis e-Claim v5.2', NULL, NULL, 'official', 'ai_meta_teknis'),
('Pneumonia', 'teknis.grouper', 'bridging', 'Pastikan grouper INA-CBG sesuai dengan severity', 'Manual INA-CBG 2024', NULL, NULL, 'official', 'ai_meta_teknis'),
('DM Tipe 2', 'teknis.kode_icd', 'bridging', 'Kode E11.9 untuk DM tipe 2 tanpa komplikasi', 'Panduan ICD-10 BPJS 2024', NULL, NULL, 'official', 'ai_meta_teknis'),
('Stroke', 'teknis.kode_icd', 'bridging', 'Kode I63.9 untuk stroke iskemik unspecified', 'Panduan ICD-10 Neurologi 2024', NULL, NULL, 'official', 'ai_meta_teknis');

-- ====================================================================
-- LAYER 7: FRAUD - AI Anti-Anomali
-- ====================================================================

INSERT INTO rules_master (diagnosis, field, layer, isi, sumber, rs_id, region_id, status, created_by) VALUES
('Pneumonia', 'validasi.anomali', 'fraud', 'Alert jika LOS > 14 hari tanpa komplikasi', 'AI Fraud Detection Model v2.1', NULL, NULL, 'active', 'ai_meta_ai_team'),
('Pneumonia', 'validasi.biaya', 'fraud', 'Flag jika biaya obat > 150% dari rata-rata kasus serupa', 'AI Cost Anomaly Model v1.5', NULL, NULL, 'active', 'ai_meta_ai_team'),
('DM Tipe 2', 'validasi.obat', 'fraud', 'Alert jika insulin dosis > 100 unit/hari tanpa justifikasi', 'AI Anti-Fraud DM Model v2.0', NULL, NULL, 'active', 'ai_meta_ai_team'),
('Stroke', 'validasi.rujukan', 'fraud', 'Flag rujukan stroke > 6 jam dari onset', 'AI Stroke Timeline Model v1.3', NULL, NULL, 'active', 'ai_meta_ai_team');

-- ====================================================================
-- LAYER 8: TEMPORARY - Kebijakan Transisi/COVID/i-DRG
-- ====================================================================

INSERT INTO rules_master (diagnosis, field, layer, isi, sumber, rs_id, region_id, status, created_by) VALUES
('Pneumonia', 'covid_protocol', 'temporary', 'Skrining COVID-19 untuk semua pneumonia (berlaku s/d Des 2024)', 'Kebijakan Transisi COVID-19', NULL, NULL, 'temporary', 'ai_meta_superadmin'),
('DM Tipe 2', 'telemedicine', 'temporary', 'Kontrol DM via telemedicine diizinkan selama masa transisi', 'SE Telemedicine BPJS 2024', NULL, NULL, 'temporary', 'ai_meta_superadmin'),
('Stroke', 'idrg_transition', 'temporary', 'Masa transisi INA-CBG ke i-DRG untuk kasus stroke (2024-2025)', 'Kebijakan Transisi i-DRG 2025', NULL, NULL, 'temporary', 'ai_meta_superadmin');

-- ====================================================================
-- VERIFY DATA BERHASIL DIINSERT
-- ====================================================================

-- Check jumlah rules per layer
SELECT 
    layer,
    COUNT(*) as total_rules,
    COUNT(DISTINCT diagnosis) as total_diagnosis,
    STRING_AGG(DISTINCT diagnosis, ', ') as diagnoses
FROM rules_master 
WHERE created_by LIKE '%test%' OR created_by LIKE '%dummy%' OR created_by LIKE '%ai_meta%' OR created_by LIKE '%admin_rs%'
GROUP BY layer 
ORDER BY 
    CASE layer
        WHEN 'permenkes' THEN 1
        WHEN 'nasional' THEN 2  
        WHEN 'ppk' THEN 3
        WHEN 'regional' THEN 4
        WHEN 'rs' THEN 5
        WHEN 'bridging' THEN 6
        WHEN 'fraud' THEN 7
        WHEN 'temporary' THEN 8
    END;

-- Check rules untuk diagnosis tertentu
SELECT 
    diagnosis, 
    field,
    layer, 
    LEFT(isi, 50) as isi_preview,
    rs_id,
    region_id,
    status
FROM rules_master 
WHERE diagnosis = 'Pneumonia'
ORDER BY diagnosis, field,
    CASE layer
        WHEN 'permenkes' THEN 1
        WHEN 'nasional' THEN 2  
        WHEN 'ppk' THEN 3
        WHEN 'regional' THEN 4
        WHEN 'rs' THEN 5
        WHEN 'bridging' THEN 6
        WHEN 'fraud' THEN 7
        WHEN 'temporary' THEN 8
    END;

-- Total summary
SELECT 
    COUNT(*) as total_dummy_rules,
    COUNT(DISTINCT diagnosis) as total_diagnoses,
    COUNT(DISTINCT layer) as total_layers,
    COUNT(DISTINCT rs_id) as total_rs_with_rules
FROM rules_master 
WHERE created_by LIKE '%test%' OR created_by LIKE '%dummy%' OR created_by LIKE '%ai_meta%' OR created_by LIKE '%admin_rs%';