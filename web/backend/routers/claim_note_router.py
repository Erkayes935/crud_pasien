# ==============================================
# backend/routers/claim_router.py  (NOTES MODULE)
# ==============================================
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import get_db
from backend.auth import require_roles_session
from backend.services.claim import note_service
from ..crud import claim_note as claim_crud

router = APIRouter(prefix="/claims", tags=["Notes"])

# ============================
# SCHEMA UNTUK INPUT
# ============================
class NoteCreate(BaseModel):
    item_id: int | None = None
    note_text: str
    parent_id: int | None = None
    field_key: str | None = None
    stage: str | None = None


# ============================
# ENDPOINT: CREATE NOTE
# ============================
@router.post("/{claim_id}/notes")
def create_note(
    claim_id: int,
    payload: NoteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """
    Simpan satu catatan (note) untuk klaim tertentu.
    - Dapat menyimpan context: stage (admission/daily/discharge)
    - Dapat menyimpan field_key (mis. primary_diagnosis, primary_action)
    """
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
            parent_id=payload.parent_id,
            field_key=payload.field_key,   # ✅ kirim field_key
            stage=payload.stage,           # ✅ kirim stage
        )

        print(f"✅ Note saved: {note.id} ({note.stage or '-'}) {note.note_text[:50]}")
        return {
            "status": "ok",
            "data": {
                "id": note.id,
                "claim_id": note.claim_id,
                "item_id": note.item_id,
                "role": note.role,
                "user_id": note.user_id,
                "note_text": note.note_text,
                "timestamp": note.timestamp,
                "parent_id": note.parent_id,
                "stage": note.stage,
                "field_key": note.field_key,
            },
        }
    except Exception as e:
        db.rollback()
        print("❌ ERROR saat simpan note:", e)
        raise HTTPException(status_code=500, detail=f"Gagal simpan note: {e}")


# ============================
# ENDPOINT: GET NOTES
# ============================
@router.get("/{claim_id}/notes")
def get_notes(
    claim_id: int,
    stage: str | None = None,
    field_key: str | None = None,
    item_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    try:
        notes = claim_crud.get_notes(db=db, claim_id=claim_id, stage=stage)
        if field_key:
            notes = [n for n in notes if n.field_key == field_key]
        if item_id:
            notes = [n for n in notes if n.item_id == item_id]

        return {
            "status": "ok",
            "count": len(notes),
            "data": [
                {
                    "id": n.id,
                    "claim_id": n.claim_id,
                    "item_id": n.item_id,
                    "role": n.role,
                    "user_id": n.user_id,
                    "note_text": n.note_text,
                    "timestamp": n.timestamp,
                    "parent_id": n.parent_id,
                    "stage": n.stage,
                    "field_key": n.field_key,   # ✅ tambahkan ini
                }
                for n in notes
            ],
        }
    except Exception as e:
        print("❌ Gagal ambil notes:", e)
        raise HTTPException(status_code=500, detail=f"Gagal ambil notes: {e}")


# ============================
# ENDPOINT: DELETE NOTE (opsional)
# ============================
@router.delete("/{claim_id}/notes/{note_id}")
def delete_note(
    claim_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """
    Hapus satu note berdasarkan ID
    """
    try:
        claim_crud.delete_note(db, note_id)
        print(f"🗑️ Note {note_id} deleted (claim {claim_id}) by user {current_user.id}")
        return {"status": "ok", "message": f"Note {note_id} deleted"}
    except Exception as e:
        db.rollback()
        print("❌ Gagal hapus note:", e)
        raise HTTPException(status_code=500, detail=f"Gagal hapus note: {e}")
