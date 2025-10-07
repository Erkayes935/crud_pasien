from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.auth import require_roles_session
from backend.services.claim import note_service
from ..crud import claim_note as claim_crud

router = APIRouter(prefix="/claims", tags=["notes"])

class NoteCreate(BaseModel):
    item_id: int | None = None
    note_text: str
    parent_id: int | None = None
    field_key: str | None = None

@router.post("/{claim_id}/notes")
def create_note(
    claim_id: int,
    payload: NoteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor","coder","verifikator","admin_rs","superadmin")),
):
    print("📥 create_note request:", payload.dict(), "claim_id=", claim_id, "user=", current_user.id)

    if not payload.note_text.strip():
        raise HTTPException(status_code=400, detail="Note text cannot be empty")

    try:
        note = note_service.add_note_service(
            db=db,
            claim_id=claim_id,
            item_id=payload.item_id,
            user=current_user,
            note_text=payload.note_text.strip(),
            parent_id=payload.parent_id
        )
        print("✅ Note saved:", note.id, note.note_text)
        return {
            "id": note.id,
            "claim_id": note.claim_id,
            "item_id": note.item_id,
            "role": note.role,
            "user_id": note.user_id,
            "note_text": note.note_text,
            "timestamp": note.timestamp,
            "parent_id": note.parent_id,
        }
    except Exception as e:
        db.rollback()
        print("❌ ERROR saat simpan note:", e)
        raise HTTPException(status_code=500, detail=f"Gagal simpan note: {e}")
