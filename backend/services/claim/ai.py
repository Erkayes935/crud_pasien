from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from typing import List, Dict, Any
from ... import models
from ...utils.dummy_data import make_dummy, make_modal
from .helper import parse_number

# ==================================================
# AI RECOMMENDATION
# ==================================================

def store_ai_recommendations(db: Session, claim_id: int, dummy_data: dict, stage: str):
        # 🔹 summary dulu
    print(f"[STORE] claim={claim_id}, stage={stage}, "
          f"dx={len(dummy_data.get('diagnosis', []))}, "
          f"km={len(dummy_data.get('komorbid', []))}, "
          f"kp={len(dummy_data.get('komplikasi', []))}")

    """Simpan hasil rekomendasi AI dummy ke tabel."""
    sim = db.query(models.ClaimSimulation).filter_by(claim_id=claim_id, stage=stage).first()
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
        db.flush()

    # Diagnosis / Komorbid / Komplikasi
    for category in ["diagnosis", "komorbid", "komplikasi"]:
        for item in dummy_data.get(category, []):
            print(f"[STORE] claim={claim_id}, stage={stage}, category={category}, count={len(item)}")  # 🔹 log
            diag = models.ClaimDiagnosis(
                claim_id=claim_id,
                diagnosis_type=category,
                diagnosis_text=item.get("kategori"),
                is_dummy=True,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(diag)
            db.flush()

            rec = models.ClaimAIRecommendation(
                claim_id=claim_id,
                stage=stage,
                category=category,
                confidence_score=item.get("score"),
                diagnosis_id=diag.id,
                child=item.get("child", False),
                is_dummy=True,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(rec)

            # Regulasi dummy diagnosis
            existing_regs = db.query(models.ClaimRegulationDetail).filter_by(
                claim_id=diag.claim_id,
                diagnosis_id=diag.id,
                is_deleted=False
            ).all()

            if not existing_regs:
                reg = models.ClaimRegulationDetail(
                    claim_id=diag.claim_id,
                    diagnosis_id=diag.id,
                    procedure_id=None,
                    judul_regulasi="PNPK Sepsis 2020",
                    dasar_hukum="PNPK",
                    bab_pasal="Bab II Pasal 3",
                    isi="Diagnosis sepsis harus berdasarkan kriteria klinis",
                    is_deleted=False,
                    is_dummy=True,
                    created_at=datetime.utcnow()-timedelta(days=1),
                    updated_at=datetime.utcnow()
                )
                db.add(reg)

    # Regulasi dummy untuk Procedure
    procedures = db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).all()
    for proc in procedures:
        existing_proc_regs = db.query(models.ClaimRegulationDetail).filter_by(
            claim_id=claim_id,
            procedure_id=proc.id,
            is_deleted=False
        ).all()

        if not existing_proc_regs:
            reg = models.ClaimRegulationDetail(
                claim_id=claim_id,
                diagnosis_id=None,
                procedure_id=proc.id,
                judul_regulasi="PNPK Sepsis 2020",
                dasar_hukum="PNPK",
                bab_pasal="Bab II Pasal 3",
                isi=f"Regulasi terkait tindakan {proc.procedure_text}",
                is_deleted=False,
                is_dummy=True,
                created_at=datetime.utcnow()-timedelta(days=1),
                updated_at=datetime.utcnow()
            )
            db.add(reg)

    db.commit()

def ai_recommendation(db: Session, claim_id: int) -> List[Dict[str, Any]]:
    print(f"[AI RECOMMENDATION] claim_id={claim_id}")
    """Generate dummy rekomendasi AI untuk klaim (admission/daily/discharge)."""
    admission = make_dummy("admission")
    print("[DEBUG admission]", admission)
    daily = [make_dummy("daily1"), make_dummy("daily2")]
    print("[DEBUG admission]", admission)
    discharge = make_dummy("discharge")
    print("[DEBUG admission]", admission)

    # Reset data lama
    db.query(models.ClaimProcedureDetail).filter(
        models.ClaimProcedureDetail.procedure_id.in_(
            db.query(models.ClaimProcedure.id).filter_by(claim_id=claim_id)
        )
    ).delete(synchronize_session=False)
    db.query(models.ClaimAIRecommendation).filter_by(claim_id=claim_id).delete()
    db.query(models.ClaimRegulationDetail).filter_by(claim_id=claim_id).delete()
    db.query(models.ClaimSimulation).filter_by(claim_id=claim_id).delete()
    db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).delete()
    db.query(models.ClaimDiagnosis).filter_by(claim_id=claim_id).delete()

    db.commit()

    # Seed dummy procedures
    admission["tindakan"] = make_modal("A41", db, claim_id, "admission")
    store_ai_recommendations(db, claim_id, admission, "admission")

    for idx, day in enumerate(daily):
        day["tindakan"] = make_modal("A41", db, claim_id, f"daily{idx+1}")
        store_ai_recommendations(db, claim_id, day, f"daily{idx+1}")

    discharge["tindakan"] = make_modal("A41", db, claim_id, "discharge")
    store_ai_recommendations(db, claim_id, discharge, "discharge")

    # Return hasil AIRecommendation
    recs = db.query(models.ClaimAIRecommendation).options(
        joinedload(models.ClaimAIRecommendation.diagnosis)
    ).filter_by(claim_id=claim_id).all()

    data = []
    for rec in recs:
        kategori = rec.diagnosis.diagnosis_text if rec.diagnosis else "-"
        klinis = "-"
        if rec.diagnosis:
            klinis = ", ".join(filter(None, [
                getattr(rec.diagnosis, "justifikasi", None),
                getattr(rec.diagnosis, "bukti_klinis", None),
                getattr(rec.diagnosis, "syarat_klinis", None),
            ])) or "-"
        item = {
            "id": rec.id,
            "stage": rec.stage,
            "category": rec.category,
            "score": rec.confidence_score,
            "diagnosis_id": rec.diagnosis_id,
            "child": rec.child,
            "kategori": kategori,
            "klinis": klinis,
            "icd10_code": getattr(rec.diagnosis, "icd10_code", "-") if rec.diagnosis else "-",
            "description": "-",
        }
        data.append(item)

    return data

