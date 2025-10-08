from sqlalchemy.orm import Session
from backend.crud import claim_note
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
WIB = timezone(timedelta(hours=7))

def add_note_service(db: Session, claim_id: int, item_id: int | None, user, note_text: str, parent_id: int | None = None):
    ts = datetime.now(WIB)   # ✅ waktu Jakarta

    print("➡️ add_note_service dipanggil claim_id=", claim_id,
          "item_id=", item_id,
          "user=", user.id,
          "role=", user.role,
          "timestamp=", ts)

    return claim_note.create_note(
        db=db,
        claim_id=claim_id,
        item_id=item_id,
        user_id=user.id,
        role=user.role,
        note_text=note_text,
        parent_id=parent_id,
        timestamp=ts   # simpan dengan WIB
    )