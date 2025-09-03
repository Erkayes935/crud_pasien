import psycopg2
from psycopg2 import sql

# Ganti dengan DATABASE_URL ngrok kamu
db_url = "postgresql://postgres:user@0.tcp.ap.ngrok.io:17313/postgres"

add_columns = [
    ("diagnosis_awal", "TEXT"),
    ("tindakan", "TEXT"),
    ("obat", "TEXT"),
    ("status", "VARCHAR(50)"),
    ("hasil", "TEXT"),
    ("kode_icd", "VARCHAR(50)"),
    ("tanggal_kunjungan", "DATE")
]

def column_exists(cur, table, column):
    cur.execute("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name=%s AND column_name=%s
    """, (table, column))
    return cur.fetchone() is not None

with psycopg2.connect(db_url) as conn:
    with conn.cursor() as cur:
        for col, tipe in add_columns:
            if not column_exists(cur, "claims", col):
                print(f"Menambah kolom {col} ke tabel claims...")
                cur.execute(sql.SQL("ALTER TABLE claims ADD COLUMN {} {} NULL").format(
                    sql.Identifier(col), sql.SQL(tipe)
                ))
            else:
                print(f"Kolom {col} sudah ada.")
        conn.commit()
print("Selesai update kolom claims.")