def ai_recommendation_detail(
    db: Session,
    claim_id: int,
    rec_type: str,
    item_id: int
) -> dict:
    """
    Kembalikan payload detail untuk modal FE:
    - rec_type in ["diagnosis","komorbid","komplikasi"]: resolve via ClaimAIRecommendation → ClaimDiagnosis
    - rec_type == "procedure": langsung ClaimProcedure + ClaimProcedureDetail
    """
    if rec_type in ["diagnosis", "komorbid", "komplikasi"]:
        rec = db.query(models.ClaimAIRecommendation).filter_by(
            id=item_id, claim_id=claim_id, category=rec_type
        ).first()
        if not rec or not rec.diagnosis_id:
            return {"status": "error", "msg": "Recommendation/Diagnosis not found"}

        diag = db.query(models.ClaimDiagnosis).filter_by(
            id=rec.diagnosis_id, claim_id=claim_id
        ).first()
        if not diag:
            return {"status": "error", "msg": "Diagnosis not found"}

        # seed default ke field diagnosis bila kosong (pakai dummy modal)
        modal_data = make_dummy("A41.9")["modal"]

        diag.icd10_code = diag.icd10_code or modal_data["icd10"]["kode_icd"]
        diag.struktur_icd10 = diag.struktur_icd10 or modal_data["icd10"]["struktur_icd10"]
        diag.kode_ganda = diag.kode_ganda or modal_data["icd10"]["kode_ganda"]
        diag.z_code = diag.z_code or modal_data["icd10"]["z_code"]
        diag.kode_bpjs_khusus = diag.kode_bpjs_khusus or modal_data["icd10"]["kode_bpjs_khusus"]

        diag.justifikasi = diag.justifikasi or modal_data["klinis"]["justifikasi"]
        diag.bukti_klinis = diag.bukti_klinis or modal_data["klinis"]["bukti_klinis"]
        diag.syarat_klinis = diag.syarat_klinis or modal_data["klinis"]["syarat_klinis"]

        diag.indikasi = diag.indikasi or modal_data["rawat_inap"]["indikasi"]
        diag.lama_rawat = diag.lama_rawat or modal_data["rawat_inap"]["lama_rawat"]
        diag.perpanjangan = diag.perpanjangan or modal_data["rawat_inap"]["perpanjangan"]

        diag.kesesuaian_rs = diag.kesesuaian_rs or modal_data["faskes"]["kesesuaian_rs"]
        diag.syarat = diag.syarat or modal_data["rujukan"]["syarat"]
        diag.kelayakan = diag.kelayakan or modal_data["rujukan"]["kelayakan"]

        diag.updated_at = datetime.utcnow()
        db.add(diag)
        db.commit()

        tindakan = db.query(models.ClaimProcedure).filter_by(claim_id=claim_id).all()
        tindakan_list = [{"id": p.id, "tindakan": p.procedure_text} for p in tindakan]

        return {
            "status": "ok",
            "data": {
                "id": diag.id,
                "kategori": diag.diagnosis_text,
                "klinis": {
                    "justifikasi": diag.justifikasi,
                    "bukti_klinis": diag.bukti_klinis,
                    "syarat_klinis": diag.syarat_klinis
                },
                "icd10": {
                    "kode_icd": diag.icd10_code,
                    "struktur_icd10": diag.struktur_icd10,
                    "kode_ganda": diag.kode_ganda,
                    "z_code": diag.z_code,
                    "kode_bpjs_khusus": diag.kode_bpjs_khusus
                },
                "tindakan": tindakan_list,
                "rawat_inap": {
                    "indikasi": diag.indikasi,
                    "lama_rawat": diag.lama_rawat,
                    "perpanjangan": diag.perpanjangan
                },
                "faskes": {"kesesuaian_rs": diag.kesesuaian_rs},
                "rujukan": {"syarat": diag.syarat, "kelayakan": diag.kelayakan}
            }
        }

    elif rec_type == "procedure":
        proc = db.query(models.ClaimProcedure)\
            .options(joinedload(models.ClaimProcedure.procedure_details))\
            .filter_by(id=item_id, claim_id=claim_id).first()
        if not proc:
            return {"status": "error", "msg": "Procedure not found"}

        details = []
        for d in proc.procedure_details:
            if d.is_deleted:
                continue
            des = " | ".join(filter(None, [d.icd9_tindakan, d.ina_cbg_tindakan, d.status_tindakan]))
            details.append({
                "icd9": d.icd9_tindakan,
                "deskripsi": des or "-",
                "validitas": d.validitas_tindakan,
                "status": d.status_tindakan,
                "ina_cbg": d.ina_cbg_tindakan,
                "faskes": d.faskes_tindakan,
                "rawat_inap": d.rawat_inap_tindakan,
                "syarat_klinis": d.syarat_klinis_tindakan
            })
        description = "; ".join([d["deskripsi"] for d in details]) if details else "-"
        return {"status": "ok", "data": {
            "id": proc.id,
            "procedure_text": proc.procedure_text,
            "description": description,
            "tindakan": details
        }}

    return {"status": "error", "msg": f"Tipe {rec_type} tidak dikenali"}

