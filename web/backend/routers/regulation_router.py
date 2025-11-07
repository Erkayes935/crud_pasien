from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
import backend.crud.claim as claim_crud
from backend.services import claim_ai

router = APIRouter()


@router.post("/claims/{claim_id}/regulation_detail")
async def regulation_detail(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Ambil detail regulasi untuk klaim tertentu.
    Flow:
    1. Cek dulu di DB (hemat token).
    2. Kalau belum ada → request ke core_engine via claim_ai.
    3. Simpan hasil ke DB via claim_crud.
    """
    claim_id = payload.get("claim_id")
    field = payload.get("field")
    context_type = payload.get("context_type")
    item_id = payload.get("item_id")

    if not claim_id or not field:
        raise HTTPException(status_code=422, detail="claim_id dan field wajib ada")

    # 🔹 1. Cek dulu di DB
    regs = claim_crud.get_regulation_details(
        db=db,
        claim_id=claim_id,
        context_type=context_type,
        item_id=item_id
    )
    if regs:
        return {
            "status": "ok",
            "field": field,
            "data": [
                {
                    "id": r.id,
                    "judul_regulasi": r.judul_regulasi,
                    "dasar_hukum": r.dasar_hukum,
                    # "bab_pasal": removed - column deleted from database
                    "isi": r.isi,
                }
                for r in regs
            ],
        }

    # 🔹 2. Kalau belum ada → request ke core_engine
    result = await claim_ai.regulation_detail(payload)
    if not result or not result.get("regulasi"):
        raise HTTPException(status_code=500, detail="Gagal ambil regulasi dari core_engine")

    # 🔹 3. Simpan ke DB
    claim_crud.store_ai_recommendations(
        db=db,
        claim_id=claim_id,
        stage=payload.get("stage", "admission"),
        ai_data=result["regulasi"],
        mode="regulation",
    )

    return {"status": "ok", "field": field, "data": [result["regulasi"]]}
