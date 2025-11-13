from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import Any, Dict
from ..db import get_session
from ..models.core import DataHubSource, DataHubRecord
from ..schemas.unified import UnifiedClinicalRecord
from sqlalchemy.orm import Session
import pandas as pd
import uuid
from ..services import standardizer, validator
from ..services.hasher import generate_hashes
from ..services.duplicate_detector import DuplicateDetector
from ..services.anonymizer import Anonymizer  # FASE 1.2
from ..services.excel_mapper import map_excel_columns  # FASE 1.4: Dynamic column mapping
from io import BytesIO
from ..logging_config import get_logger
from ..services.logger import log_event

logger = get_logger(__name__)
router = APIRouter()

def _model_to_dict(m: Any) -> Dict:
    """
    Compat wrapper for Pydantic v1/v2:
    - v2: model_dump()
    - v1: dict()
    """
    if hasattr(m, "model_dump"):
        return m.model_dump()
    if hasattr(m, "dict"):
        return m.dict()
    return dict(m)

# ========== 1️⃣ Manual Input ==========
@router.post("/manual")
def ingest_manual(
    record: UnifiedClinicalRecord,
    db: Session = Depends(get_session)
):
    src = DataHubSource(type="manual")
    db.add(src)
    db.flush()

    data = _model_to_dict(record)
    try:
        validator.validate_fields(data)
    except ValueError as e:
        logger.warning("Validation failed for manual ingest: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    data = standardizer.run(data)
    
    # FASE 1.2: Anonymize if PHI present (for manual/excel only, gateway skip)
    anonymizer = Anonymizer(db)
    if anonymizer.should_anonymize(data, source_type="manual"):
        data = anonymizer.anonymize_record(
            data=data,
            source_type="manual",
            source_record_id=data.get("record_id")
        )
    
    # FASE 1.1: Generate hash & fingerprint
    hashes = generate_hashes(data)
    data["content_hash"] = hashes["content_hash"]
    data["similarity_fingerprint"] = hashes["similarity_fingerprint"]

    rec = DataHubRecord(
        record_id=data.get("record_id") or data.get("id") or str(uuid.uuid4()),
        hospital_id=data.get("hospital_id") or "unknown",
        source_id=src.id,
        json_data=data,
        status=data.get("status", "ready_for_ai"),
        content_hash=data["content_hash"],
        similarity_fingerprint=data["similarity_fingerprint"]
    )
    db.add(rec)
    db.flush()  # Get ID first before checking duplicates
    
    # FASE 1.1: Check for duplicates
    detector = DuplicateDetector(db)
    duplicate_check = detector.check_duplicate(rec)
    
    duplicate_warning = None
    if duplicate_check:
        # Mark as duplicate
        detector.mark_as_duplicate(rec, duplicate_check["type"])
        
        # Create duplicate group
        detector.create_duplicate_group(
            master_record_id=duplicate_check["match"].record_id,
            duplicate_record_ids=[rec.record_id],
            similarity_score=duplicate_check["score"],
            duplicate_type=duplicate_check["type"]
        )
        
        duplicate_warning = {
            "duplicate_detected": True,
            "duplicate_type": duplicate_check["type"],
            "similarity_score": duplicate_check["score"],
            "existing_record_id": duplicate_check["match"].record_id,
            "message": f"⚠️ {duplicate_check['type'].upper()} duplicate detected ({duplicate_check['score']}% similarity)"
        }
        
        log_event(
            db, 
            rec.record_id, 
            "manual", 
            "duplicate",
            f"{duplicate_check['type']} duplicate: {duplicate_check['score']}% similarity with {duplicate_check['match'].record_id}"
        )
    
    db.commit()
    log_event(db, rec.record_id, "manual", "info", "Record berhasil ditambahkan")
    logger.info("Manual record ingested: %s (src_id=%s)", rec.record_id, src.id)
    
    response = {
        "status": "ok", 
        "record_id": rec.record_id,
        "record_status": rec.status
    }
    
    if duplicate_warning:
        response["duplicate_warning"] = duplicate_warning
    
    return response


# ========== 2️⃣ Import Excel ==========
@router.post("/import_excel")
def ingest_excel(
    file: UploadFile = File(...),
    hospital_id: str = Form("unknown"),
    db: Session = Depends(get_session)
):
    # Support both Excel (.xlsx, .xls) and CSV (.csv)
    filename_lower = file.filename.lower()
    if not filename_lower.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="File harus Excel (.xlsx/.xls) atau CSV (.csv)")

    src = DataHubSource(type="import_excel", filename=file.filename, uploader="system")
    db.add(src)
    db.flush()

    # read into pandas DataFrame (use bytes)
    try:
        contents = file.file.read()
        # Auto-detect: CSV or Excel
        if filename_lower.endswith(".csv"):
            df = pd.read_csv(BytesIO(contents))
        else:
            df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        logger.exception("Failed to read uploaded file")
        raise HTTPException(status_code=400, detail="Gagal membaca file") from e
    finally:
        file.file.close()

    if "lama_rawat" in df.columns:
        df["lama_rawat"] = pd.to_numeric(df["lama_rawat"], errors="coerce").fillna(0).astype(int)
    df = df.fillna("")

    saved = 0
    duplicates_detected = 0
    detector = DuplicateDetector(db)
    anonymizer = Anonymizer(db)  # FASE 1.2: Add anonymizer for excel
    
    for _, row in df.iterrows():
        # FASE 1.4: Auto-map Excel columns to standard fields
        row_dict = row.to_dict()
        row_dict = map_excel_columns(row_dict)
        
        payload = {
            "record_id": str(uuid.uuid4()),
            "hospital_id": hospital_id,
            "source": "import_excel",
            # FASE 1.3.1: Add missing fields
            "episode_id": row_dict.get("episode_id") or None,
            "visit_no": int(row_dict.get("visit_no", 1)),
            "jenis_rawat": row_dict.get("jenis_rawat", "Rawat Inap"),
            "tanggal_masuk": str(row_dict.get("tanggal_masuk")),
            "lama_rawat": int(row_dict.get("lama_rawat", 0)),
            "gejala": row_dict.get("gejala"),
            "riwayat": row_dict.get("riwayat"),
            "diagnosis": row_dict.get("diagnosis"),
            "tindakan": row_dict.get("tindakan"),
            "obat": row_dict.get("obat"),
            "status": "ready_for_ai",
            # FASE 1.2: Excel might have PHI fields
            "nama_pasien": row_dict.get("nama_pasien"),
            "nik": row_dict.get("nik"),
            "alamat": row_dict.get("alamat"),
            "no_telepon": row_dict.get("no_telepon")
        }

        # FASE 1.4: Standardize FIRST (before validation!)
        # Reason: Standardizer converts dates/enums to expected format
        try:
            payload = standardizer.run(payload)
        except Exception as e:
            logger.warning("Standardization failed for import_excel: %s", e)
        
        # FASE 1.4: Then validate (after standardization)
        try:
            validator.validate_fields(payload)
        except ValueError as e:
            logger.warning("Row validation failed for import_excel: %s", e)
        
        # FASE 1.2: Anonymize if PHI present
        if anonymizer.should_anonymize(payload, source_type="excel"):
            payload = anonymizer.anonymize_record(
                data=payload,
                source_type="excel",
                source_record_id=payload["record_id"]
            )
        
        # FASE 1.1: Generate hash & fingerprint
        hashes = generate_hashes(payload)
        payload["content_hash"] = hashes["content_hash"]
        payload["similarity_fingerprint"] = hashes["similarity_fingerprint"]

        record = DataHubRecord(
            record_id=payload["record_id"],
            hospital_id=hospital_id,
            source_id=src.id,
            json_data=payload,
            status=payload.get("status", "ready_for_ai"),
            content_hash=payload["content_hash"],
            similarity_fingerprint=payload["similarity_fingerprint"]
        )
        db.add(record)
        db.flush()
        
        # FASE 1.1: Check for duplicates
        duplicate_check = detector.check_duplicate(record)
        if duplicate_check:
            detector.mark_as_duplicate(record, duplicate_check["type"])
            detector.create_duplicate_group(
                master_record_id=duplicate_check["match"].record_id,
                duplicate_record_ids=[record.record_id],
                similarity_score=duplicate_check["score"],
                duplicate_type=duplicate_check["type"]
            )
            duplicates_detected += 1
            log_event(
                db,
                record.record_id,
                "import_excel",
                "duplicate",
                f"{duplicate_check['type']} duplicate: {duplicate_check['score']}%"
            )
        
        saved += 1

    db.commit()
    log_event(db, src.id, "import_excel", "info", f"{saved} records imported, {duplicates_detected} duplicates detected")

    logger.info("Imported %d rows from Excel (%s), %d duplicates", saved, file.filename, duplicates_detected)
    return {
        "status": "ok", 
        "rows": saved,
        "duplicates_detected": duplicates_detected,
        "message": f"✅ {saved} records imported" + (f", ⚠️ {duplicates_detected} duplicates detected" if duplicates_detected > 0 else "")
    }

