-- Dummy user untuk aaa@yopmail.com, role doctor, hospital_id sesuai RS yang ada (misal RS Siloam Bandung, id=3)
INSERT INTO users (email, role, hospital_id, nama, password) VALUES ('aaa@yopmail.com', 'doctor', 3, 'Dr. AAA', 'dummy123');

-- Dummy klaim untuk semua RS
INSERT INTO claims (hospital_id, pasien_id, dokter_id, tanggal, status) VALUES
(1, 99, NULL, '2025-09-01', 'draft'),
(2, 90, NULL, '2025-09-01', 'draft'),
(3, 89, NULL, '2025-09-01', 'draft'),
(4, 88, NULL, '2025-09-01', 'draft'),
(5, 87, NULL, '2025-09-01', 'draft'),
(6, 86, NULL, '2025-09-01', 'draft'),
(7, 85, NULL, '2025-09-01', 'draft'),
(8, 84, NULL, '2025-09-01', 'draft'),
(9, 83, NULL, '2025-09-01', 'draft');

-- Sesuaikan pasien_id dan dokter_id jika perlu, ini hanya contoh struktur.
