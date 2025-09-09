import datetime

def process_resume_medis(data: dict, mode: str = "list", settings: dict = None) -> dict:
    """
    Generate resume medis (dummy version).
    mode: "list" atau "naratif"
    settings: dict {regulasi: bool, obat: bool, ringkas: bool}
    """
    settings = settings or {}
    pasien = data.get("pasien", {})
    visit = data.get("visit", {})
    diagnosis = data.get("diagnosis", {})
    tindakan = data.get("tindakan", {})
    obat = data.get("obat", [])
    regulasi = data.get("regulasi", [])
    dokter = data.get("dokter", {})

    # Fallback untuk field penting
    identitas = {
        "nama": pasien.get("nama", "-"),
        "no_rm": pasien.get("no_rm", "-"),
        "umur": pasien.get("umur", "-"),
        "jk": pasien.get("jk", "-"),
        "keluhan": pasien.get("keluhan", "-")
    }

    if mode == "naratif":
        resume_text = (
            f"Pasien {identitas['nama']} ({identitas['jk']}, {identitas['umur']} th) "
            f"dirawat sejak {visit.get('tgl_masuk', '-') } dengan keluhan {identitas['keluhan']}. "
            f"Diagnosis utama {diagnosis.get('utama', {}).get('nama', '-')} "
            f"({diagnosis.get('utama', {}).get('kode', '-')}). "
            f"Tindakan utama {tindakan.get('utama', {}).get('nama', '-')}."
        )
    else:
        if settings.get("ringkas", False):
            resume_text = (
                f"Pasien {identitas['nama']} ({identitas['jk']}, {identitas['umur']} th)\n"
                f"Diagnosis utama: {diagnosis.get('utama', {}).get('nama', '-')} [{diagnosis.get('utama', {}).get('kode', '-')}]\n"
                f"Tindakan utama: {tindakan.get('utama', {}).get('nama', '-')} [{tindakan.get('utama', {}).get('kode', '-')}]"
            )
        else:
            resume_text = "Resume Medis (List Mode)"

    return {
        "mode": mode,
        "identitas": identitas,
        "visit": visit,
        "diagnosis": diagnosis,
        "tindakan": tindakan,
        "obat": obat if settings.get("obat", True) else [],
        "regulasi": regulasi if settings.get("regulasi", True) else [],
        "dokter": dokter,
        "naratif": resume_text,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
