import datetime
import os
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def process_resume_medis(data: dict, mode: str = "list", settings: dict = None) -> dict:
    """
    Generate resume medis menggunakan template resmi RS + AI wording
    mode: "list" = template structured, "naratif" = template + AI narrative
    """
    settings = settings or {}
    
    # Extract data sesuai template structure
    pasien = data.get("pasien", {})
    visit = data.get("visit", {})
    diagnosis = data.get("diagnosis", {"utama": {}, "sekunder": []})
    tindakan = data.get("tindakan", {"utama": {}, "sekunder": []})
    obat = data.get("obat", [])
    regulasi = data.get("regulasi", [])
    dokter = data.get("dokter", {})
    
    # Generate berdasarkan mode
    if mode == "naratif":
        resume_content = _generate_template_with_ai_narrative(
            pasien, visit, diagnosis, tindakan, obat, regulasi, dokter, settings
        )
    else:
        resume_content = _generate_structured_template(
            pasien, visit, diagnosis, tindakan, obat, regulasi, dokter, settings
        )
    
    return {
        "mode": mode,
        "identitas": _extract_identitas(pasien),
        "visit": visit,
        "diagnosis": diagnosis,
        "tindakan": tindakan,
        "obat": obat if settings.get("obat", True) else [],
        "regulasi": regulasi if settings.get("regulasi", True) else [],
        "dokter": dokter,
        "naratif": resume_content,
        "template_type": "discharge_summary",
        "created_at": datetime.datetime.utcnow().isoformat()
    }

def _generate_template_with_ai_narrative(pasien, visit, diagnosis, tindakan, obat, regulasi, dokter, settings):
    """Generate template dengan AI narrative di bagian ringkasan klinis"""
    
    # Prepare data untuk AI
    patient_summary = _prepare_ai_data(pasien, visit, diagnosis, tindakan, obat, dokter)
    
    # Generate AI narrative untuk ringkasan klinis
    ai_narrative = _generate_clinical_narrative(patient_summary, settings)
    
    template = f"""
RESUME MEDIS / DISCHARGE SUMMARY

═══════════════════════════════════════════════════════════════════

1. IDENTITAS PASIEN
   • Nama Pasien      : {pasien.get('nama', '-')}
   • No. RM           : {pasien.get('no_rm', '-')}
   • Umur             : {pasien.get('umur', '-')} tahun
   • Jenis Kelamin    : {pasien.get('jk', '-')}
   • Tgl Masuk        : {visit.get('tgl_masuk', '-')}
   • Tgl Pulang       : {visit.get('tgl_keluar', '-')}
   • Ruangan          : {visit.get('ruangan', '-')}

2. RINGKASAN KLINIS
   • Keluhan Utama    : {pasien.get('keluhan', '-')}
   
   • Ringkasan Perawatan:
{ai_narrative}

3. DIAGNOSIS
   • Utama            : {diagnosis.get('utama', {}).get('nama', '-')} ({diagnosis.get('utama', {}).get('icd', '-')})
   • Sekunder         : {_format_diagnosis_sekunder(diagnosis.get('sekunder', []))}

4. TINDAKAN / PROSEDUR
   • Utama            : {tindakan.get('utama', {}).get('nama', '-')} ({tindakan.get('utama', {}).get('kode', '-')})
   • Sekunder         : {_format_tindakan_sekunder(tindakan.get('sekunder', []))}

5. TERAPI OBAT
{_format_obat_template(obat)}

{_format_regulasi_template(regulasi, settings)}

6. DOKTER PENANGGUNG JAWAB
   • DPJP             : {dokter.get('dpjp', '-')}
   • Perawat          : {dokter.get('perawat', '-')}

═══════════════════════════════════════════════════════════════════
Tanggal Generate: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} WIB
    """
    
    return template.strip()

