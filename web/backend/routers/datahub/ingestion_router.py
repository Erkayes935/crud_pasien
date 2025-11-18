from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import Any, Dict
from backend.database import get_datahub_session
from backend.models.datahub.core import DataHubSource, DataHubRecord
from backend.schemas.unified import UnifiedClinicalRecord
from backend.auth import require_roles_session
from sqlalchemy.orm import Session
import pandas as pd
import uuid
from backend.services.datahub import standardizer, validator
from backend.services.datahub.hasher import generate_hashes
from backend.services.datahub.duplicate_detector import DuplicateDetector
from backend.services.datahub.anonymizer import Anonymizer  # FASE 1.2
from backend.services.datahub.excel_mapper import map_excel_columns  # FASE 1.4: Dynamic column mapping
from io import BytesIO
import logging
from backend.services.datahub.logger import log_event

logger = logging.getLogger(__name__)
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
    db: Session = Depends(get_datahub_session)
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
    
    # FASE 1.1 + 2.6: Check for duplicates with confidence-based decision
    detector = DuplicateDetector(db)
    duplicate_check = detector.check_duplicate(rec)
    
    duplicate_warning = None
    
    # FASE 2.6: ALWAYS store similarity info (even if < 85%)
    if duplicate_check:
        rec.similarity_info = {
            "checked": True,
            "max_score": duplicate_check["score"],
            "closest_record": duplicate_check["match"].record_id if duplicate_check["match"] else None,
            "confidence": duplicate_check.get("confidence"),
            "is_duplicate": duplicate_check.get("is_duplicate", False)
        }
    else:
        rec.similarity_info = {
            "checked": True,
            "max_score": 0,
            "closest_record": None,
            "confidence": None,
            "is_duplicate": False
        }
    
    # Only process as duplicate if >= threshold (is_duplicate = True)
    if duplicate_check and duplicate_check.get("is_duplicate", False):
        confidence = duplicate_check.get("confidence", "low")
        
        # FASE 2.1: Auto-merge decision based on confidence level
        if confidence in ["exact", "very_high", "high"]:  # ≥93% similarity
            # HIGH CONFIDENCE → Auto-merge
            group = detector.create_duplicate_group(
                master_record_id=duplicate_check["match"].record_id,
                duplicate_record_ids=[rec.record_id],
                similarity_score=duplicate_check["score"],
                duplicate_type=duplicate_check["type"]
            )
            
            # Auto-merge immediately
            detector.merge_duplicates(group.id)
            
            duplicate_warning = {
                "duplicate_detected": True,
                "duplicate_type": duplicate_check["type"],
                "similarity_score": duplicate_check["score"],
                "confidence": confidence,
                "action": "auto_merged",
                "existing_record_id": duplicate_check["match"].record_id,
                "message": f"✅ AUTO-MERGED: {confidence.upper()} confidence duplicate ({duplicate_check['score']}%)"
            }
            
            log_event(
                db, 
                rec.record_id, 
                "manual", 
                "info",
                f"Auto-merged ({confidence}): {duplicate_check['score']}% similarity with {duplicate_check['match'].record_id}"
            )
            
        elif confidence == "medium":  # 88-92% similarity
            # MEDIUM CONFIDENCE → Flag for manual review
            rec.status = "possible_duplicate"
            
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
                "confidence": confidence,
                "action": "flagged_for_review",
                "existing_record_id": duplicate_check["match"].record_id,
                "message": f"⚠️ REVIEW REQUIRED: Medium confidence duplicate ({duplicate_check['score']}%) - Manual verification needed"
            }
            
            log_event(
                db, 
                rec.record_id, 
                "manual", 
                "duplicate",
                f"Medium confidence duplicate ({duplicate_check['score']}%) - flagged for review"
            )
            
        else:  # low confidence (85-87%)
            # LOW CONFIDENCE → Just warning, don't block
            rec.status = "duplicate_flagged"
            
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
                "confidence": confidence,
                "action": "suspicious_flagged",
                "existing_record_id": duplicate_check["match"].record_id,
                "message": f"🚩 SUSPICIOUS: Low confidence duplicate ({duplicate_check['score']}%) - Proceed with caution"
            }
            
            log_event(
                db, 
                rec.record_id, 
                "manual", 
                "info",
                f"Low confidence duplicate ({duplicate_check['score']}%) - flagged as suspicious"
            )
    else:
        # FASE 2.6: Log similarity info even if < 85% (not duplicate)
        if duplicate_check:
            log_event(
                db, 
                rec.record_id, 
                "manual", 
                "info",
                f"Similarity check: {duplicate_check['score']:.1f}% with {duplicate_check['match'].record_id} (below threshold, not duplicate)"
            )
        else:
            log_event(
                db, 
                rec.record_id, 
                "manual", 
                "info",
                "Similarity check: No matching records found (unique data)"
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
    db: Session = Depends(get_datahub_session)
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
        
        # FASE 1.1 & 2.1 & 2.6: Check for duplicates with confidence-based decision
        duplicate_check = detector.check_duplicate(record)
        
        # FASE 2.6: ALWAYS store similarity info (even if < 85%)
        if duplicate_check:
            record.similarity_info = {
                "checked": True,
                "max_score": duplicate_check["score"],
                "closest_record": duplicate_check["match"].record_id if duplicate_check["match"] else None,
                "confidence": duplicate_check.get("confidence"),
                "is_duplicate": duplicate_check.get("is_duplicate", False)
            }
        else:
            record.similarity_info = {
                "checked": True,
                "max_score": 0,
                "closest_record": None,
                "confidence": None,
                "is_duplicate": False
            }
        
        # Only process as duplicate if >= threshold
        if duplicate_check and duplicate_check.get("is_duplicate", False):
            confidence = duplicate_check.get("confidence", "low")
            
            # Auto-merge decision based on confidence
            if confidence in ["exact", "very_high", "high"]:  # ≥93%
                # HIGH CONFIDENCE → Auto-merge
                group = detector.create_duplicate_group(
                    master_record_id=duplicate_check["match"].record_id,
                    duplicate_record_ids=[record.record_id],
                    similarity_score=duplicate_check["score"],
                    duplicate_type=duplicate_check["type"]
                )
                detector.merge_duplicates(group.id)
                log_event(db, record.record_id, "import_excel", "info",
                    f"Auto-merged ({confidence}): {duplicate_check['score']}% with {duplicate_check['match'].record_id}")
                    
            elif confidence == "medium":  # 88-92%
                # MEDIUM CONFIDENCE → Flag for review
                record.status = "possible_duplicate"
                detector.create_duplicate_group(
                    master_record_id=duplicate_check["match"].record_id,
                    duplicate_record_ids=[record.record_id],
                    similarity_score=duplicate_check["score"],
                    duplicate_type=duplicate_check["type"]
                )
                log_event(db, record.record_id, "import_excel", "duplicate",
                    f"Medium confidence ({duplicate_check['score']}%) - flagged for review")
                    
            else:  # low (85-87%)
                # LOW CONFIDENCE → Just flag
                record.status = "duplicate_flagged"
                detector.create_duplicate_group(
                    master_record_id=duplicate_check["match"].record_id,
                    duplicate_record_ids=[record.record_id],
                    similarity_score=duplicate_check["score"],
                    duplicate_type=duplicate_check["type"]
                )
                log_event(db, record.record_id, "import_excel", "info",
                    f"Low confidence ({duplicate_check['score']}%) - flagged as suspicious")
            
            duplicates_detected += 1
        else:
            # FASE 2.6: Log similarity info even if < 85% (not duplicate)
            if duplicate_check:
                log_event(db, record.record_id, "import_excel", "info",
                    f"Similarity check: {duplicate_check['score']:.1f}% with {duplicate_check['match'].record_id} (below threshold, not duplicate)")
            else:
                log_event(db, record.record_id, "import_excel", "info",
                    "Similarity check: No matching records found (unique data)")
        
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


# ========== 2️⃣B FASE 3: Excel Preview (Column Analysis) ==========
@router.post("/excel/preview")
def preview_excel_columns(
    file: UploadFile = File(...),
    db: Session = Depends(get_datahub_session)
):
    """
    FASE 3: Preview Excel columns and suggest mappings.
    
    NO DATABASE INSERT! Just analyze structure.
    
    Returns:
        ColumnAnalysis with exact/fuzzy matches, missing fields, extra columns
    """
    from backend.services.datahub.excel_mapper import analyze_excel_columns
    from backend.schemas.unified import ColumnAnalysis, ColumnMatch
    
    # Validate file type
    filename_lower = file.filename.lower()
    if not filename_lower.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="File harus Excel (.xlsx/.xls) atau CSV (.csv)")
    
    # Read Excel into DataFrame
    try:
        contents = file.file.read()
        if filename_lower.endswith(".csv"):
            df = pd.read_csv(BytesIO(contents))
        else:
            df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    # Analyze columns
    analysis = analyze_excel_columns(df, threshold=75)
    
    # Convert to Pydantic models
    exact_matches = [ColumnMatch(**m) for m in analysis["exact_matches"]]
    fuzzy_matches = [ColumnMatch(**m) for m in analysis["fuzzy_matches"]]
    
    result = ColumnAnalysis(
        total_rows=analysis["total_rows"],
        total_columns=analysis["total_columns"],
        exact_matches=exact_matches,
        fuzzy_matches=fuzzy_matches,
        missing_fields=analysis["missing_fields"],
        extra_columns=analysis["extra_columns"],
        preview_data=analysis["preview_data"]
    )
    
    logger.info(f"Preview Excel: {len(df)} rows, {len(df.columns)} columns, {len(exact_matches)} exact, {len(fuzzy_matches)} fuzzy")
    
    return result