# ========== 3️⃣ Bridging Gateway ==========
@router.post("/gateway")
def ingest_gateway(
    payload: UnifiedClinicalRecord,
    db: Session = Depends(get_session)
):
    """
    Gateway endpoint - Data sudah ANONYMOUS dari Gateway!
    
    FASE 1.2: Gateway sudah anonymize (remove PHI, add patient_uuid).
    Data Hub hanya validate & store, TIDAK anonymize lagi.
    """
    src = DataHubSource(type="gateway")
    db.add(src)
    db.flush()

    data = _model_to_dict(payload)
    
    # FASE 1.2: Validate patient_uuid ada (dari Gateway)
    if not data.get("patient_uuid"):
        logger.warning("Gateway data missing patient_uuid")
        raise HTTPException(
            status_code=400, 
            detail="Gateway must send anonymized data with patient_uuid"
        )
    
    try:
        validator.validate_fields(data)
    except ValueError as e:
        logger.warning("Validation failed for gateway ingest: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    data = standardizer.run(data)
    
    # NOTE: Gateway data already anonymous, SKIP anonymizer!
    
    # FASE 1.1: Generate hash & fingerprint
    hashes = generate_hashes(data)
    data["content_hash"] = hashes["content_hash"]
    data["similarity_fingerprint"] = hashes["similarity_fingerprint"]

    record = DataHubRecord(
        record_id=data.get("record_id") or str(uuid.uuid4()),
        hospital_id=data.get("hospital_id") or "unknown",
        source_id=src.id,
        json_data=data,
        status=data.get("status", "ready_for_ai"),
        content_hash=data["content_hash"],
        similarity_fingerprint=data["similarity_fingerprint"]
    )
    db.add(record)
    db.flush()
    
    # FASE 1.1: Check for duplicates
    detector = DuplicateDetector(db)
    duplicate_check = detector.check_duplicate(record)
    
    duplicate_warning = None
    if duplicate_check:
        detector.mark_as_duplicate(record, duplicate_check["type"])
        detector.create_duplicate_group(
            master_record_id=duplicate_check["match"].record_id,
            duplicate_record_ids=[record.record_id],
            similarity_score=duplicate_check["score"],
            duplicate_type=duplicate_check["type"]
        )
        duplicate_warning = {
            "duplicate_detected": True,
            "duplicate_type": duplicate_check["type"],
            "similarity_score": duplicate_check["score"],
            "existing_record_id": duplicate_check["match"].record_id
        }
        log_event(
            db,
            record.record_id,
            "gateway",
            "duplicate",
            f"{duplicate_check['type']} duplicate: {duplicate_check['score']}%"
        )
    
    db.commit()
    log_event(db, record.record_id, "gateway", "info", "Record berhasil ditambahkan")
    logger.info("Gateway record ingested: %s (src_id=%s)", record.record_id, src.id)
    
    response = {
        "status": "ok",
        "record_id": record.record_id,
        "record_status": record.status
    }
    
    if duplicate_warning:
        response["duplicate_warning"] = duplicate_warning
    
    return response
