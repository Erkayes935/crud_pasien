import psycopg2

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="user",
    host="0.tcp.ap.ngrok.io",
    port=17313
)
cur = conn.cursor()

# 1. visit_mapping: rename uuid -> visit_uuid, tambah kolom
try:
    cur.execute("ALTER TABLE visit_mapping RENAME COLUMN uuid TO visit_uuid;")
except Exception as e:
    print(f"visit_mapping: {e}")
for col, typ in [
    ("ai_status", "VARCHAR(20) DEFAULT 'pending'"),
    ("submitted_at", "TIMESTAMP"),
    ("completed_at", "TIMESTAMP")
]:
    try:
        cur.execute(f"ALTER TABLE visit_mapping ADD COLUMN {col} {typ};")
    except Exception as e:
        print(f"visit_mapping: {col}: {e}")

# 2. claim_logs: rename details -> description, user_id -> updated_by, tambah updated_at
try:
    cur.execute("ALTER TABLE claim_logs RENAME COLUMN details TO description;")
except Exception as e:
    print(f"claim_logs: {e}")
try:
    cur.execute("ALTER TABLE claim_logs RENAME COLUMN user_id TO updated_by;")
except Exception as e:
    print(f"claim_logs: {e}")
try:
    cur.execute("ALTER TABLE claim_logs ADD COLUMN updated_at TIMESTAMP;")
except Exception as e:
    print(f"claim_logs: updated_at: {e}")

conn.commit()
cur.close()
conn.close()
print("Selesai update struktur tabel.")
