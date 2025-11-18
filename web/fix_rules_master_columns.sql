-- Add missing columns to rules_master table
-- These columns are expected by HousekeepingMixin

ALTER TABLE rules_master 
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE rules_master 
ADD COLUMN IF NOT EXISTS is_dummy BOOLEAN NOT NULL DEFAULT false;

-- Verify columns
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'rules_master' 
ORDER BY ordinal_position;
