import psycopg2

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="user",
    host="0.tcp.ap.ngrok.io",
    port=17313
)
cur = conn.cursor()

# Hapus mapping patient_mapping sebelum delete patient (cascade manual)
try:
    cur.execute("DELETE FROM patient_mapping WHERE patient_id IN (SELECT id FROM patients);")
    conn.commit()
    print("Semua mapping di patient_mapping sudah dihapus.")
except Exception as e:
    print(f"Error hapus mapping: {e}")

cur.close()
conn.close()
