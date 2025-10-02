"""
Module: backend.utils.dummy_data

Berisi generator data dummy untuk klaim:
- make_group : dummy diagnosis/komorbid/komplikasi
- make_modal : dummy procedure (ClaimProcedure + ClaimProcedureDetail)
- make_dummy : paket lengkap simulasi dummy klaim
"""

import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from backend import models


def make_group(prefix, icd_prefix):
    """3 penyakit utama + 3 turunan per penyakit"""
    return [
        {"kategori": f"{prefix} 1", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": False},
        {"kategori": f"→ {prefix} 1a", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 1b", "klinis": "-",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 1c", "klinis": "-",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},

        {"kategori": f"{prefix} 2", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": False},
        {"kategori": f"→ {prefix} 2a", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 2b", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 2c", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},

        {"kategori": f"{prefix} 3", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": False},
        {"kategori": f"→ {prefix} 3a", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 3b", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
        {"kategori": f"→ {prefix} 3c", "klinis": "",
         "icd": "", "tindakan": "", "score": random.randint(60, 95),
         "child": True},
    ]


def make_modal(icd: str, db: Session, claim_id: int, stage: str):
    """
    Hybrid make_modal:
    - Kalau claim_id belum punya procedure -> isi dummy sekali
    - Kalau sudah ada -> ambil langsung dari DB
    """
    sim = db.query(models.ClaimSimulation).filter_by(claim_id=claim_id).first()
    if not sim:
        sim = models.ClaimSimulation(
            claim_id=claim_id,
            stage=stage,
            is_dummy=True,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(sim)
        db.flush()  # dapat sim.id

    # ===== 1. Cek apakah sudah ada procedure untuk claim ini =====
    existing_procs = db.query(models.ClaimProcedure) \
        .options(joinedload(models.ClaimProcedure.procedure_details)) \
        .filter(models.ClaimProcedure.claim_id == claim_id) \
        .all()

    if not existing_procs:
        # ===== 2. Insert dummy hanya sekali =====
        dummy_procs = [
            {
                "nama": "Operasi Apendektomi",
                "detail_dummy": [
                    {
                        "icd9": "47.09",
                        "validitas": "valid",
                        "status": "utama",
                        "ina_cbg": "C-04-12",
                        "faskes": "RS Tipe C",
                        "rawat_inap": "≥ 2 hari",
                        "syarat_klinis": "Diagnosis apendisitis akut"
                    }
                ]
            },
            {
                "nama": "CT Scan Abdomen",
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "CT Scan Paha",
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Pemeriksaan Laboratorium", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "USG Abdomen", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "MRI Kepala", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Pemasangan Infus", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Pemberian Oksigen", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Terapi Nebulizer",
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Transfusi Darah",
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            },
            {
                "nama": "Terapi Infus", 
                "detail_dummy": [
                    {
                        "icd9": "88.01",
                        "validitas": "valid",
                        "status": "sekunder",
                        "ina_cbg": "C-04-15",
                        "faskes": "RS Tipe B",
                        "rawat_inap": "Tidak wajib",
                        "syarat_klinis": "Indikasi abdominal pain"
                    }
                ]
            }
        ]

        for d in dummy_procs:
            proc = models.ClaimProcedure(
                claim_id=claim_id,
                procedure_text=d["nama"],
                procedure_type="utama",      # default, bisa diubah
                requirement_flag=False,
                created_at=datetime.now()-timedelta(days=1),
                updated_at=datetime.now(),
                is_dummy=True,
                is_deleted=False
            )
            db.add(proc)
            db.flush()  # biar langsung dapat proc.id

            for det in d["detail_dummy"]:
                det_model = models.ClaimProcedureDetail(
                    procedure_id=proc.id,
                    claim_simulation_id=sim.id,   # jangan lupa isi biar NOT NULL
                    icd9_tindakan=det.get("icd9"),
                    validitas_tindakan=det.get("validitas"),
                    status_tindakan=det.get("status"),
                    ina_cbg_tindakan=det.get("ina_cbg"),
                    faskes_tindakan=det.get("faskes"),
                    rawat_inap_tindakan=det.get("rawat_inap"),
                    syarat_klinis_tindakan=det.get("syarat_klinis"),
                    is_dummy=True,
                    is_deleted=False
                )
                db.add(det_model)

        db.commit()
        existing_procs = db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).all()

    # ===== 3. Ambil semua procedure yang ada di DB =====
    tindakan = []
    for p in existing_procs:
        tindakan.append({
            "id": p.id,
            "nama": p.procedure_text,
            "deskripsi": p.description,
            "detail": [
                {
                    "icd9": d.icd9_tindakan,
                    "deskripsi": f"{d.icd9_tindakan or ''} | {d.status_tindakan or ''} | {d.ina_cbg_tindakan or ''}",
                    "validitas": d.validitas_tindakan,
                    "status": d.status_tindakan,
                    "ina_cbg": d.ina_cbg_tindakan,
                    "faskes": d.faskes_tindakan,
                    "rawat_inap": d.rawat_inap_tindakan,
                    "syarat_klinis": d.syarat_klinis_tindakan,
                }
                for d in p.procedure_details if not d.is_deleted
            ]
        })

    return tindakan


def make_dummy(tab):
    """Generate dummy penuh untuk tab klaim (diagnosis, komorbid, komplikasi, modal, evaluasi)"""
    data = {
        "diagnosis": make_group("Diagnosis", f"{tab.upper()}DX"),
        "komorbid": make_group("Komorbid", f"{tab.upper()}KM"),
        "komplikasi": make_group("Komplikasi", f"{tab.upper()}KP"),
        "modal": {
            "klinis": {
                "justifikasi": "GFR 15-29, BMI 30-40",
                "bukti_klinis": "Belum ada bukti klinis",
                "syarat_klinis": "Belum ada syarat klinis",
            },
            "icd10": {
                "kode_icd": "E11.24",
                "struktur_icd10": "D42.5",
                "kode_ganda": "A4.10",
                "z_code": "Z18",
                "kode_bpjs_khusus": "K1",
            },
            "tindakan": [],  # dari DB (dummy sekali aja)
            "rawat_inap": {
                "indikasi": "Tidak ada indikasi khusus",
                "lama_rawat": "3 hari",
                "perpanjangan": "Tidak"
            },
            "faskes": {"kesesuaian_rs": "Tipe C"},
            "rujukan": {"syarat": "Tidak ada", "kelayakan": "Layak"}
        },
        "simulasi": {
            "utama": None,
            "sekunder": [],
            "tindakanUtama": None,
            "tindakanSekunder": [],
        },
        "evaluasi": {
            "kombinasi_diagnosis": {
                "validitas": "valid",
                "validitas_detail": "Sepsis + DM valid (komorbid umum)",
                "severity": "Medium (Sepsis + DM)",
                "kode_ina_cbg": "D-04-12",
                "estimasi_tarif": "Rp 7.500.000",
                "syarat_klinis": "HbA1c + kultur darah",
                "evaluasi_faskes": "Minimal RS Tipe B",
                "rawat_inap": "Minimal 3 hari rawat"
            },
            "kombinasi_tindakan": [
                {
                    "tindakan": "Antibiotik IV",
                    "validitas": "valid",
                    "validitas_detail": "Antibiotik IV",
                    "status": "optional",
                    "tarif_impact": "Rp 7.500.000",
                    "faskes": "RS Tipe B",
                    "rawat_inap": "≥ 3 hari",
                    "syarat_klinis": "Infus IV tercatat ganda - tidak pengaruh"
                },
                {
                    "validitas": "valid",
                    "validitas_detail": "Ventilasi Mekanik",
                    "tindakan": "Ventilasi Mekanik",
                    "status": "wajib",
                    "tarif_impact": "Rp 12.500.000",
                    "faskes": "RS Tipe C",
                    "rawat_inap": "≥ 5 hari",
                    "syarat_klinis": "PCI + CABG bersamaan - tidak lazim"
                }
            ],
            "alternatif": [
                {
                    "kombinasi": "Sepsis + ARDS",
                    "severity": "High",
                    "kode_ina_cbg": "D-04-13",
                    "tarif": "Rp 12.500.000",
                    "syarat_klinis": "Ventilasi Mekanik + catatan ICU",
                    "faskes": "RS Tipe B",
                    "rawat_inap": "≥ 3 hari + ICU ≥ 2 hari",
                    "tindakan_wajib": "Ventilasi Mekanik"
                },
                {
                    "kombinasi": "Sepsis + DM + ARDS",
                    "severity": "invalid",
                    "kode_ina_cbg": "D-04-13",
                    "tarif": "Rp 13.500.000",
                    "syarat_klinis": "Ventilasi Mekanik + catatan ICU",
                    "faskes": "RS Tipe B / C",
                    "rawat_inap": "≥ 3 hari + ICU ≥ 2 hari",
                    "tindakan_wajib": "Ventilasi Mekanik"
                }
            ]
        }
    }

    print(f"[make_dummy] tab={tab}, "
          f"diagnosis={len(data['diagnosis'])}, "
          f"komorbid={len(data['komorbid'])}, "
          f"komplikasi={len(data['komplikasi'])}")
    
    return data

def make_dummy_idrg_diagnosis():
    return {
        "group_idrg": "I-SEP-2",
        "severity_index": "2",
        "checklist": "Catat kultur darah & LOS ≥ 3 hari",
        "faktor_severity": "Sepsis + DM",
        "ungroupable_alert": "Ungroupable jika kultur darah hilang",
        "simulasi_tarif": "Rp 7.200.000",
        "gap_analysis": "+Rp 1.500.000",
    }

def make_dummy_idrg_summary():
    return {
        "group_idrg_kombinasi": "I-SEP-DM-3",
        "severity_kombinasi": "Tinggi",
        "checklist_kombinasi": "HbA1c + kultur darah wajib",
        "faktor_severity": "Sepsis + DM + komplikasi",
        "risiko_ungroupable": "HbA1c tidak tercatat",
        "estimasi_tarif": "Rp 9.000.000",
        "gap_inacbg_vs_idrg": "-Rp 2.000.000",
        "rekomendasi_ai": "Tambahkan dokumentasi HbA1c di semua pasien DM"
    }

from datetime import datetime

def make_dummy_idrg_regulasi(context: str, field: str):
    mapping = {
        "group_idrg": "Group i-DRG",
        "severity_index": "Severity Index",
        "checklist": "Checklist Dokumentasi",
        "ungroupable_alert": "Ungroupable Alert",
        "group_idrg_kombinasi": "Group i-DRG Kombinasi",
        "severity_kombinasi": "Severity Kombinasi",
        "checklist_kombinasi": "Checklist i-DRG Kombinasi",
        "risiko_ungroupable": "Risiko Ungroupable"
    }

    label = mapping.get(field, field)

    if context == "diagnosis":
        return {
            "judul_regulasi": f"Aturan i-DRG Diagnosis - {label}",
            "dasar_hukum": "Permenkes",
            "bab_pasal": "Bab I Pasal 3",
            "isi": f"Regulasi terkait {label} pada i-DRG Diagnosis (dummy).",
            "is_dummy": True,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    elif context == "summary":
        return {
            "judul_regulasi": f"Aturan i-DRG Summary - {label}",
            "dasar_hukum": "Permenkes",
            "bab_pasal": "Bab II Pasal 6",
            "isi": f"Regulasi terkait {label} pada i-DRG Summary (dummy).",
            "is_dummy": True,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    else:
        return {
            "judul_regulasi": "Aturan i-DRG (Unknown Context)",
            "dasar_hukum": "Permenkes",
            "bab_pasal": "-",
            "isi": f"Context {context} tidak dikenali (dummy).",
            "is_dummy": True,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

def dummy_diagnosis_list():
    return [
        {"id": 1, "code": "R05", "name": "Batuk"},
        {"id": 2, "code": "J20.9", "name": "Bronkitis akut, tidak spesifik"},
        {"id": 3, "code": "J18.9", "name": "Pneumonia"},
        {"id": 4, "code": "J45", "name": "Asma"}
    ]

def dummy_diagnosis_detail(icd_code: str):
    base = {
        "kategori": "Unknown",
        "klinis": {"justifikasi": "-", "bukti_klinis": "-", "syarat_klinis": "-"},
        "icd10": {
            "kode_icd": icd_code,
            "struktur_icd10": "-",
            "kode_ganda": "-",
            "z_code": "-",
            "kode_bpjs_khusus": "-"
        },
        "tindakan": [
            {"procedure_text": "Pemeriksaan penunjang standar"}
        ],
        "rawat_inap": {"indikasi": "-", "lama_rawat": "-", "perpanjangan": "-"},
        "faskes": {"kesesuaian_rs": "-"},
        "rujukan": {"syarat": "-", "kelayakan": "-"},
        "idrg_diagnosis": make_dummy_idrg_diagnosis()
    }

    mapping = {
        "R05": {
            "kategori": "Batuk",
            "klinis": {
                "justifikasi": "Batuk > 2 minggu",
                "bukti_klinis": "Riwayat batuk persisten",
                "syarat_klinis": "Foto thorax + pemeriksaan dahak"
            },
            "icd10": {
                "kode_icd": "R05",
                "struktur_icd10": "Bab XVIII",
                "kode_ganda": "R05",
                "z_code": "Z94",
                "kode_bpjs_khusus": "K2"
            },
            "tindakan": [
                {"procedure_text": "Terapi batuk simptomatik"}
            ],
            "rawat_inap": {
                "indikasi": "Tidak wajib rawat inap",
                "lama_rawat": "1-2 hari",
                "perpanjangan": "Tidak ada"
            },
            "faskes": {"kesesuaian_rs": "RS Tipe C"},
            "rujukan": {"syarat": "Jika komplikasi", "kelayakan": "Layak"},
            "idrg_diagnosis": make_dummy_idrg_diagnosis()
        },
        "J20.9": {
            "kategori": "Bronkitis Akut",
            "klinis": {
                "justifikasi": "Batuk + wheezing",
                "bukti_klinis": "Auskultasi paru",
                "syarat_klinis": "Spirometri"
            },
            "icd10": {
                "kode_icd": "J20.9",
                "struktur_icd10": "Bab X",
                "kode_ganda": "J20.9",
                "z_code": "Z95",
                "kode_bpjs_khusus": "K3"
            },
            "tindakan": [
                {"procedure_text": "Bronkodilator inhalasi"}
            ],
            "rawat_inap": {
                "indikasi": "Wajib jika sesak nafas",
                "lama_rawat": "3-5 hari",
                "perpanjangan": "Berdasarkan kondisi"
            },
            "faskes": {"kesesuaian_rs": "RS Tipe B"},
            "rujukan": {"syarat": "Jika gagal terapi", "kelayakan": "Layak"},
            "idrg_diagnosis": make_dummy_idrg_diagnosis()
        },
        "J18.9": { 
            "kategori": "Pneumonia",
            "klinis": {
                "justifikasi": "Demam + batuk + infiltrat",
                "bukti_klinis": "Foto thorax",
                "syarat_klinis": "Pemeriksaan darah lengkap"
            },
            "icd10": {
                "kode_icd": "J18.9",
                "struktur_icd10": "Bab X",
                "kode_ganda": "J18.9",
                "z_code": "Z96",
                "kode_bpjs_khusus": "K4"
            },
            "tindakan": [
                {"procedure_text": "Antibiotik spektrum luas"}
            ],
            "rawat_inap": {
                "indikasi": "Wajib rawat inap",
                "lama_rawat": "5-7 hari",
                "perpanjangan": "Berdasarkan respon terapi"
            },
            "faskes": {"kesesuaian_rs": "RS Tipe A"},
            "rujukan": {"syarat": "Jika gagal terapi", "kelayakan": "Layak"},
            "idrg_diagnosis": make_dummy_idrg_diagnosis()
         },
        "J45":   { 
            "kategori": "Asma",
            "klinis": {
                "justifikasi": "Demam + batuk + infiltrat",
                "bukti_klinis": "Foto thorax",
                "syarat_klinis": "Pemeriksaan darah lengkap"
            },
            "icd10": {
                "kode_icd": "J45",
                "struktur_icd10": "Bab X",
                "kode_ganda": "J45",
                "z_code": "Z97",
                "kode_bpjs_khusus": "K5"
            },
            "tindakan": [
                {"procedure_text": "Antibiotik spektrum luas"}
            ],
            "rawat_inap": {
                "indikasi": "Wajib rawat inap",
                "lama_rawat": "5-7 hari",
                "perpanjangan": "Berdasarkan respon terapi"
            },
            "faskes": {"kesesuaian_rs": "RS Tipe A"},
            "rujukan": {"syarat": "Jika gagal terapi", "kelayakan": "Layak"},
            "idrg_diagnosis": make_dummy_idrg_diagnosis()
         }
    }

    return mapping.get(icd_code, base)