# ========== 2️⃣C FASE 3: Excel Import with User-Confirmed Mapping ==========
@router.post("/excel/import-with-mapping")
def import_excel_with_mapping(
    file: UploadFile = File(...),
    mapping_json: str = Form(...),
    hospital_id: str = Form("unknown"),
    db: Session = Depends(get_datahub_session)
):
    """
    FASE 3: Import Excel with user-confirmed column mapping.
    
    Flow:
    1. User confirms mapping from /excel/preview
    2. Apply mapping to DataFrame
    3. Process rows (same as /import_excel)
    4. Insert to database
    
    Args:
        file: Excel file
        mapping_json: JSON string of ColumnMappingRequest
        hospital_id: Hospital ID
    
    Returns:
        ImportResult with success/failed counts
    """
    from backend.services.datahub.excel_mapper import apply_column_mapping
    from backend.schemas.unified import ColumnMappingRequest, ImportResult
    import json
    
    # Parse mapping JSON
    try:
        mapping_dict = json.loads(mapping_json)
        mapping = ColumnMappingRequest(**mapping_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid mapping JSON: {str(e)}")
    
    # Validate file type
    filename_lower = file.filename.lower()
    if not filename_lower.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="File harus Excel (.xlsx/.xls) atau CSV (.csv)")
    
    # Read Excel or CSV
    try:
        contents = file.file.read()
        if filename_lower.endswith(".csv"):
            df = pd.read_csv(BytesIO(contents))
        else:
            df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        logger.error(f"Failed to read Excel: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    # Apply user-confirmed mapping
    df_mapped = apply_column_mapping(
        df,
        column_mapping=mapping.column_mapping,
        extra_column_action=mapping.extra_column_action,
        missing_field_values=mapping.missing_field_values
    )
    
    # Create source
    src = DataHubSource(type="import_excel", filename=file.filename, uploader="system")
    db.add(src)
    db.flush()
    
    # Process rows (SAME LOGIC AS /import_excel)
    saved = 0
    failed = 0
    errors = []
    duplicates_detected = 0
    detector = DuplicateDetector(db)
    
    for idx, row in df_mapped.iterrows():
        try:
            # Clean NaN values (pandas NaN -> None for JSON compatibility)
            row_dict = row.to_dict()
            row_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
            
            # Map columns
            data = map_excel_columns(row_dict)
            data["hospital_id"] = hospital_id
            data["source"] = "import_excel"
            
            # Validate
            validator.validate_fields(data)
            
            # Standardize
            data = standardizer.run(data)
            
            # Generate hashes
            hashes = generate_hashes(data)
            
            # Create record first
            record = DataHubRecord(
                record_id=data.get("record_id") or f"REC_{uuid.uuid4().hex[:8].upper()}",
                hospital_id=data["hospital_id"],
                source_id=src.id,
                json_data=data,
                content_hash=hashes["content_hash"],
                similarity_fingerprint=hashes["similarity_fingerprint"]
            )
            db.add(record)
            db.flush()
            
            # Check duplicate with record object
            duplicate_check = detector.check_duplicate(record)
            
            # Store similarity info (serialize match object to record_id)
            if duplicate_check:
                record.similarity_info = {
                    "checked": True,
                    "type": duplicate_check["type"],
                    "max_score": duplicate_check["score"],
                    "closest_record": duplicate_check["match"].record_id if duplicate_check.get("match") else None,
                    "confidence": duplicate_check.get("confidence"),
                    "is_duplicate": duplicate_check.get("is_duplicate", False)
                }
            else:
                record.similarity_info = {
                    "checked": True,
                    "max_score": 0.0,
                    "closest_record": None,
                    "confidence": None,
                    "is_duplicate": False
                }
            
            # Handle duplicates (same logic)
            if duplicate_check and duplicate_check.get("is_duplicate", False):
                confidence = duplicate_check.get("confidence", "low")
                
                if confidence in ["exact", "very_high", "high"]:
                    group = detector.create_duplicate_group(
                        master_record_id=duplicate_check["match"].record_id,
                        duplicate_record_ids=[record.record_id],
                        similarity_score=duplicate_check["score"],
                        duplicate_type=duplicate_check["type"]
                    )
                    detector.merge_duplicates(group.id)
                    log_event(db, record.record_id, "import_excel", "info",
                        f"Auto-merged ({confidence}): {duplicate_check['score']}%")
                elif confidence == "medium":
                    record.status = "possible_duplicate"
                    detector.create_duplicate_group(
                        master_record_id=duplicate_check["match"].record_id,
                        duplicate_record_ids=[record.record_id],
                        similarity_score=duplicate_check["score"],
                        duplicate_type=duplicate_check["type"]
                    )
                    log_event(db, record.record_id, "import_excel", "duplicate",
                        f"Medium confidence - flagged for review")
                else:
                    record.status = "duplicate_flagged"
                    detector.create_duplicate_group(
                        master_record_id=duplicate_check["match"].record_id,
                        duplicate_record_ids=[record.record_id],
                        similarity_score=duplicate_check["score"],
                        duplicate_type=duplicate_check["type"]
                    )
                
                duplicates_detected += 1
            else:
                if duplicate_check:
                    log_event(db, record.record_id, "import_excel", "info",
                        f"Similarity: {duplicate_check['score']:.1f}% (below threshold)")
            
            # ✅ NEW: Auto-split to structured tables (Patient, Visit, MedicalRecord)
            try:
                from backend.services.datahub.record_processor import split_to_structured_tables
                split_result = split_to_structured_tables(record, db)
                log_event(db, record.record_id, "import_excel", "info",
                    f"Split to tables: Patient {split_result['patient'].patient_uuid}, Visit {split_result['visit'].visit_uuid}")
            except Exception as split_error:
                logger.warning(f"Failed to split record {record.record_id} to tables: {split_error}")
                # Continue anyway - record still in data_hub_records
            
            saved += 1
            
        except Exception as e:
            failed += 1
            error_msg = f"Row {idx + 1}: {str(e)}"
            errors.append(error_msg)
            logger.warning(error_msg)
    
    db.commit()
    log_event(db, src.id, "import_excel", "info", 
        f"Imported {saved} records, {failed} failed, {duplicates_detected} duplicates")
    
    logger.info(f"Excel import with mapping: {saved} success, {failed} failed")
    
    return ImportResult(
        source_id=src.id,
        records_imported=saved,
        records_failed=failed,
        duplicates_found=duplicates_detected,
        errors=errors
    )


# ========== 3️⃣ Bridging Gateway ==========
@router.post("/gateway")
def ingest_gateway(
    payload: UnifiedClinicalRecord,
    db: Session = Depends(get_datahub_session)
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
    
    # FASE 1.1 & 2.1 & 2.6: Check for duplicates with confidence-based decision
    detector = DuplicateDetector(db)
    duplicate_check = detector.check_duplicate(record)
    
    duplicate_warning = None
    
    # FASE 2.6: ALWAYS store similarity info (even if < 85%)
    if duplicate_check:
        record.similarity_info = {
            "checked": True,
            "max_score": duplicate_check["score"],
            "closest_record": duplicate_check["match"].record_id if duplicate_check["match"] else None,
            "confidence": duplicate_check.get("confidence"),
            "is_duplicate": duplicate_check.get("is_duplicate", False)
        }
    else:
        record.similarity_info = {
            "checked": True,
            "max_score": 0,
            "closest_record": None,
            "confidence": None,
            "is_duplicate": False
        }
    
    # Only process as duplicate if >= threshold
    if duplicate_check and duplicate_check.get("is_duplicate", False):
        confidence = duplicate_check.get("confidence", "low")
        
        # Auto-merge decision based on confidence
        if confidence in ["exact", "very_high", "high"]:  # ≥93%
            # HIGH CONFIDENCE → Auto-merge
            group = detector.create_duplicate_group(
                master_record_id=duplicate_check["match"].record_id,
                duplicate_record_ids=[record.record_id],
                similarity_score=duplicate_check["score"],
                duplicate_type=duplicate_check["type"]
            )
            detector.merge_duplicates(group.id)
            
            duplicate_warning = {
                "duplicate_detected": True,
                "duplicate_type": duplicate_check["type"],
                "similarity_score": duplicate_check["score"],
                "confidence": confidence,
                "action": "auto_merged",
                "existing_record_id": duplicate_check["match"].record_id
            }
            log_event(db, record.record_id, "gateway", "info",
                f"Auto-merged ({confidence}): {duplicate_check['score']}%")
                
        elif confidence == "medium":  # 88-92%
            # MEDIUM CONFIDENCE → Flag for review
            record.status = "possible_duplicate"
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
                "confidence": confidence,
                "action": "flagged_for_review",
                "existing_record_id": duplicate_check["match"].record_id
            }
            log_event(db, record.record_id, "gateway", "duplicate",
                f"Medium confidence ({duplicate_check['score']}%) - flagged for review")
                
        else:  # low (85-87%)
            # LOW CONFIDENCE → Just flag
            record.status = "duplicate_flagged"
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
                "confidence": confidence,
                "action": "suspicious_flagged",
                "existing_record_id": duplicate_check["match"].record_id
            }
            log_event(db, record.record_id, "gateway", "info",
                f"Low confidence ({duplicate_check['score']}%) - flagged as suspicious")
    else:
        # FASE 2.6: Log similarity info even if < 85% (not duplicate)
        if duplicate_check:
            log_event(db, record.record_id, "gateway", "info",
                f"Similarity check: {duplicate_check['score']:.1f}% with {duplicate_check['match'].record_id} (below threshold, not duplicate)")
        else:
            log_event(db, record.record_id, "gateway", "info",
                "Similarity check: No matching records found (unique data)")
    
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
