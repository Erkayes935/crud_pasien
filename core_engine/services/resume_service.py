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
    diagnosis = data.get("diagnosis") if data.get("diagnosis") is not None else {"utama": {}, "sekunder": []}
    tindakan = data.get("tindakan") if data.get("tindakan") is not None else {"utama": {}, "sekunder": []}
    obat = data.get("obat") if data.get("obat") is not None else []
    regulasi = data.get("regulasi") if data.get("regulasi") is not None else []
    dokter = data.get("dokter") if data.get("dokter") is not None else {}

    # Fallback dummy jika utama kosong
    if not diagnosis.get("utama"):
        diagnosis["utama"] = {"kategori": "Diagnosis", "nama": "-", "icd": "-", "klinis": "-"}
    if not tindakan.get("utama"):
        tindakan["utama"] = {"nama": "-", "kode": "-"}

    identitas = {
        "nama": pasien.get("nama", "-"),
        "no_rm": pasien.get("no_rm", "-"),
        "umur": pasien.get("umur", "-"),
        "jk": pasien.get("jk", "-"),
        "keluhan": pasien.get("keluhan", "-")
    }

    tgl_masuk = visit.get("tgl_masuk") or visit.get("tanggal_masuk") or "-"
    tgl_keluar = visit.get("tgl_keluar") or visit.get("tanggal_keluar") or "-"
    diagnosis_utama = diagnosis["utama"].get("nama", "-")
    diagnosis_icd = diagnosis["utama"].get("icd", diagnosis["utama"].get("kode", "-"))
    tindakan_utama = tindakan["utama"].get("nama", "-")
    obat_list = []
    for o in obat:
        nama = o.get("nama", "-")
        dosis = o.get("dosis", "")
        if dosis:
            obat_list.append(f"{nama} ({dosis})")
        else:
            obat_list.append(nama)
    obat_str = ", ".join(obat_list) if obat_list else "-"

    if mode == "naratif":
        resume_text = (
            f"Pasien {identitas['nama']} ({identitas['jk']}, {identitas['umur']} th) "
            f"dirawat sejak {tgl_masuk} hingga {tgl_keluar} dengan keluhan {identitas['keluhan']}. "
            f"Diagnosis utama: {diagnosis_utama} [{diagnosis_icd}]. "
            f"Tindakan utama: {tindakan_utama}. "
            f"Obat: {obat_str}."
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
        "created_at": datetime.datetime.utcnow().isoformat()
    }

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
        "created_at": datetime.datetime.utcnow().isoformat()
    }
