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
    field_key: str | None = None,   # ✅ tambahkan parameter ini
    stage: str | None = None
):
    """
    Service untuk menambah catatan (note) ke klaim.
    Meneruskan ke CRUD dengan semua context:
    - field_key: nama kolom (mis. primary_diagnosis / primary_action)
    - stage: admission / daily / discharge
    """
    ts = datetime.now(WIB)

    print("➡️ add_note_service dipanggil",
          f"claim_id={claim_id}",
          f"item_id={item_id}",
          f"stage={stage}",
          f"user={user.id}",
          f"role={user.role}",
          f"timestamp={ts}")

    note = claim_note.create_note(
        db=db,
        claim_id=claim_id,
        item_id=item_id,
        user_id=user.id,
        role=user.role,
        note_text=note_text,
        parent_id=parent_id,
        field_key=field_key,   # ✅ sudah valid sekarang
        stage=stage,
        timestamp=ts
    )

    return note
