from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from ... import models
from .helper import parse_number, _update_or_create_procedure, _update_diag_fields

# =========================
# Simulasi + Evaluasi
# =========================

def load_sim_and_summary_service(db: Session, claim_id: int, include_summary: bool = True):
    """Ambil ulang simulasi + evaluasi dari tabel pecahan"""
    sim, summ = {}, {}

    sims = db.query(models.ClaimSimulation).filter_by(claim_id=claim_id).all()
    for s in sims:
        if s.stage not in sim:
            sim[s.stage] = {
                "utama_diagnosis": None,
                "utama_tindakan": None,
                "sekunder_diagnosis": [],
                "sekunder_tindakan": []
            }
        if s.diagnosis_utama_id:
            sim[s.stage]["utama_diagnosis"] = {"id": s.diagnosis_utama_id, "type": "diagnosis"}
        if s.tindakan_utama_id:
            sim[s.stage]["utama_tindakan"] = {"id": s.tindakan_utama_id, "type": "tindakan"}
        if s.diagnosis_sekunder_id:
            sim[s.stage]["sekunder_diagnosis"].append({"id": s.diagnosis_sekunder_id, "type": "diagnosis"})
        if s.tindakan_sekunder_id:
            sim[s.stage]["sekunder_tindakan"].append({"id": s.tindakan_sekunder_id, "type": "tindakan"})

    if include_summary:
        summ["diagnosis"] = [
            {
                "validitas": d.validitas,
                "severity": d.severity,
                "kode_ina_cbg": d.kode_ina_cbg,
                "estimasi_tarif": float(d.estimasi_tarif) if d.estimasi_tarif else None,
                "syarat_klinis": d.syarat_klinis,
                "evaluasi_faskes": d.evaluasi_faskes,
                "rawat_inap": d.rawat_inap,
            }
            for d in db.query(models.ClaimDiagnosisEvaluation).filter_by(claim_id=claim_id).all()
        ]
        summ["procedure"] = [
            {
                "validitas": p.validitas,
                "status_tindakan": p.status_tindakan,
                "tarif_impact": float(p.tarif_impact) if p.tarif_impact else None,
                "faskes": p.faskes,
                "rawat_inap": p.rawat_inap,
                "syarat_klinis": p.syarat_klinis,
            }
            for p in db.query(models.ClaimProcedureEvaluation).filter_by(claim_id=claim_id).all()
        ]
        summ["alternatif"] = [
            {
                "kombinasi_nama": a.kombinasi_nama,
                "severity": a.severity,
                "kode_ina_cbg": a.kode_ina_cbg,
                "estimasi_tarif": float(a.estimasi_tarif) if a.estimasi_tarif else None,
                "syarat_klinis": a.syarat_klinis,
                "faskes": a.faskes,
                "rawat_inap": a.rawat_inap,
                "tindakan_wajib": a.tindakan_wajib,
            }
            for a in db.query(models.ClaimCombinationAlternative).filter_by(claim_id=claim_id).all()
        ]
    return sim, summ

