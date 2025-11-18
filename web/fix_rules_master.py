"""
Fix rules_master missing columns (is_deleted, is_dummy)
Run this script to add missing HousekeepingMixin columns
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

sql = """
-- Add missing columns to rules_master table
ALTER TABLE rules_master 
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE rules_master 
ADD COLUMN IF NOT EXISTS is_dummy BOOLEAN NOT NULL DEFAULT false;

-- Also fix regional_reports if needed
ALTER TABLE regional_reports 
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE regional_reports 
ADD COLUMN IF NOT EXISTS is_dummy BOOLEAN NOT NULL DEFAULT false;
"""

try:
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
        print("✅ Successfully added missing columns to rules_master and regional_reports!")
        
        # Verify
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'rules_master' 
            AND column_name IN ('is_deleted', 'is_dummy')
            ORDER BY column_name;
        """))
        cols = [row[0] for row in result]
        print(f"✅ Verified columns in rules_master: {cols}")
        
except Exception as e:
    print(f"❌ Error: {e}")
