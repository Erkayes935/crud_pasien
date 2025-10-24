from datetime import datetime
from sqlalchemy.orm import Session
from ... import models
from .ai import store_ai_recommendations, store_ai_evaluations


# ==========================================================
# 🧩 HELPER 1: Simpan Diagnosis & Tindakan (dynamic source)
# ==========================================================
def _save_base_data(db: Session, claim_id: int, stage: str, stage_data: dict):
    """
    Simpan diagnosis & tindakan hasil mapping dokter ke DB.
    - Tidak mengubah procedure_source.
    - Tidak bikin duplikat AI vs manual.
    - Menangani ICD9 list agar tidak campur antar tindakan.
    """
    primary_diagnosis, secondary_diagnoses = None, []
    primary_procedure, secondary_procedures = None, []

    # === Diagnosis ===
    for category in ["diagnosis", "komorbid", "komplikasi"]:
        for item in stage_data.get(category, []):
            diag_name = (
                item.get("name")
                or item.get("kategori")
                or item.get("nama_kategori")
                or "-"
            )
            mapping = (item.get("mapping") or "").lower()
            source = (item.get("source") or "manual").lower()

            existing = (
                db.query(models.ClaimDiagnosis)
                .filter(
                    models.ClaimDiagnosis.claim_id == claim_id,
                    models.ClaimDiagnosis.diagnosis_text == diag_name,
                    models.ClaimDiagnosis.is_deleted == False,
                )
                .first()
            )

            if existing:
                diag = existing
                print(f"[SAVE_SIMULASI] ⚠️ Skip duplicate diagnosis: {diag_name}")
            else:
                diag = models.ClaimDiagnosis(
                    claim_id=claim_id,
                    diagnosis_type=category,
                    diagnosis_text=diag_name,
                    icd10_code=item.get("icd10_code") or item.get("icd"),
                    diagnosis_source=source,
                    justifikasi_klinis=item.get("klinis"),
                    is_deleted=False,
                    is_dummy=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(diag)
                db.flush()
                print(f"[SAVE_SIMULASI] ➕ Added diagnosis: {diag_name} ({source})")

            if "utama" in mapping or "primary" in mapping:
                primary_diagnosis = diag.id
            else:
                secondary_diagnoses.append(diag.id)

    # === Procedure ===
    for item in stage_data.get("tindakan", []):
        proc_name = (
            item.get("name")
            or item.get("kategori")
            or item.get("nama_kategori")
            or "-"
        )
        mapping = (item.get("mapping") or "").lower()
        source = (item.get("source") or "manual").lower()

        # Pecah semua ICD9 jadi list
        raw_icd9 = item.get("icd9_code") or item.get("icd")
        if isinstance(raw_icd9, str):
            codes = [x.strip() for x in raw_icd9.split(",") if x.strip()]
        elif isinstance(raw_icd9, list):
            codes = [x.strip() for x in raw_icd9 if isinstance(x, str)]
        else:
            codes = []

        # Ambil satu kode berdasar urutan tindakan (index dinamis)
        index = stage_data.get("tindakan", []).index(item) if item in stage_data.get("tindakan", []) else 0
        icd9_val = codes[index] if index < len(codes) else (codes[0] if codes else None)

        # Cari existing berdasarkan nama tindakan aja (tanpa lihat source)
        existing_proc = (
            db.query(models.ClaimProcedure)
            .filter(
                models.ClaimProcedure.claim_id == claim_id,
                models.ClaimProcedure.procedure_text == proc_name,
                models.ClaimProcedure.is_deleted == False,
            )
            .first()
        )

        if existing_proc:
            # Jangan ubah apa-apa, cukup pakai ulang
            print(f"[SAVE_SIMULASI] ⚠️ Existing procedure reused: {proc_name} ({existing_proc.procedure_source})")
            proc = existing_proc
        else:
            proc = models.ClaimProcedure(
                claim_id=claim_id,
                procedure_text=proc_name,
                procedure_source=source,
                icd9_code=icd9_val,
                stage=stage,
                requirement_flag=False,
                is_deleted=False,
                is_dummy=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(proc)
            db.flush()
            print(f"[SAVE_SIMULASI] ➕ Added procedure: {proc_name} ({source})")

            if icd9_val:
                db.add(
                    models.ClaimProcedureDetail(
                        procedure_id=proc.id,
                        icd9_tindakan=icd9_val,
                        deskripsi_tindakan=f"ICD-9: {icd9_val}, Status: {item.get('status_tindakan') or 'Wajib (Manual)'}, INA-CBG: {item.get('ina_cbg_tindakan') or '-'}",
                        validitas_tindakan=item.get("validitas") or "VALID (Manual)",
                        status_tindakan=item.get("status_tindakan") or "Wajib (Manual)",
                        ina_cbg_tindakan=item.get("ina_cbg_tindakan"),
                        syarat_klinis_tindakan=item.get("syarat_klinis") or "-",
                        is_deleted=False,
                        created_at=datetime.utcnow(),
                    )
                )

        if "utama" in mapping or "primary" in mapping:
            primary_procedure = proc.id
        else:
            secondary_procedures.append(proc.id)

    # === Fallback kalau mapping kosong ===
    if not primary_diagnosis and secondary_diagnoses:
        primary_diagnosis = secondary_diagnoses[0]
    if not primary_procedure and secondary_procedures:
        primary_procedure = secondary_procedures[0]

    db.flush()
    return {
        "primary_diagnosis": primary_diagnosis,
        "secondary_diagnoses": secondary_diagnoses,
        "primary_procedure": primary_procedure,
        "secondary_procedures": secondary_procedures,
    }



# ==========================================================
# 🧩 HELPER 2: Buat ulang ClaimSimulation (bersih)
# ==========================================================
def _save_simulation_mapping(db: Session, claim_id: int, stage: str, refs: dict):
    """Bersihkan dan buat ulang ClaimSimulation agar mapping tetap fresh."""
    db.query(models.ClaimSimulation).filter(
        models.ClaimSimulation.claim_id == claim_id,
        models.ClaimSimulation.stage == stage
    ).delete(synchronize_session=False)

    db.commit()

    # ✅ Pastikan list aman, walau kosong atau None
    secondary_diags = refs.get("secondary_diagnoses") or [None]
    secondary_procs = refs.get("secondary_procedures") or [None]

    main_sim = models.ClaimSimulation(
        claim_id=claim_id,
        stage=stage,
        diagnosis_utama_id=refs.get("primary_diagnosis"),
        diagnosis_sekunder_id=secondary_diags[0],
        tindakan_utama_id=refs.get("primary_procedure"),
        tindakan_sekunder_id=secondary_procs[0],
        is_deleted=False,
        is_dummy=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        coder_verified=False,
        is_coder_approved=False,
    )
    db.add(main_sim)

    # secondary lainnya
    for diag_id in secondary_diags[1:]:
        if diag_id:
            db.add(models.ClaimSimulation(
                claim_id=claim_id,
                stage=stage,
                diagnosis_sekunder_id=diag_id,
                is_deleted=False,
                is_dummy=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                coder_verified=False,
                is_coder_approved=False,
            ))

    for proc_id in secondary_procs[1:]:
        if proc_id:
            db.add(models.ClaimSimulation(
                claim_id=claim_id,
                stage=stage,
                tindakan_sekunder_id=proc_id,
                is_deleted=False,
                is_dummy=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                coder_verified=False,
                is_coder_approved=False,
            ))

    db.commit()
    print(f"[SAVE_SIMULASI] ✅ Simulation mapping refreshed for claim {claim_id}")


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
    print(f"[SAVE_SIMULASI] 🚀 Start saving simulation for claim {claim_id}")
    if not sim_data:
        print("[SAVE_SIMULASI] ⚠️ No sim_data provided, skip")
        return

    for stage, stage_data in (sim_data or {}).items():
        # ✅ Skip stage kosong biar tidak error
        if not isinstance(stage_data, dict) or not stage_data:
            print(f"[SAVE_SIMULASI] ⏭️ Skip empty stage: {stage}")
            continue

        print(f"[SAVE_SIMULASI] ▶ Stage: {stage}")
        refs = _save_base_data(db, claim_id, stage, stage_data)
        _save_simulation_mapping(db, claim_id, stage, refs)

    if form_data:
        _save_modal_data(db, claim_id, form_data)

    print(f"[SAVE_SIMULASI] ✅ Successfully saved dynamic simulation for claim {claim_id}")
