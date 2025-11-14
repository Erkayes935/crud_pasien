from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_datahub_session
from backend.models.datahub.core import DataHubRecord
import pandas as pd
from fastapi.responses import StreamingResponse
from io import BytesIO

router = APIRouter()

@router.get("/excel")
def export_excel(db: Session = Depends(get_datahub_session)):
    records = db.query(DataHubRecord).all()
    data = [r.json_data for r in records]
    df = pd.DataFrame(data)
    stream = BytesIO()
    df.to_excel(stream, index=False)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=datahub_export.xlsx"})
