-- TRUNCATE semua tabel utama (disable FK constraint dulu)
SET session_replication_role = replica;
TRUNCATE TABLE claims, medical_records, visits, patients, users, hospitals RESTART IDENTITY CASCADE;
SET session_replication_role = DEFAULT;

-- Dummy hospitals
INSERT INTO hospitals (nama, kode_hospital) VALUES
('RSUP Dr. Sardjito', 'RS001'),
('RSUD Jakarta Utara', 'RS002'),
('RS Siloam Bandung', 'RS003'),
('RSUD Bandung', 'RS004'),
('RS Siloam Yogyakarta', 'RS005'),
('RSUP Adam Malik', 'RS006'),
('RS Mayapada Bandung', 'RS007'),
('RS Siloam Surabaya', 'RS008'),
('RSUD Surabaya', 'RS009'),
('RSUP Persahabatan', 'RS010'),
('RSUD Semarang', 'RS011'),
('RS Siloam Semarang', 'RS012'),
('RSUP Fatmawati', 'RS013'),
('RSUD Medan', 'RS014'),
('RS Siloam Medan', 'RS015'),
('RSUP Hasan Sadikin', 'RS016'),
('RSUD Yogyakarta', 'RS017'),
('RS Siloam Makassar', 'RS018'),
('RSUP Wahidin', 'RS019'),
('RSUD Makassar', 'RS020');

-- Dummy users
INSERT INTO users (email, role, hospital_id, auth0_sub) VALUES
('aaa@yopmail.com', 'dokter', 3, 'zVQ9YdZgvqSvPTC+'),
('arca@yopmail.com', 'dokter', 4, 'QV8uG2uhatqvEsT'),
('superadmin@mail.com', 'superadmin', NULL, 'xw9672cRWwdeVzE'),
('user1@yopmail.com', 'doctor', 1, NULL),
('user2@yopmail.com', 'doctor', 2, NULL),
('user3@yopmail.com', 'doctor', 3, NULL),
('user4@yopmail.com', 'doctor', 4, NULL),
('user5@yopmail.com', 'doctor', 5, NULL),
('user6@yopmail.com', 'doctor', 6, NULL),
('user7@yopmail.com', 'doctor', 7, NULL),
('user8@yopmail.com', 'doctor', 8, NULL),
('user9@yopmail.com', 'doctor', 9, NULL),
('user10@yopmail.com', 'doctor', 10, NULL),
('user11@yopmail.com', 'doctor', 11, NULL),
('user12@yopmail.com', 'doctor', 12, NULL),
('user13@yopmail.com', 'doctor', 13, NULL),
('user14@yopmail.com', 'doctor', 14, NULL),
('user15@yopmail.com', 'doctor', 15, NULL),
('user16@yopmail.com', 'doctor', 16, NULL),
('user17@yopmail.com', 'doctor', 17, NULL),
('user18@yopmail.com', 'doctor', 18, NULL),
('user19@yopmail.com', 'doctor', 19, NULL),
('user20@yopmail.com', 'doctor', 20, NULL);

-- Dummy patients
INSERT INTO patients (nama, hospital_id) VALUES
('Pasien 1', 1),('Pasien 2', 2),('Pasien 3', 3),('Pasien 4', 4),('Pasien 5', 5),('Pasien 6', 6),('Pasien 7', 7),('Pasien 8', 8),('Pasien 9', 9),('Pasien 10', 10),('Pasien 11', 11),('Pasien 12', 12),('Pasien 13', 13),('Pasien 14', 14),('Pasien 15', 15),('Pasien 16', 16),('Pasien 17', 17),('Pasien 18', 18),('Pasien 19', 19),('Pasien 20', 20);

-- Dummy visits
INSERT INTO visits (patient_id, hospital_id, doctor_id, tanggal_kunjungan) VALUES
(1, 1, 1, '2025-09-01'),(2, 2, 2, '2025-09-01'),(3, 3, 3, '2025-09-01'),(4, 4, 4, '2025-09-01'),(5, 5, 5, '2025-09-01'),(6, 6, 6, '2025-09-01'),(7, 7, 7, '2025-09-01'),(8, 8, 8, '2025-09-01'),(9, 9, 9, '2025-09-01'),(10, 10, 10, '2025-09-01'),(11, 11, 11, '2025-09-01'),(12, 12, 12, '2025-09-01'),(13, 13, 13, '2025-09-01'),(14, 14, 14, '2025-09-01'),(15, 15, 15, '2025-09-01'),(16, 16, 16, '2025-09-01'),(17, 17, 17, '2025-09-01'),(18, 18, 18, '2025-09-01'),(19, 19, 19, '2025-09-01'),(20, 20, 20, '2025-09-01');

-- Dummy medical_records
INSERT INTO medical_records (patient_id, visit_id) VALUES
(1, 1),
(2, 2),
(3, 3),
(4, 4),
(5, 5),
(6, 6),
(7, 7),
(8, 8),
(9, 9),
(10, 10),
(11, 11),
(12, 12),
(13, 13),
(14, 14),
(15, 15),
(16, 16),
(17, 17),
(18, 18),
(19, 19),
(20, 20);

-- Dummy claims
INSERT INTO claims (hospital_id, patient_id, doctor_id, claim_date, status, visit_id, medical_record_id) VALUES
(1, 1, 1, '2025-09-01', 'draft', 1, 1),
(2, 2, 2, '2025-09-01', 'draft', 2, 2),
(3, 3, 3, '2025-09-01', 'draft', 3, 3),
(4, 4, 4, '2025-09-01', 'draft', 4, 4),
(5, 5, 5, '2025-09-01', 'draft', 5, 5),
(6, 6, 6, '2025-09-01', 'draft', 6, 6),
(7, 7, 7, '2025-09-01', 'draft', 7, 7),
(8, 8, 8, '2025-09-01', 'draft', 8, 8),
(9, 9, 9, '2025-09-01', 'draft', 9, 9),
(10, 10, 10, '2025-09-01', 'draft', 10, 10),
(11, 11, 11, '2025-09-01', 'draft', 11, 11),
(12, 12, 12, '2025-09-01', 'draft', 12, 12),
(13, 13, 13, '2025-09-01', 'draft', 13, 13),
(14, 14, 14, '2025-09-01', 'draft', 14, 14),
(15, 15, 15, '2025-09-01', 'draft', 15, 15),
(16, 16, 16, '2025-09-01', 'draft', 16, 16),
(17, 17, 17, '2025-09-01', 'draft', 17, 17),
(18, 18, 18, '2025-09-01', 'draft', 18, 18),
(19, 19, 19, '2025-09-01', 'draft', 19, 19),
(20, 20, 20, '2025-09-01', 'draft', 20, 20);
