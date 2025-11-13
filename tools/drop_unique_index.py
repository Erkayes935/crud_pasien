"""Drop unique index on kode_cbg"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web.backend.database import engine
from sqlalchemy import text

print("Dropping unique index ix_inacbg_tariff_kode_cbg...")
with engine.connect() as conn:
    conn.execute(text('DROP INDEX IF EXISTS ix_inacbg_tariff_kode_cbg'))
    conn.commit()
    print("✅ Dropped unique index!")
