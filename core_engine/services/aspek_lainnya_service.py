import json
from openai import OpenAI

client = OpenAI()

# ======================================================
# 🔹 Generate Aspek Lainnya (Semi-dinamis + Filter kosong)
# ======================================================
def generate_aspek_lainnya(ctx: dict):
    """
    Analisis aspek non-klinis untuk diagnosis atau tindakan.
    - Diagnosis: program_nasional, kewenangan_dokter, pelaporan_wajib
    - Tindakan: kewenangan_pelaksana, syarat_fasilitas, kombinasi_eksklusi
    AI boleh menambahkan aspek tambahan lain.
    Field dengan nilai '-' tidak akan digunakan saat render / simpan.
    """

    diagnosis = ctx.get("diagnosis") or ""
    procedure = ctx.get("procedure") or ""
    rs_id = ctx.get("rs_id") or ""
    region_id = ctx.get("region_id") or ""
    stage = ctx.get("stage") or "diagnosis"

    # 🔹 Tentukan konteks & field utama
    subject_type = "tindakan" if procedure else "diagnosis"
    subject_label = f"{subject_type} {procedure or diagnosis}"

    base_fields = (
        ["kewenangan_pelaksana", "syarat_fasilitas", "kombinasi_eksklusi"]
        if subject_type == "tindakan"
        else ["program_nasional", "kewenangan_dokter", "pelaporan_wajib"]
    )
    field_template = {f: "-" for f in base_fields}

    # 🔹 Prompt dinamis
    prompt = f"""
Anda adalah asisten AI untuk sistem verifikasi klaim medis rumah sakit.
Analisis konteks {subject_label} dan hasilkan JSON dengan struktur berikut:

{json.dumps(field_template, indent=2, ensure_ascii=False)}

Aturan:
- Gunakan struktur di atas sebagai contoh minimal.
- **Tambahkan field lain** jika ada aspek non-klinis tambahan yang relevan.
- Jika tidak relevan, isi dengan tanda "-".
- Jangan sertakan field dengan nilai '-' dalam hasil akhir.
- Semua hasil harus di dalam key 'aspek_lainnya', dalam format JSON.
"""

    try:
        # 🔹 Panggil GPT
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        raw_output = (response.choices[0].message.content or "").strip()
        parsed = json.loads(raw_output) if raw_output else {}

        # 🔹 Ambil hasil aspek & notifikasi
        aspek = parsed.get("aspek_lainnya", {}) or {}

        # 🔹 Filter field kosong / '-'
        aspek = {k: v for k, v in aspek.items() if v and v.strip() != "-"}

        notif_section = parsed.get("notifications", {}) or parsed.get("notification", {}) or {}
        notif_msg = notif_section.get("message") or "Analisis aspek non-klinis selesai."

        return {
            "aspek_lainnya": aspek,
            "scope": "lainnya",
            "notifications": {
                "lainnya": {
                    "status": "info",
                    "message": notif_msg
                }
            }
        }

    except Exception as e:
        print(f"[ASPEK_LAINNYA] ⚠️ Error generate_aspek_lainnya: {e}")
        return {
            "aspek_lainnya": {},
            "scope": "lainnya",
            "notifications": {
                "lainnya": {
                    "status": "error",
                    "message": f"Gagal menganalisis aspek lainnya: {e}"
                }
            }
        }
