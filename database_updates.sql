-- ===============================================
-- DATABASE UPDATES FOR FASE 6A-6C + FEEDBACK SYSTEM
-- Jalankan query ini di PgAdmin
-- ===============================================

-- 1. FASE 6C.3: Tambah kolom feedback ke tabel rules_master
-- ===============================================
ALTER TABLE rules_master 
ADD COLUMN IF NOT EXISTS feedback TEXT,
ADD COLUMN IF NOT EXISTS feedback_by VARCHAR(255),
ADD COLUMN IF NOT EXISTS feedback_date TIMESTAMP;

-- 2. FASE 6A: Pastikan kolom pdf_file sudah ada (jika belum)
-- ===============================================
ALTER TABLE rules_master 
ADD COLUMN IF NOT EXISTS pdf_file TEXT;

-- 2b. Tambah kolom yang hilang dari model terbaru
-- ===============================================
ALTER TABLE rules_master 
ADD COLUMN IF NOT EXISTS rs_id TEXT,
ADD COLUMN IF NOT EXISTS region_id TEXT,
ADD COLUMN IF NOT EXISTS approved_by TEXT,
ADD COLUMN IF NOT EXISTS approved_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS review_notes TEXT;

-- 3. FASE 6C: Pastikan tabel regional_reports sudah ada
-- ===============================================
CREATE TABLE IF NOT EXISTS regional_reports (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    se_file TEXT NOT NULL,
    region_id TEXT NOT NULL,
    rs_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    reported_by TEXT NOT NULL,
    reviewed_by TEXT,
    reviewed_date TIMESTAMP,
    review_notes TEXT,
    converted_rules_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tambah index untuk performa yang lebih baik
-- ===============================================
CREATE INDEX IF NOT EXISTS idx_rules_master_layer ON rules_master(layer);
CREATE INDEX IF NOT EXISTS idx_rules_master_diagnosis ON rules_master(diagnosis);
CREATE INDEX IF NOT EXISTS idx_rules_master_status ON rules_master(status);
CREATE INDEX IF NOT EXISTS idx_rules_master_rs_id ON rules_master(rs_id);
CREATE INDEX IF NOT EXISTS idx_regional_reports_rs_id ON regional_reports(rs_id);
CREATE INDEX IF NOT EXISTS idx_regional_reports_status ON regional_reports(status);

-- 5. FASE 6B: Tambah data dummy untuk layer yang masih kosong
-- ===============================================

-- Layer 1: Permenkes (Nasional)
INSERT INTO rules_master (
    layer, diagnosis, field, isi, sumber, 
    rs_id, status, created_by, created_at
) VALUES 
-- Permenkes untuk A09 (Diare)
('permenkes', 'A09 - Diarrhoea and gastroenteritis of presumed infectious origin', 'diagnosis.justifikasi', 
 'Permenkes No. 5 Tahun 2014: Diagnosis diare akut memerlukan pemeriksaan feses rutin dan kultur jika terdapat demam >38°C atau darah dalam feses. Rehidrasi oral sebagai terapi lini pertama kecuali ada indikasi dehidrasi berat.', 
 'Permenkes No. 5 Tahun 2014', null, 'official', 'system', CURRENT_TIMESTAMP),

('permenkes', 'A09 - Diarrhoea and gastroenteritis of presumed infectious origin', 'diagnosis.terapi', 
 'Permenkes No. 28 Tahun 2019: Antibiotik hanya diberikan pada diare berdarah, demam tinggi, atau pasien immunocompromised. Hindari penggunaan antidiare pada diare akut infeksius.', 
 'Permenkes No. 28 Tahun 2019', null, 'official', 'system', CURRENT_TIMESTAMP),

-- Permenkes untuk J44.1 (COPD Eksaserbasi)
('permenkes', 'J44.1 - Chronic obstructive pulmonary disease with acute exacerbation', 'diagnosis.pemeriksaan', 
 'Permenkes No. 76 Tahun 2016: Eksaserbasi COPD akut memerlukan evaluasi saturasi O2, analisa gas darah, dan foto thoraks. Bronkodilator kerja cepat sebagai terapi utama.', 
 'Permenkes No. 76 Tahun 2016', null, 'official', 'system', CURRENT_TIMESTAMP),

('permenkes', 'J44.1 - Chronic obstructive pulmonary disease with acute exacerbation', 'diagnosis.terapi', 
 'Permenkes No. 40 Tahun 2017: Kortikosteroid sistemik diberikan maksimal 5-7 hari. Antibiotik hanya jika ada tanda infeksi bakteri (sputum purulen, leukositosis).', 
 'Permenkes No. 40 Tahun 2017', null, 'official', 'system', CURRENT_TIMESTAMP);

-- Layer 2: Nasional (Pedoman Nasional)
INSERT INTO rules_master (
    layer, diagnosis, field, isi, sumber, 
    rs_id, status, created_by, created_at
) VALUES 
-- Pedoman Nasional untuk A09
('nasional', 'A09 - Diarrhoea and gastroenteritis of presumed infectious origin', 'diagnosis.klasifikasi', 
 'Pedoman Nasional Diare 2021: Klasifikasi dehidrasi berdasarkan kehilangan cairan <5% (ringan), 5-10% (sedang), >10% (berat). Oralit formula baru WHO/UNICEF sebagai standar.', 
 'Pedoman Nasional Diare 2021', null, 'official', 'system', CURRENT_TIMESTAMP),

('nasional', 'A09 - Diarrhoea and gastroenteritis of presumed infectious origin', 'rawat_inap.monitoring', 
 'Standar Nasional Keselamatan Pasien: Monitoring ketat tanda vital dan balance cairan setiap 4-6 jam pada diare dengan dehidrasi sedang-berat.', 
 'Standar Nasional Keselamatan Pasien', null, 'official', 'system', CURRENT_TIMESTAMP),

-- Pedoman Nasional untuk J44.1
('nasional', 'J44.1 - Chronic obstructive pulmonary disease with acute exacerbation', 'diagnosis.pemeriksaan', 
 'Pedoman PDPI 2020: Spirometri tidak dilakukan saat eksaserbasi akut. Evaluasi fungsi paru dilakukan setelah stabilisasi minimal 4 minggu.', 
 'Pedoman PDPI 2020', null, 'official', 'system', CURRENT_TIMESTAMP),

('nasional', 'J44.1 - Chronic obstructive pulmonary disease with acute exacerbation', 'rawat_inap.rehabilitasi', 
 'Standar Pelayanan COPD: Rehabilitasi paru dimulai sejak rawat inap dengan mobilisasi dini dan fisioterapi dada jika tidak ada kontraindikasi.', 
 'Standar Pelayanan COPD', null, 'official', 'system', CURRENT_TIMESTAMP);

-- Layer 6: Bridging (Sistem e-Claim)
INSERT INTO rules_master (
    layer, diagnosis, field, isi, sumber, 
    rs_id, status, created_by, created_at
) VALUES 
-- Bridging rules untuk A09
('bridging', 'A09 - Diarrhoea and gastroenteritis of presumed infectious origin', 'claim.syarat_klaim', 
 'e-Claim Bridging: Diagnosis A09 memerlukan minimal 1 pemeriksaan penunjang (feses rutin atau elektrolit) untuk dapat di-claim. Rawat inap minimal 2 hari jika dehidrasi.', 
 'Sistem e-Claim BPJS', null, 'official', 'system', CURRENT_TIMESTAMP),

('bridging', 'A09 - Diarrhoea and gastroenteritis of presumed infectious origin', 'claim.koding_sekunder', 
 'Sistem Bridging INA-CBG: Koding sekunder Z87.19 (riwayat penyakit digestif) dapat ditambahkan jika ada riwayat diare berulang untuk optimalisasi grouping.', 
 'Sistem Bridging INA-CBG', null, 'official', 'system', CURRENT_TIMESTAMP),

-- Bridging rules untuk J44.1
('bridging', 'J44.1 - Chronic obstructive pulmonary disease with acute exacerbation', 'claim.dokumentasi_wajib', 
 'e-Claim Bridging: J44.1 memerlukan dokumentasi spirometri dalam 1 tahun terakhir atau foto thoraks menunjukkan emfisema/hiperinflasi untuk validasi klaim.', 
 'Sistem e-Claim BPJS', null, 'official', 'system', CURRENT_TIMESTAMP),

('bridging', 'J44.1 - Chronic obstructive pulmonary disease with acute exacerbation', 'claim.koding_sekunder', 
 'Sistem Bridging: Tambahkan Z87.891 (riwayat merokok) sebagai diagnosis sekunder untuk meningkatkan akurasi casemix dan severity adjustment.', 
 'Sistem Bridging INA-CBG', null, 'official', 'system', CURRENT_TIMESTAMP);

-- Layer 7: Fraud Detection
INSERT INTO rules_master (
    layer, diagnosis, field, isi, sumber, 
    rs_id, status, created_by, created_at
) VALUES 
-- Fraud detection untuk A09
('fraud', 'A09 - Diarrhoea and gastroenteritis of presumed infectious origin', 'fraud.los_anomaly', 
 'FRAUD ALERT: Diare dengan rawat inap >7 hari tanpa komplikasi atau komorbid patut dicurigai. Periksa konsistensi dengan pemeriksaan penunjang dan respons terapi.', 
 'Sistem Deteksi Fraud BPJS', null, 'official', 'system', CURRENT_TIMESTAMP),

('fraud', 'A09 - Diarrhoea and gastroenteritis of presumed infectious origin', 'fraud.pattern_detection', 
 'Pattern Recognition: Pasien dengan diare berulang >3x dalam 30 hari dengan provider sama perlu investigasi lebih lanjut untuk kemungkinan fraud billing.', 
 'Sistem Deteksi Fraud BPJS', null, 'official', 'system', CURRENT_TIMESTAMP),

-- Fraud detection untuk J44.1
('fraud', 'J44.1 - Chronic obstructive pulmonary disease with acute exacerbation', 'fraud.diagnosis_verification', 
 'FRAUD ALERT: COPD eksaserbasi tanpa riwayat merokok atau pajanan polutan, terutama usia <40 tahun, memerlukan verifikasi diagnosis yang ketat.', 
 'Sistem Deteksi Fraud BPJS', null, 'official', 'system', CURRENT_TIMESTAMP),

('fraud', 'J44.1 - Chronic obstructive pulmonary disease with acute exacerbation', 'fraud.frequency_anomaly', 
 'Anomaly Detection: Frekuensi rawat inap COPD >4x/tahun dengan provider sama tanpa rujukan spesialis paru patut dicurigai sebagai potential fraud.', 
 'Sistem Deteksi Fraud BPJS', null, 'official', 'system', CURRENT_TIMESTAMP);

-- Layer 8: Temporary Rules (Panduan Darurat)
INSERT INTO rules_master (
    layer, diagnosis, field, isi, sumber, 
    rs_id, status, created_by, created_at
) VALUES 
-- Temporary rules untuk kondisi pandemi/darurat
('temporary', 'A09 - Diarrhoea and gastroenteritis of presumed infectious origin', 'temporary.pandemic_protocol', 
 'PANDUAN DARURAT COVID-19: Selama pandemi, isolasi pasien diare hingga hasil swab COVID-19 negatif. Gunakan APD lengkap level 2 untuk semua kontak pasien.', 
 'Panduan Darurat COVID-19 Kemenkes', null, 'active', 'system', CURRENT_TIMESTAMP),

('temporary', 'J44.1 - Chronic obstructive pulmonary disease with acute exacerbation', 'temporary.pandemic_screening', 
 'PANDUAN DARURAT: Eksaserbasi COPD dengan sesak napas berat, pertimbangkan COVID-19 sebagai trigger. Rapid test antigen wajib sebelum nebulisasi.', 
 'Panduan Darurat COVID-19 Kemenkes', null, 'active', 'system', CURRENT_TIMESTAMP),

-- Temporary rules umum
('temporary', 'All Diagnoses', 'temporary.emergency_extension', 
 'KEBIJAKAN DARURAT 2024: Selama situasi darurat nasional, perpanjangan rawat inap maksimal 3 hari tambahan dapat dipertimbangkan dengan approval supervisor.', 
 'Kebijakan Darurat Nasional 2024', null, 'active', 'system', CURRENT_TIMESTAMP);

-- 6. Tambah sample data regional reports untuk testing
-- ===============================================
INSERT INTO regional_reports (
    title, description, se_file, region_id, rs_id, 
    status, reported_by, review_notes
) VALUES 
('SE BPJS Jatim No.01/2024 - Diare A09', 
 'Surat Edaran mengenai aturan klaim diagnosis diare dengan komplikasi dehidrasi untuk wilayah Jawa Timur',
 'se_jatim_diare_2024.pdf', 'jatim', 'rs_001', 
 'pending', 'admin_rs_001', 'Perlu review lebih lanjut oleh AI META'),

('SE BPJS Jabar No.02/2024 - COPD J44.1',
 'Surat Edaran mengenai dokumentasi wajib untuk klaim COPD eksaserbasi akut wilayah Jawa Barat', 
 'se_jabar_copd_2024.pdf', 'jabar', 'rs_002',
 'pending', 'admin_rs_002', 'Butuh clarification dari dokter penanggung jawab');

-- 7. Update beberapa rules yang sudah ada untuk menambah contoh feedback
-- ===============================================
UPDATE rules_master 
SET feedback = 'Aturan ini sudah sesuai dengan praktik di lapangan. Sangat membantu dalam decision making.',
    feedback_by = 'dr.admin@rs001.com',
    feedback_date = CURRENT_TIMESTAMP - INTERVAL '2 days'
WHERE id = (
    SELECT id FROM rules_master 
    WHERE layer = 'rs' AND diagnosis LIKE '%A09%' 
      AND isi LIKE '%dehidrasi%' 
    LIMIT 1
);

UPDATE rules_master 
SET feedback = 'Perlu penambahan kriteria untuk pasien pediatrik. Dosis oralit berbeda untuk anak <2 tahun.',
    feedback_by = 'dr.pediatri@rs002.com', 
    feedback_date = CURRENT_TIMESTAMP - INTERVAL '1 day'
WHERE id = (
    SELECT id FROM rules_master 
    WHERE layer = 'rs' AND diagnosis LIKE '%A09%'
      AND isi LIKE '%oralit%'
    LIMIT 1
);

-- 8. Verify data integrity
-- ===============================================
-- Cek apakah semua kolom berhasil ditambahkan
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'rules_master' 
  AND column_name IN ('feedback', 'feedback_by', 'feedback_date', 'pdf_file')
ORDER BY column_name;

-- Cek apakah tabel regional_reports berhasil dibuat
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'regional_reports'
ORDER BY ordinal_position;

-- Cek distribusi rules per layer
SELECT layer, COUNT(*) as total_rules,
       COUNT(CASE WHEN feedback IS NOT NULL THEN 1 END) as rules_with_feedback
FROM rules_master 
GROUP BY layer 
ORDER BY layer;

-- Cek sample data regional reports
SELECT COUNT(*) as total_reports, 
       COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_reports
FROM regional_reports;

-- ===============================================
-- SELESAI! 
-- Jalankan query ini secara berurutan di PgAdmin
-- Atau copy-paste semuanya sekaligus
-- ===============================================