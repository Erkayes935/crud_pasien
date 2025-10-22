from datetime import datetime
from sqlalchemy.orm import Session
from ... import models
from .ai import store_ai_recommendations, store_ai_evaluations


# ==========================================================
# 🧩 HELPER 1: Simpan Diagnosis & Tindakan dasar
# ==========================================================
def _save_base_data(db: Session, claim_id: int, stage: str, stage_data: dict):
    """
    Simpan data diagnosis & tindakan hasil mapping dokter ke DB.
    Tidak menghapus data lama, hanya tambah yang baru untuk simulasi aktif.
    """
    primary_diagnosis, secondary_diagnoses = None, []
    primary_procedure, secondary_procedures = None, []

    # === Diagnosis Section ===
    for category in ["diagnosis", "komorbid", "komplikasi"]:
        for item in stage_data.get(category, []):
            mapping = (item.get("mapping") or "").lower()
            diag_name = item.get("name") or item.get("kategori") or item.get("nama_kategori")

            diag = models.ClaimDiagnosis(
                claim_id=claim_id,
                diagnosis_type=category,
                diagnosis_text=diag_name,
                icd10_code=item.get("icd10_code") or item.get("icd"),
                diagnosis_source="doctor",
                justifikasi_klinis=item.get("klinis"),
                is_deleted=False,
                is_dummy=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(diag)
            db.flush()

            if "utama" in mapping or "primary" in mapping:
                primary_diagnosis = diag.id
                print(f"[SAVE_SIMULASI] ✅ Primary diagnosis: {diag_name} (ID {diag.id})")
            else:
                secondary_diagnoses.append(diag.id)
                print(f"[SAVE_SIMULASI] ➕ Secondary diagnosis: {diag_name} (ID {diag.id})")

    # === Procedure Section ===
    for item in stage_data.get("tindakan", []):
        mapping = (item.get("mapping") or "").lower()
        proc_name = item.get("name") or item.get("kategori") or item.get("nama_kategori")
        source = item.get("source") or item.get("procedure_source") or "manual"
        if source not in ["ai", "manual", "doctor"]:
            source = "manual"  # fallback aman

        proc = models.ClaimProcedure(
            claim_id=claim_id,
            procedure_text=proc_name,
            procedure_source=source,
            stage=stage,
            requirement_flag=False,
            is_deleted=False,
            is_dummy=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(proc)
        db.flush()

        if item.get("icd9_code") or item.get("icd"):
            db.add(models.ClaimProcedureDetail(
                procedure_id=proc.id,
                icd9_tindakan=item.get("icd9_code") or item.get("icd"),
                nama_tindakan=proc_name,
                is_deleted=False,
                created_at=datetime.utcnow()
            ))

        if "utama" in mapping or "primary" in mapping:
            primary_procedure = proc.id
            print(f"[SAVE_SIMULASI] ✅ Primary procedure: {proc_name} (ID {proc.id})")
        else:
            secondary_procedures.append(proc.id)
            print(f"[SAVE_SIMULASI] ➕ Secondary procedure: {proc_name} (ID {proc.id})")

    db.commit()
    return {
        "primary_diagnosis": primary_diagnosis,
        "secondary_diagnoses": secondary_diagnoses,
        "primary_procedure": primary_procedure,
        "secondary_procedures": secondary_procedures,
    }


# ==========================================================
# 🧩 HELPER 2: Simpan relasi ClaimSimulation
# ==========================================================
def _save_simulation_mapping(db: Session, claim_id: int, stage: str, mapping: dict):
    """Buat relasi utama–sekunder di ClaimSimulation."""
    db.query(models.ClaimSimulation).filter(
        models.ClaimSimulation.claim_id == claim_id,
        models.ClaimSimulation.stage == stage,
        models.ClaimSimulation.is_deleted == False,
    ).update({"is_deleted": True})

    main_sim = models.ClaimSimulation(
        claim_id=claim_id,
        stage=stage,
        diagnosis_utama_id=mapping["primary_diagnosis"],
        diagnosis_sekunder_id=(mapping["secondary_diagnoses"] or [None])[0],
        tindakan_utama_id=mapping["primary_procedure"],
        tindakan_sekunder_id=(mapping["secondary_procedures"] or [None])[0],
        is_deleted=False,
        is_dummy=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(main_sim)

    # Tambah simulasi tambahan untuk secondary procedure
    for sec_id in mapping["secondary_procedures"][1:]:
        db.add(models.ClaimSimulation(
            claim_id=claim_id,
            stage=stage,
            diagnosis_utama_id=None,
            diagnosis_sekunder_id=None,
            tindakan_utama_id=None,
            tindakan_sekunder_id=sec_id,
            is_deleted=False,
            is_dummy=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))

    db.commit()
    print(f"[SAVE_SIMULASI] 🧩 Saved simulation mapping for {stage}")


# ==========================================================
# 🧩 HELPER 3: Simpan hasil i-DRG ke IDRGDiagnosis
# ==========================================================
def _store_idrg_results(db: Session, claim_id: int, idrg_data: dict):
    """Simpan hasil analisis i-DRG ke tabel IDRGDiagnosis (mirroring claim_router.py)."""
    if not idrg_data:
        return

    data = idrg_data.get("data", idrg_data)
    try:
        entry = models.ClaimIDRGDiagnosis(
            claim_id=claim_id,
            diagnosis_id=data.get("diagnosis_id"),
            group_idrg=data.get("group_idrg"),
            severity_index=data.get("severity_index"),
            checklist_dokumentasi="; ".join(data.get("checklist_dokumentasi", [])),
            faktor_penentu_severity="; ".join(data.get("faktor_penentu_severity", [])),
            ungroupable_alert=data.get("ungroupable_alert"),
            estimasi_tarif=data.get("estimasi_tarif"),
            gap_analysis=data.get("gap_analysis"),
            notification_status=(data.get("notification") or {}).get("status"),
            notification_message=(data.get("notification") or {}).get("message"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )
        db.add(entry)
        db.commit()
        print(f"[SAVE_SIMULASI] 💰 Saved i-DRG: {entry.group_idrg} (Severity {entry.severity_index})")
    except Exception as e:
        db.rollback()
        print(f"[SAVE_SIMULASI] ❌ Error saving i-DRG: {e}")


# ==========================================================
# 🧩 HELPER 4: Integrasikan semua modal tambahan
# ==========================================================
def _save_modal_data(db: Session, claim_id: int, form_data: dict):
    """Integrasikan modal klinis, tindakan, regulasi, evaluasi, dan i-DRG."""
    if not form_data:
        return

    print(f"[SAVE_SIMULASI] 🔄 Integrating modal data for claim {claim_id}")

    # 🩺 Diagnosis detail (klinis, faskes, rujukan, tarif, dsb.)
    for diag in form_data.get("diagnosis_modal", []):
        store_ai_recommendations(db, claim_id, diag, mode="diagnosis")

    # ⚙️ Tindakan detail
    for proc in form_data.get("procedure_modal", []):
        store_ai_recommendations(db, claim_id, proc, mode="procedure")

    # 📚 Regulasi per field
    for reg in form_data.get("regulation_modal", []):
        store_ai_recommendations(db, claim_id, reg, mode="regulation")

    # 📊 Evaluasi kombinasi
    if "evaluation_modal" in form_data:
        store_ai_evaluations(db, claim_id, form_data["evaluation_modal"])

    # 🧾 i-DRG Result
    if "idrg_modal" in form_data:
        _store_idrg_results(db, claim_id, form_data["idrg_modal"])

    print(f"[SAVE_SIMULASI] ✅ Completed modal integration for claim {claim_id}")


# ==========================================================
# 🧩 FUNGSI UTAMA
# ==========================================================
def save_simulasi(db: Session, claim_id: int, sim_data: dict, form_data: dict = None):
    """
    Fungsi utama penyimpanan hasil simulasi dokter ke DB.
    Aman, modular, dan sesuai dengan struktur claim_router.py & ai.py.
    """
    print(f"[SAVE_SIMULASI] 🚀 Start saving simulation for claim {claim_id}")

    for stage, stage_data in (sim_data or {}).items():
        if not isinstance(stage_data, dict):
            continue

        print(f"[SAVE_SIMULASI] ▶ Stage: {stage}")
        mapping = _save_base_data(db, claim_id, stage, stage_data)
        _save_simulation_mapping(db, claim_id, stage, mapping)

    _save_modal_data(db, claim_id, form_data)

    print(f"[SAVE_SIMULASI] ✅ Successfully saved doctor mapping for claim {claim_id}")