def _generate_structured_template(pasien, visit, diagnosis, tindakan, obat, regulasi, dokter, settings):
    """Generate resume dengan template terstruktur sesuai standar RS"""
    
    template = f"""
RESUME MEDIS / DISCHARGE SUMMARY

═══════════════════════════════════════════════════════════════════

1. IDENTITAS PASIEN
   • Nama Pasien      : {pasien.get('nama', '-')}
   • No. RM           : {pasien.get('no_rm', '-')}
   • Umur             : {pasien.get('umur', '-')} tahun
   • Jenis Kelamin    : {pasien.get('jk', '-')}
   • Keluhan Utama    : {pasien.get('keluhan', '-')}
   • Tgl Masuk        : {visit.get('tgl_masuk', '-')}
   • Tgl Pulang       : {visit.get('tgl_keluar', '-')}
   • Ruangan          : {visit.get('ruangan', '-')}

2. DIAGNOSIS
   • Utama            : {diagnosis.get('utama', {}).get('nama', '-')} ({diagnosis.get('utama', {}).get('icd', '-')})
   • Sekunder         : {_format_diagnosis_sekunder(diagnosis.get('sekunder', []))}

3. TINDAKAN / PROSEDUR
   • Utama            : {tindakan.get('utama', {}).get('nama', '-')} ({tindakan.get('utama', {}).get('kode', '-')})
   • Sekunder         : {_format_tindakan_sekunder(tindakan.get('sekunder', []))}

4. TERAPI OBAT
{_format_obat_template(obat)}

{_format_regulasi_template(regulasi, settings)}

5. DOKTER PENANGGUNG JAWAB
   • DPJP             : {dokter.get('dpjp', '-')}
   • Perawat          : {dokter.get('perawat', '-')}

═══════════════════════════════════════════════════════════════════
Tanggal Generate: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} WIB
    """
    
    return template.strip()

def _prepare_ai_data(pasien, visit, diagnosis, tindakan, obat, dokter):
    """Prepare data untuk AI narrative"""
    return f"""
    Pasien {pasien.get('nama', 'Unknown')}, {pasien.get('jk', '-')}, {pasien.get('umur', '-')} tahun
    Keluhan: {pasien.get('keluhan', '-')}
    Masuk: {visit.get('tgl_masuk', '-')} | Keluar: {visit.get('tgl_keluar', '-')}
    Diagnosis Utama: {diagnosis.get('utama', {}).get('nama', '-')}
    Tindakan Utama: {tindakan.get('utama', {}).get('nama', '-')}
    Obat: {', '.join([o.get('nama', '') for o in obat]) if obat else 'Tidak ada data'}
    """

def _generate_clinical_narrative(patient_data: str, settings: dict) -> str:
    """Generate ringkasan klinis naratif menggunakan OpenAI"""
    
    prompt = f"""
    Sebagai dokter DPJP, buatlah ringkasan klinis naratif untuk resume medis berdasarkan data berikut:

    {patient_data}

    Instruksi:
    1. Buat ringkasan dalam format paragraf yang mengalir
    2. Jelaskan kronologi perawatan secara singkat dan jelas
    3. Gunakan bahasa medis yang profesional
    4. Fokus pada kondisi masuk, perjalanan penyakit, dan hasil terapi
    5. {"Buat ringkas 2-3 kalimat" if settings.get('ringkas') else "Buat detail 1-2 paragraf"}
    
    Ringkasan klinis:
    """
    
    try:
        # ✅ NEW SYNTAX untuk OpenAI 1.0+
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Anda adalah dokter spesialis yang membuat ringkasan klinis untuk resume medis."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.2
        )
        
        narrative = response.choices[0].message.content.strip()
        # Format narrative untuk template
        return "     " + narrative.replace('\n', '\n     ')
        
    except Exception as e:
        return f"     [AI Error: {str(e)}] Pasien dirawat dengan diagnosis dan tindakan sesuai kondisi klinis."

# ✅ HELPER FUNCTIONS (sama seperti sebelumnya)
def _format_diagnosis_sekunder(sekunder_list) -> str:
    if not sekunder_list:
        return "-"
    
    formatted = []
    for d in sekunder_list:
        nama = d.get('nama', '-')
        kode = d.get('kode', '')
        if kode:
            formatted.append(f"{nama} ({kode})")
        else:
            formatted.append(nama)
    
    return "\n                     ".join(formatted)

def _format_tindakan_sekunder(sekunder_list) -> str:
    if not sekunder_list:
        return "-"
    
    formatted = []
    for t in sekunder_list:
        nama = t.get('nama', '-')
        kode = t.get('kode', '')
        if kode:
            formatted.append(f"{nama} ({kode})")
        else:
            formatted.append(nama)
    
    return "\n                     ".join(formatted)

def _format_obat_template(obat_list) -> str:
    if not obat_list:
        return "   • Tidak ada data obat"
    
    formatted = []
    for obat in obat_list:
        nama = obat.get('nama', '-')
        dosis = obat.get('dosis', '')
        if dosis:
            formatted.append(f"   • {nama} - {dosis}")
        else:
            formatted.append(f"   • {nama}")
    
    return '\n'.join(formatted)

