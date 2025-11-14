-- Fix VARCHAR(10) columns in patients table to VARCHAR(20)
-- Run this directly on VPS database

-- Update no_ktp to VARCHAR(20) (for 16-digit NIK)
ALTER TABLE patients 
ALTER COLUMN no_ktp TYPE VARCHAR(20);

-- Update no_rm to VARCHAR(20)
ALTER TABLE patients 
ALTER COLUMN no_rm TYPE VARCHAR(20);

-- Update no_bpjs to VARCHAR(20)
ALTER TABLE patients 
ALTER COLUMN no_bpjs TYPE VARCHAR(20);

-- Update no_hp to VARCHAR(20)
ALTER TABLE patients 
ALTER COLUMN no_hp TYPE VARCHAR(20);

-- Update email to VARCHAR(120) (as per model definition)
ALTER TABLE patients 
ALTER COLUMN email TYPE VARCHAR(120);

-- Update jenis_kelamin (already 10, keep as is)
-- ALTER TABLE patients ALTER COLUMN jenis_kelamin TYPE VARCHAR(10);

-- Verify changes
SELECT 
    column_name, 
    data_type, 
    character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'patients' 
    AND column_name IN ('no_ktp', 'no_rm', 'no_bpjs', 'no_hp', 'email', 'jenis_kelamin')
ORDER BY column_name;
