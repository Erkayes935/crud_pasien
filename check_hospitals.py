import os
from sqlalchemy import create_engine, text

# Ganti dengan URL database ngrok yang dipakai di backend/config.py atau .env
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT id, nama FROM hospitals"))
    hospitals = result.fetchall()
    print(f"Jumlah RS di database: {len(hospitals)}")
    for h in hospitals:
        print(f"ID: {h.id}, Nama: {h.nama}")
