# ==========================================================
# claim_stage_helper.py (FINAL FIX)
# ==========================================================
from ..models import Visit

def determine_stages_from_visits(visits):
    """
    Menentukan stage klaim (Admission/Daily/Discharge)
    dengan logika prioritas:
    1️⃣ Berdasarkan 'jenis_kunjungan'
    2️⃣ Fallback ke 'poli' hanya bila semua jenis_kunjungan kosong
    3️⃣ Tidak boleh muncul Daily/Discharge untuk Rawat Jalan murni
    """
    if not visits or len(visits) == 0:
        return ["admission"]

    def norm(text):
        return (text or "").lower().strip()

    jenis_list = [norm(v.jenis_kunjungan) for v in visits if v.jenis_kunjungan]
    poli_list = [norm(v.poli) for v in visits if v.poli]

    # 🔹 Kalau semua visit punya jenis_kunjungan (tidak kosong)
    if jenis_list:
        has_igd = any("igd" in j for j in jenis_list)
        has_inap = any("inap" in j for j in jenis_list)
        has_jalan = any("jalan" in j for j in jenis_list)

        # ✅ Kasus rawat jalan murni
        if all("jalan" in j for j in jenis_list) and not (has_igd or has_inap):
            stages = ["admission"]

        # ✅ IGD → Rawat Jalan
        elif has_igd and has_jalan and not has_inap:
            stages = ["admission", "discharge"]

        # ✅ Ada rawat inap (langsung / dari IGD / dari poli)
        elif has_inap:
            stages = ["admission", "daily", "discharge"]

        # ✅ IGD saja (tanpa rawat inap)
        elif has_igd and not has_inap:
            stages = ["admission", "discharge"]

        else:
            stages = ["admission"]

    else:
        # 🔹 Semua jenis_kunjungan kosong → fallback ke nama poli
        poli_set = set(poli_list)
        has_igd = any("igd" in p or "gawat darurat" in p for p in poli_set)
        has_inap = any(
            "rawat inap" in p or "bangsal" in p or "ruang" in p or "perawatan" in p
            or "icu" in p or "picu" in p or "nicu" in p
            for p in poli_set
        )
        has_jalan = any("poli" in p or "klinik" in p for p in poli_set)

        if has_inap:
            stages = ["admission", "daily", "discharge"]
        elif has_igd and not has_inap:
            stages = ["admission", "discharge"]
        elif has_jalan:
            stages = ["admission"]
        else:
            stages = ["admission"]

    print(f"[AUTO-STAGE] jenis={jenis_list or '-'} | poli={poli_list or '-'} → {stages}")
    return stages