# ==================================================
# AI SUMMARY / EVALUASI
# ==================================================

def store_ai_evaluations(db: Session, claim_id: int, evaluasi: dict):
    """Simpan hasil evaluasi kombinasi ke tabel evaluasi klaim."""
    db.query(models.ClaimRegulationDetail).filter_by(claim_id=claim_id).delete()
    db.query(models.ClaimDiagnosisEvaluation).filter_by(claim_id=claim_id).delete()
    db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=claim_id).delete()
    db.query(models.ClaimCombinationAlternative).filter_by(claim_id=claim_id).delete()
    db.commit()

    def parse_validitas(raw: str):
        if not raw:
            return None
        raw_lower = raw.lower()
        if "invalid" in raw_lower:
            return "invalid"
        if "warning" in raw_lower or "medium" in raw_lower:
            return "warning"
        if "valid" in raw_lower:
            return "valid"
        return None

    # Kombinasi Diagnosis
    diag_eval = models.ClaimDiagnosisEvaluation(
        claim_id=claim_id,
        validitas=parse_validitas(evaluasi["kombinasi_diagnosis"].get("validitas")),
        validitas_detail=evaluasi["kombinasi_diagnosis"].get("validitas_detail"),
        severity=evaluasi["kombinasi_diagnosis"].get("severity"),
        kode_ina_cbg=evaluasi["kombinasi_diagnosis"].get("kode_ina_cbg"),
        estimasi_tarif=parse_number(evaluasi["kombinasi_diagnosis"].get("estimasi_tarif")),
        syarat_klinis=evaluasi["kombinasi_diagnosis"].get("syarat_klinis"),
        evaluasi_faskes=evaluasi["kombinasi_diagnosis"].get("evaluasi_faskes"),
        rawat_inap=evaluasi["kombinasi_diagnosis"].get("rawat_inap"),
        is_dummy=True,
        is_deleted=False,
        created_at=datetime.utcnow(),
    )
    db.add(diag_eval)
    db.flush()

    reg = models.ClaimRegulationDetail(
        claim_id=claim_id,
        diagnosis_evaluation_id=diag_eval.id,
        judul_regulasi="PNPK Evaluasi Diagnosis 2020",
        dasar_hukum="PNPK",
        bab_pasal="Bab IV Pasal 8",
        isi="Evaluasi kombinasi diagnosis harus berdasarkan kriteria klinis",
        is_dummy=True,
        is_deleted=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(reg)

    # Kombinasi Tindakan
    for td in evaluasi.get("kombinasi_tindakan", []):
        proc_eval = models.ClaimProcedureEvaluation(
            claim_id=claim_id,
            validitas=parse_validitas(td.get("validitas")),
            validitas_detail=td.get("validitas_detail"),
            status_tindakan=td.get("status"),
            tarif_impact=parse_number(td.get("tarif_impact")),
            faskes=td.get("faskes"),
            rawat_inap=td.get("rawat_inap"),
            syarat_klinis=td.get("syarat_klinis"),
            is_dummy=True,
            is_deleted=False,
            created_at=datetime.utcnow(),
        )
        db.add(proc_eval)
        db.flush()

        reg = models.ClaimRegulationDetail(
            claim_id=claim_id,
            procedure_evaluation_id=proc_eval.id,
            judul_regulasi="PNPK Evaluasi Tindakan 2020",
            dasar_hukum="PNPK",
            bab_pasal="Bab V Pasal 12",
            isi=f"Evaluasi regulasi terkait tindakan {proc_eval.status_tindakan or '-'}",
            is_dummy=True,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(reg)

    # Alternatif Kombinasi
    severity_default = evaluasi["kombinasi_diagnosis"].get("severity")
    for alt in evaluasi["alternatif"][:2]:
        comb = models.ClaimCombinationAlternative(
            claim_id=claim_id,
            kombinasi_nama=alt.get("kombinasi"),
            severity=severity_default,
            kode_ina_cbg=alt.get("kode_ina_cbg"),
            estimasi_tarif=parse_number(alt.get("tarif")),
            syarat_klinis=alt.get("syarat_klinis"),
            faskes=alt.get("faskes"),
            rawat_inap=alt.get("rawat_inap"),
            tindakan_wajib=alt.get("tindakan_wajib"),
            is_dummy=True,
            is_deleted=False,
            created_at=datetime.utcnow(),
        )
        db.add(comb)

    db.commit()

def ai_summary_service(db: Session, claim_id: int, payload: dict):
    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        return {"error": "Claim not found"}

    # ambil simulasi
    simulasi = payload.get("simulasi", {})

    # buat evaluasi dummy
    evaluasi = make_dummy("summary")["evaluasi"]
    store_ai_evaluations(db, claim_id, evaluasi)

    # ambil hasil simpan
    diag = db.query(models.ClaimDiagnosisEvaluation).filter_by(claim_id=claim_id).first()
    procs = db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=claim_id).all()
    alts = db.query(models.ClaimCombinationAlternative).filter_by(claim_id=claim_id).limit(2).all()

    return {
        "diagnosis": {
            "id": diag.id if diag else "-",
            "validitas": diag.validitas if diag else "-",
            "validitas_detail": diag.validitas_detail if diag else "-",
            "severity": diag.severity if diag else "-",
            "kode_ina_cbg": diag.kode_ina_cbg if diag else "-",
            "estimasi_tarif": diag.estimasi_tarif if diag else "-",
            "syarat": diag.syarat_klinis if diag else "-",
            "evaluasi_faskes": diag.evaluasi_faskes if diag else "-",
            "rawat_inap": diag.rawat_inap if diag else "-"
        },
        "procedure": [
            {
                "id": p.id,
                "validitas": p.validitas or "-",
                "validitas_detail": p.validitas_detail or "-",
                "tindakan": p.validitas_detail or p.status_tindakan or "-",
                "status_tindakan": p.status_tindakan or "-",
                "tarif_impact": f"Rp {int(p.tarif_impact):,}" if p.tarif_impact else "-",
                "faskes": p.faskes or "-",
                "rawat_inap": p.rawat_inap or "-",
                "syarat_klinis": p.syarat_klinis or "-"
            }
            for p in procs
        ],
        "alternatif": [
            {
                "nama": a.kombinasi_nama,
                "severity_detail": diag.severity if not a.severity else a.severity,
                "ina_cbg": a.kode_ina_cbg,
                "tarif": a.estimasi_tarif,
                "syarat": a.syarat_klinis,
                "faskes": a.faskes,
                "rawat_inap": a.rawat_inap,
                "tindakan_wajib": a.tindakan_wajib
            }
            for a in alts
        ],
        "alternatif_count": len(alts)
    }

# ==================================================
# Regulation Service Functions - Claim Regulasi Detail
# ==================================================
def get_regulations_payload(
    db: Session,
    claim_id: int,
    diagnosis_id: int | None = None,
    procedure_id: int | None = None,
    diagnosis_evaluation_id: int | None = None,
    procedure_evaluation_id: int | None = None,
) -> dict:
    q = db.query(models.ClaimRegulationDetail).filter_by(
        claim_id=claim_id, is_deleted=False
    )
    if diagnosis_id:
        q = q.filter(models.ClaimRegulationDetail.diagnosis_id == diagnosis_id)
    elif procedure_id:
        q = q.filter(models.ClaimRegulationDetail.procedure_id == procedure_id)
    elif diagnosis_evaluation_id:
        q = q.filter(models.ClaimRegulationDetail.diagnosis_evaluation_id == diagnosis_evaluation_id)
    elif procedure_evaluation_id:
        q = q.filter(models.ClaimRegulationDetail.procedure_evaluation_id == procedure_evaluation_id)

    regs = q.all()
    return {
        "status": "ok",
        "data": [
            {
                "id": r.id,
                "judul_regulasi": r.judul_regulasi,
                "dasar_hukum": r.dasar_hukum,
                "bab_pasal": r.bab_pasal,
                "isi": r.isi,
            } for r in regs
        ]
    }
