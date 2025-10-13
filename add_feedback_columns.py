#!/usr/bin/env python3
"""
Script untuk menambahkan kolom feedback ke tabel rules_master
Tanpa menggunakan alembic, langsung dengan SQLAlchemy
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'web'))

from web.backend.database import engine
from sqlalchemy import text
import traceback

def add_feedback_columns():
    """Tambahkan kolom feedback ke tabel rules_master"""
    
    try:
        print("🔄 Menambahkan kolom feedback ke tabel rules_master...")
        
        with engine.connect() as conn:
            # Check if columns already exist
            check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'rules_master' 
            AND column_name IN ('feedback', 'feedback_by', 'feedback_date')
            """
            existing_columns = conn.execute(text(check_query)).fetchall()
            existing_column_names = [row[0] for row in existing_columns]
            
            print(f"📋 Kolom yang sudah ada: {existing_column_names}")
            
            # Add feedback column if not exists
            if 'feedback' not in existing_column_names:
                conn.execute(text("ALTER TABLE rules_master ADD COLUMN feedback TEXT"))
                print("✅ Kolom 'feedback' berhasil ditambahkan")
            else:
                print("ℹ️  Kolom 'feedback' sudah ada")
            
            # Add feedback_by column if not exists
            if 'feedback_by' not in existing_column_names:
                conn.execute(text("ALTER TABLE rules_master ADD COLUMN feedback_by VARCHAR(255)"))
                print("✅ Kolom 'feedback_by' berhasil ditambahkan")
            else:
                print("ℹ️  Kolom 'feedback_by' sudah ada")
            
            # Add feedback_date column if not exists
            if 'feedback_date' not in existing_column_names:
                conn.execute(text("ALTER TABLE rules_master ADD COLUMN feedback_date TIMESTAMP"))
                print("✅ Kolom 'feedback_date' berhasil ditambahkan")
            else:
                print("ℹ️  Kolom 'feedback_date' sudah ada")
            
            conn.commit()
            print("🎉 Semua kolom feedback berhasil ditambahkan!")
            
            # Verify the changes
            verify_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'rules_master' 
            AND column_name IN ('feedback', 'feedback_by', 'feedback_date')
            ORDER BY column_name
            """
            columns = conn.execute(text(verify_query)).fetchall()
            print("\n📊 Verifikasi kolom feedback:")
            for column_name, data_type in columns:
                print(f"   - {column_name}: {data_type}")
                
    except Exception as e:
        print(f"❌ Error saat menambahkan kolom feedback: {str(e)}")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting feedback columns addition...")
    success = add_feedback_columns()
    
    if success:
        print("\n✅ Script selesai! Kolom feedback sudah siap digunakan.")
    else:
        print("\n❌ Script gagal! Silakan periksa error di atas.")