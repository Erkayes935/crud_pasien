from sqlalchemy.orm import Session
from backend import models

def create_note(db: Session, claim_id: int, item_id: int | None, user_id: int, role: str,
                note_text: str, parent_id: int | None = None, timestamp=None):
    from backend import models

    note = models.ClaimNote(
        claim_id=claim_id,
        item_id=item_id,
        user_id=user_id,
        role=role,
        note_text=note_text,
        parent_id=parent_id,
        timestamp=timestamp   # fallback UTC kalau tidak dikirim
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note