def _format_regulasi_template(regulasi_list, settings) -> str:
    if not settings.get('regulasi', True) or not regulasi_list:
        return ""
    
    header = "\n6. REGULASI TERKAIT"
    formatted = []
    for reg in regulasi_list:
        judul = reg.get('judul', '-')
        keterangan = reg.get('keterangan', '')
        if keterangan:
            formatted.append(f"   • {judul} - {keterangan}")
        else:
            formatted.append(f"   • {judul}")
    
    return header + "\n" + '\n'.join(formatted)

def _extract_identitas(pasien: dict) -> dict:
    return {
        "nama": pasien.get("nama", "-"),
        "no_rm": pasien.get("no_rm", "-"),
        "umur": pasien.get("umur", "-"),
        "jk": pasien.get("jk", "-"),
        "keluhan": pasien.get("keluhan", "-")
    }




# import datetime

# def process_resume_medis(data: dict, mode: str = "list", settings: dict = None) -> dict:
#     """
#     Generate resume medis (dummy version).
#     mode: "list" atau "naratif"
#     settings: dict {regulasi: bool, obat: bool, ringkas: bool}
#     """
#     settings = settings or {}
#     pasien = data.get("pasien", {})
#     visit = data.get("visit", {})
#     diagnosis = data.get("diagnosis") if data.get("diagnosis") is not None else {"utama": {}, "sekunder": []}
#     tindakan = data.get("tindakan") if data.get("tindakan") is not None else {"utama": {}, "sekunder": []}
#     obat = data.get("obat") if data.get("obat") is not None else []
#     regulasi = data.get("regulasi") if data.get("regulasi") is not None else []
#     dokter = data.get("dokter") if data.get("dokter") is not None else {}

#     # Fallback dummy jika utama kosong
#     if not diagnosis.get("utama"):
#         diagnosis["utama"] = {"kategori": "Diagnosis", "nama": "-", "icd": "-", "klinis": "-"}
#     if not tindakan.get("utama"):
#         tindakan["utama"] = {"nama": "-", "kode": "-"}

#     identitas = {
#         "nama": pasien.get("nama", "-"),
#         "no_rm": pasien.get("no_rm", "-"),
#         "umur": pasien.get("umur", "-"),
#         "jk": pasien.get("jk", "-"),
#         "keluhan": pasien.get("keluhan", "-")
#     }

#     tgl_masuk = visit.get("tgl_masuk") or visit.get("tanggal_masuk") or "-"
#     tgl_keluar = visit.get("tgl_keluar") or visit.get("tanggal_keluar") or "-"
#     diagnosis_utama = diagnosis["utama"].get("nama", "-")
#     diagnosis_icd = diagnosis["utama"].get("icd", diagnosis["utama"].get("kode", "-"))
#     tindakan_utama = tindakan["utama"].get("nama", "-")
#     obat_list = []
#     for o in obat:
#         nama = o.get("nama", "-")
#         dosis = o.get("dosis", "")
#         if dosis:
#             obat_list.append(f"{nama} ({dosis})")
#         else:
#             obat_list.append(nama)
#     obat_str = ", ".join(obat_list) if obat_list else "-"

#     if mode == "naratif":
#         resume_text = (
#             f"Pasien {identitas['nama']} ({identitas['jk']}, {identitas['umur']} th) "
#             f"dirawat sejak {tgl_masuk} hingga {tgl_keluar} dengan keluhan {identitas['keluhan']}. "
#             f"Diagnosis utama: {diagnosis_utama} [{diagnosis_icd}]. "
#             f"Tindakan utama: {tindakan_utama}. "
#             f"Obat: {obat_str}."
#         )
#     else:
#         resume_text = "Resume Medis (List Mode)"

#     return {
#         "mode": mode,
#         "identitas": identitas,
#         "visit": visit,
#         "diagnosis": diagnosis,
#         "tindakan": tindakan,
#         "obat": obat if settings.get("obat", True) else [],
#         "regulasi": regulasi if settings.get("regulasi", True) else [],
#         "dokter": dokter,
#         "naratif": resume_text,
#         "created_at": datetime.datetime.utcnow().isoformat()
#     }

#     return {
#         "mode": mode,
#         "identitas": identitas,
#         "visit": visit,
#         "diagnosis": diagnosis,
#         "tindakan": tindakan,
#         "obat": obat if settings.get("obat", True) else [],
#         "regulasi": regulasi if settings.get("regulasi", True) else [],
#         "dokter": dokter,
#         "naratif": resume_text,
#         "created_at": datetime.datetime.utcnow().isoformat()
#     }