def save_simulation_and_summary(db: Session, claim_id: int, sim_data: dict, summ_data: dict):
    """Simpan ulang simulasi (utama/sekunder) + evaluasi kombinasi ke tabel pecahan (pakai helper + regulasi)."""

    claim = db.query(models.Claim).get(claim_id)
    if not claim:
        return

    # 🔹 Bersihkan dulu data dummy supaya FK gak nyangkut
    db.query(models.ClaimRegulationDetail).filter_by(claim_id=claim_id, is_dummy=True).delete()
    db.query(models.ClaimSimulation).filter(models.ClaimSimulation.claim_id == claim_id).delete()
    db.query(models.ClaimDiagnosisEvaluation).filter(models.ClaimDiagnosisEvaluation.claim_id == claim_id).delete()
    db.query(models.ClaimProcedureEvaluation).filter(models.ClaimProcedureEvaluation.claim_id == claim_id).delete()
    db.query(models.ClaimCombinationAlternative).filter(models.ClaimCombinationAlternative.claim_id == claim_id).delete()
    db.flush()

    # 🔹 Simpan ulang ClaimSimulation
    for stage, arr in (sim_data or {}).items():
        if not isinstance(arr, dict):
            continue

        # Diagnosis utama
        utama_diag_id = None
        if arr.get("utama"):
            utama_item = arr["utama"]
            name = utama_item.get("name") or utama_item.get("diagnosis_text")
            if name:
                diag = db.query(models.ClaimDiagnosis).filter_by(
                    claim_id=claim_id, diagnosis_text=name
                ).first()
                if diag:
                    utama_diag_id = diag.id
                    db.add(models.ClaimRegulationDetail(
                        claim_id=claim_id,
                        diagnosis_id=utama_diag_id,
                        judul_regulasi="Regulasi default diagnosis utama",
                        dasar_hukum="PNPK",
                        bab_pasal="Bab II Pasal 5",
                        isi=f"Regulasi terkait diagnosis utama {name}",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        is_deleted=False,
                        is_dummy=True
                    ))

        # Diagnosis sekunder
        sek_diag_id = None
        if arr.get("sekunder"):
            sek_item = arr["sekunder"][0] if isinstance(arr["sekunder"], list) and arr["sekunder"] else None
            if sek_item:
                name = sek_item.get("name") or sek_item.get("diagnosis_text")
                if name:
                    diag = db.query(models.ClaimDiagnosis).filter_by(
                        claim_id=claim_id, diagnosis_text=name
                    ).first()
                    if diag:
                        sek_diag_id = diag.id
                        db.add(models.ClaimRegulationDetail(
                            claim_id=claim_id,
                            diagnosis_id=sek_diag_id,
                            judul_regulasi="Regulasi default diagnosis sekunder",
                            dasar_hukum="PNPK",
                            bab_pasal="Bab III Pasal 7",
                            isi=f"Regulasi terkait diagnosis sekunder {name}",
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                            is_deleted=False,
                            is_dummy=True
                        ))

        # Buat simulasi kosong dulu
        sim = models.ClaimSimulation(
            claim_id=claim_id,
            stage=stage,
            diagnosis_utama_id=utama_diag_id,
            diagnosis_sekunder_id=sek_diag_id,
            is_dummy=False,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(sim)
        db.flush()  # ✅ supaya sim.id terisi

        # Tindakan utama
        if arr.get("tindakanUtama"):
            sim.tindakan_utama_id = _update_or_create_procedure(
                db, claim, arr["tindakanUtama"], "utama", sim.id
            )
            # Tambahkan regulasi default utk tindakan utama
            db.add(models.ClaimRegulationDetail(
                claim_id=claim_id,
                procedure_id=sim.tindakan_utama_id,
                judul_regulasi="Regulasi default tindakan utama",
                dasar_hukum="PNPK",
                bab_pasal="Bab X",
                isi="Regulasi terkait tindakan utama",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
                is_dummy=True
            ))

        # Tindakan sekunder
        if arr.get("tindakanSekunder"):
            sek_item = arr["tindakanSekunder"][0] if isinstance(arr["tindakanSekunder"], list) else arr["tindakanSekunder"]
            sim.tindakan_sekunder_id = _update_or_create_procedure(
                db, claim, sek_item, "sekunder", sim.id
            )
            # Tambahkan regulasi default utk tindakan sekunder
            db.add(models.ClaimRegulationDetail(
                claim_id=claim_id,
                procedure_id=sim.tindakan_sekunder_id,
                judul_regulasi="Regulasi default tindakan sekunder",
                dasar_hukum="PNPK",
                bab_pasal="Bab Y",
                isi="Regulasi terkait tindakan sekunder",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
                is_dummy=True
            ))

        db.flush()  # ✅ update sim setelah id tindakan terisi

    # 🔹 Simpan Evaluasi (summary)
    if summ_data:
        # === Kombinasi Diagnosis ===
        diag_name = summ_data.get("kombinasi_diagnosis", {}).get("name") \
                 or summ_data.get("kombinasi_diagnosis", {}).get("diagnosis_text")
        diag = db.query(models.ClaimDiagnosis).filter_by(
            claim_id=claim_id, diagnosis_text=diag_name
        ).first() if diag_name else None

        diag_eval = models.ClaimDiagnosisEvaluation(
            claim_id=claim_id,
            validitas=summ_data.get("kombinasi_diagnosis", {}).get("validitas"),
            severity=summ_data.get("kombinasi_diagnosis", {}).get("severity"),
            validitas_detail=summ_data.get("kombinasi_diagnosis", {}).get("validitas_detail"),
            kode_ina_cbg=summ_data.get("kombinasi_diagnosis", {}).get("kode_ina_cbg"),
            estimasi_tarif=parse_number(summ_data.get("kombinasi_diagnosis", {}).get("estimasi_tarif")),
            syarat_klinis=summ_data.get("kombinasi_diagnosis", {}).get("syarat_klinis"),
            evaluasi_faskes=summ_data.get("kombinasi_diagnosis", {}).get("evaluasi_faskes"),
            rawat_inap=summ_data.get("kombinasi_diagnosis", {}).get("rawat_inap"),
            created_at=datetime.utcnow(),
            is_deleted=False,
            is_dummy=True
        )
        db.add(diag_eval)
        db.flush()

        db.add(models.ClaimRegulationDetail(
            claim_id=claim_id,
            diagnosis_evaluation_id=diag_eval.id,
            judul_regulasi="PNPK Evaluasi Diagnosis 2020",
            dasar_hukum="PNPK",
            bab_pasal="Bab IV Pasal 8",
            isi="Evaluasi kombinasi diagnosis harus berdasarkan kriteria klinis",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
            is_dummy=True
        ))

        # === Kombinasi Tindakan ===
        for v in summ_data.get("procedure", []):
            proc_id = None
            name = v.get("tindakan") or v.get("name") or v.get("procedure_text")
            if name:
                proc = db.query(models.ClaimProcedure).filter_by(claim_id=claim_id, procedure_text=name).first()
                proc_id = proc.id if proc else None

            proc_eval = models.ClaimProcedureEvaluation(
                claim_id=claim_id,
                validitas=v.get("validitas"),
                validitas_detail=v.get("validitas_detail"),
                status_tindakan=v.get("status_tindakan"),
                tarif_impact=parse_number(v.get("tarif_impact")),
                faskes=v.get("faskes"),
                rawat_inap=v.get("rawat_inap"),
                syarat_klinis=v.get("syarat_klinis"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
                is_dummy=True
            )
            db.add(proc_eval)
            db.flush()

            db.add(models.ClaimRegulationDetail(
                claim_id=claim_id,
                procedure_evaluation_id=proc_eval.id,
                judul_regulasi="PNPK Evaluasi Tindakan 2020",
                dasar_hukum="PNPK",
                bab_pasal="Bab V Pasal 12",
                isi=f"Evaluasi regulasi terkait tindakan {proc_eval.status_tindakan or '-'}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
                is_dummy=True
            ))

        # === Alternatif Kombinasi ===
        for alt in summ_data.get("alternatif", []):
            db.add(models.ClaimCombinationAlternative(
                claim_id=claim_id,
                kombinasi_nama=alt.get("kombinasi"),
                severity=alt.get("severity"),
                kode_ina_cbg=alt.get("kode_ina_cbg"),
                estimasi_tarif=parse_number(alt.get("tarif")),
                syarat_klinis=alt.get("syarat_klinis"),
                faskes=alt.get("faskes"),
                rawat_inap=alt.get("rawat_inap"),
                tindakan_wajib=alt.get("tindakan_wajib"),
                created_at=datetime.utcnow(),
                is_deleted=False,
                is_dummy=True
            ))

    db.commit()

def get_simulations_service(db: Session, claim_id: int):
    sims = db.query(models.ClaimSimulation).options(
        joinedload(models.ClaimSimulation.diagnosis_utama),
        joinedload(models.ClaimSimulation.diagnosis_sekunder),
        joinedload(models.ClaimSimulation.tindakan_utama),
        joinedload(models.ClaimSimulation.tindakan_sekunder)
    ).filter_by(claim_id=claim_id).all()

    return {
        "status": "ok",
        "data": [
            {
                "stage": s.stage,
                "diagnosis_utama_id": s.diagnosis_utama_id,
                "diagnosis_utama_name": s.diagnosis_utama.diagnosis_text if s.diagnosis_utama else None,
                "diagnosis_sekunder_id": s.diagnosis_sekunder_id,
                "diagnosis_sekunder_name": s.diagnosis_sekunder.diagnosis_text if s.diagnosis_sekunder else None,
                "tindakan_utama_id": s.tindakan_utama_id,
                "tindakan_utama_name": s.tindakan_utama.procedure_text if s.tindakan_utama else None,
                "tindakan_sekunder_id": s.tindakan_sekunder_id,
                "tindakan_sekunder_name": s.tindakan_sekunder.procedure_text if s.tindakan_sekunder else None,
            }
            for s in sims
        ]
    }


