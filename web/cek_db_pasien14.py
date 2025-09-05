import psycopg2

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="user",
    host="0.tcp.ap.ngrok.io",
    port=13909
)
cur = conn.cursor()

# Cek klaim dan mapping untuk pasien_id=14
cur.execute("SELECT * FROM claim_logs WHERE description LIKE '%14%' ORDER BY updated_at DESC LIMIT 5;")
logs = cur.fetchall()
print("Claim logs untuk pasien 14:")
for log in logs:
    print(log)

cur.execute("SELECT * FROM visit_mapping WHERE patient_id=14;")
visit_maps = cur.fetchall()
print("Visit mapping untuk pasien 14:")
for vm in visit_maps:
    print(vm)

cur.close()
conn.close()
