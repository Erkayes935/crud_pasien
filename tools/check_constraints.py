"""Quick script to check constraints on inacbg_tariff table"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import inspect
from web.backend.database import engine

inspector = inspect(engine)

print("=" * 60)
print("INDEXES on inacbg_tariff:")
print("=" * 60)
indexes = inspector.get_indexes('inacbg_tariff')
for idx in indexes:
    unique_flag = "UNIQUE" if idx.get('unique', False) else "NON-UNIQUE"
    print(f"  [{unique_flag}] {idx['name']}: {idx['column_names']}")

print("\n" + "=" * 60)
print("UNIQUE CONSTRAINTS on inacbg_tariff:")
print("=" * 60)
constraints = inspector.get_unique_constraints('inacbg_tariff')
if constraints:
    for c in constraints:
        print(f"  ❌ {c['name']}: {c['column_names']}")
else:
    print("  ✅ None (good!)")

print("\n" + "=" * 60)
