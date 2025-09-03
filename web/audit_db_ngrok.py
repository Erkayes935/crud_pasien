import psycopg2

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="user",
    host="0.tcp.ap.ngrok.io",
    port=17313
)

cur = conn.cursor()

# Ambil semua tabel
tables_query = """
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
"""
cur.execute(tables_query)
tables = [row[0] for row in cur.fetchall()]

print("Tabel di database:")
for table in tables:
    print(f"- {table}")
    cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}';")
    for col, dtype in cur.fetchall():
        print(f"    {col} ({dtype})")

cur.close()
conn.close()
