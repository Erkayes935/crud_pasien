# ============================================
# backend/services/claim/note_service.py
# ============================================

from sqlalchemy.orm import Session
from backend.crud import claim_note
from datetime import datetime, timedelta, timezone

# WIB timezone
WIB = timezone(timedelta(hours=7))
def add_note_service(
    db: Session,
    claim_id: int,
    item_id: int | None,
    user,
    note_text: str,
    parent_id: int | None = None,
    field_key: str | None = None,
    stage: str | None = None
):
    """
    Service untuk menambah catatan (note) ke klaim.
    - Menyimpan catatan sesuai peran (doctor/coder/verifikator)
    - Jika role = coder → juga isi origin_item_id (diagnosis/procedure asli)
    """
    ts = datetime.now(WIB)
    origin_item_id = None

    print(
        "➡️ add_note_service dipanggil",
        f"claim_id={claim_id}",
        f"item_id={item_id}",
        f"stage={stage}",
        f"user={user.id}",
        f"role={user.role}",
        f"timestamp={ts}"
    )

    try:
        # 🔍 kalau role coder, cari asal diagnosis/procedure
        if user.role == "coder" and item_id:
            diag_eval = db.query(models.ClaimDiagnosisEvaluation).filter_by(id=item_id).first()
            proc_eval = db.query(models.ClaimProcedureEvaluation).filter_by(id=item_id).first()

            if diag_eval and hasattr(diag_eval, "diagnosis_id"):
                origin_item_id = diag_eval.diagnosis_id
            elif proc_eval and hasattr(proc_eval, "procedure_id"):
                origin_item_id = proc_eval.procedure_id

        # 🩺 kalau bukan coder, origin_item_id = item_id itu sendiri
        if not origin_item_id:
            origin_item_id = item_id

        # 💾 simpan ke DB
        note = claim_note.create_note(
            db=db,
            claim_id=claim_id,
            item_id=item_id,
            user_id=user.id,
            role=user.role,
            note_text=note_text.strip(),
            parent_id=parent_id,
            field_key=field_key,
            stage=stage,
            timestamp=ts,
        )

        # 🔄 isi kolom origin_item_id kalau ada
        if hasattr(note, "origin_item_id") and origin_item_id:
            note.origin_item_id = origin_item_id
            db.add(note)
            db.commit()
            db.refresh(note)

        print(f"✅ Note saved: {note.id} (origin={origin_item_id}) {note.note_text[:40]}")
        return note

    except Exception as e:
        db.rollback()
        print("❌ ERROR add_note_service:", e)
        raise