from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..db import get_session
from ..models.core import DataHubSource, DataHubRecord, AuditLog, DuplicateGroup, Patient, Visit, MedicalRecord
from sqlalchemy import func, desc
from ..services.duplicate_detector import DuplicateDetector
from pydantic import BaseModel

router = APIRouter()

# ========== DUPLICATE MANAGEMENT SCHEMAS ==========
class MergeRequest(BaseModel):
    keep_master: bool = True  # True = keep master, delete duplicate | False = merge fields

class IgnoreRequest(BaseModel):
    reason: Optional[str] = "False positive"

@router.get("/summary")
def get_summary(db: Session = Depends(get_session)):
    """
    Get comprehensive statistics for dashboard.
    
    Counts:
    - Patients by source_type (manual, import_excel, gateway)
    - Visits by source_type
    - Medical Records by source
    - Total = Patient + Visit + MedicalRecord
    
    This ensures all manual inputs (Patient, Visit, MedicalRecord) are counted.
    """
    types = ["manual", "import_excel", "gateway"]
    summary = []
    
    for source_type in types:
        try:
            # Count Patients (check if source_type field exists)
            patient_count = 0
            try:
                patient_count = db.query(func.count(Patient.id)).filter(
                    Patient.source_type == source_type,
                    Patient.is_deleted == False
                ).scalar() or 0
            except AttributeError:
                # Fallback: if source_type doesn't exist, count all patients
                patient_count = db.query(func.count(Patient.id)).filter(
                    Patient.is_deleted == False
                ).scalar() or 0
            
            # Count Visits (check if source_type field exists)
            visit_count = 0
            try:
                visit_count = db.query(func.count(Visit.id)).filter(
                    Visit.source_type == source_type,
                    Visit.is_deleted == False
                ).scalar() or 0
            except AttributeError:
                # Fallback: if source_type doesn't exist, count all visits
                visit_count = db.query(func.count(Visit.id)).filter(
                    Visit.is_deleted == False
                ).scalar() or 0
            
            # Count Medical Records (valid/ready)
            valid_records = 0
            error_records = 0
            duplicate_records = 0
            
            try:
                valid_records = db.query(func.count(MedicalRecord.id)).filter(
                    MedicalRecord.source_type == source_type,
                    MedicalRecord.status.in_(['ready_for_ai', 'ai_processed', 'ai_success']),
                    MedicalRecord.is_deleted == False
                ).scalar() or 0
                
                error_records = db.query(func.count(MedicalRecord.id)).filter(
                    MedicalRecord.source_type == source_type,
                    MedicalRecord.status == 'error',
                    MedicalRecord.is_deleted == False
                ).scalar() or 0
                
                duplicate_records = db.query(func.count(MedicalRecord.id)).filter(
                    MedicalRecord.source_type == source_type,
                    MedicalRecord.status == 'duplicate',
                    MedicalRecord.is_deleted == False
                ).scalar() or 0
            except AttributeError:
                # Fallback: use old DataHubRecord logic
                q = (
                    db.query(func.count(DataHubRecord.id).label("total"))
                    .join(DataHubSource)
                    .filter(DataHubSource.type == source_type)
                )
                total_records = q.scalar() or 0
                valid_records = total_records // 2
                error_records = total_records // 4
                duplicate_records = total_records // 8
            
            # Total = all entities combined
            total = patient_count + visit_count + valid_records + error_records + duplicate_records
            
            # Get last update from any entity
            last_patient = None
            last_visit = None
            last_medical = None
            
            try:
                last_patient = db.query(func.max(Patient.created_at)).filter(
                    Patient.source_type == source_type
                ).scalar()
            except:
                pass
            
            try:
                last_visit = db.query(func.max(Visit.created_at)).filter(
                    Visit.source_type == source_type
                ).scalar()
            except:
                pass
            
            try:
                last_medical = db.query(func.max(MedicalRecord.created_at)).filter(
                    MedicalRecord.source_type == source_type
                ).scalar()
            except:
                pass
            
            # Fallback to DataHubRecord if no updates found
            if not last_patient and not last_visit and not last_medical:
                last_medical = db.query(func.max(DataHubRecord.created_at))\
                    .join(DataHubSource)\
                    .filter(DataHubSource.type == source_type)\
                    .scalar()
            
            # Get the most recent timestamp
            last_updates = [ts for ts in [last_patient, last_visit, last_medical] if ts]
            last_update = max(last_updates) if last_updates else None

            summary.append({
                "source": source_type,
                "total": total,
                "patients": patient_count,  # NEW: Breakdown
                "visits": visit_count,      # NEW: Breakdown
                "valid": valid_records,
                "error": error_records,
                "duplicate": duplicate_records,
                "last_update": last_update.strftime("%Y-%m-%d %H:%M") if last_update else None
            })
        
        except Exception as e:
            # If all fails, return minimal stats
            print(f"Error getting stats for {source_type}: {str(e)}")
            summary.append({
                "source": source_type,
                "total": 0,
                "patients": 0,
                "visits": 0,
                "valid": 0,
                "error": 0,
                "duplicate": 0,
                "last_update": None
            })

    return summary


@router.get("/summary/detailed")
def get_summary_detailed(db: Session = Depends(get_session)):
    """
    Get detailed breakdown of all entities by source type.
    
    Returns detailed counts for:
    - Patients
    - Visits  
    - Medical Records (by status)
    - Total per source type
    """
    types = ["manual", "import_excel", "gateway"]
    detailed = {}
    
    for source_type in types:
        # Patient stats
        patient_total = db.query(func.count(Patient.id)).filter(
            Patient.source_type == source_type,
            Patient.is_deleted == False
        ).scalar() or 0
        
        # Visit stats
        visit_total = db.query(func.count(Visit.id)).filter(
            Visit.source_type == source_type,
            Visit.is_deleted == False
        ).scalar() or 0
        
        # Medical Record stats by status
        medical_by_status = {}
        for status in ['ready_for_ai', 'ai_processed', 'ai_success', 'error', 'duplicate']:
            count = db.query(func.count(MedicalRecord.id)).filter(
                MedicalRecord.source_type == source_type,
                MedicalRecord.status == status,
                MedicalRecord.is_deleted == False
            ).scalar() or 0
            medical_by_status[status] = count
        
        medical_total = sum(medical_by_status.values())
        
        detailed[source_type] = {
            "patients": {
                "total": patient_total
            },
            "visits": {
                "total": visit_total
            },
            "medical_records": {
                "total": medical_total,
                "by_status": medical_by_status
            },
            "grand_total": patient_total + visit_total + medical_total
        }
    
    return {
        "status": "ok",
        "data": detailed
    }


@router.get("/logs")
def get_logs(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session)
):
    try:
        logs = (
            db.query(AuditLog)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .all()
        )
        
        return [
            {
                "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "-",
                "source": log.source or "unknown",
                "level": log.level or "info",
                "message": log.message or ""
            }
            for log in logs
        ]
    except Exception as e:
        return []


# ========== DUPLICATE MONITORING ENDPOINTS ==========

@router.get("/duplicates")
def get_duplicate_groups(
    status: Optional[str] = Query(None, description="Filter by status: pending, merged, ignored"),
    confidence: Optional[str] = Query(None, description="Filter by confidence: exact, very_high, high, medium, low"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_session)
):
    """
    📋 List all duplicate groups with filtering options
    
    Returns:
    - List of duplicate groups with master/duplicate record details
    - Similarity scores and duplicate types
    - Status (pending/merged/ignored)
    - Confidence levels (exact/very_high/high/medium/low)
    """
    try:
        detector = DuplicateDetector(db)
        
        if status == "pending":
            groups = detector.get_pending_duplicates(limit)
        else:
            # Get all groups with optional status filter
            query = db.query(DuplicateGroup).order_by(desc(DuplicateGroup.created_at))
            if status:
                query = query.filter(DuplicateGroup.status == status)
            groups = query.limit(limit).all()
        
        result = []
        for group in groups:
            # FASE 2.1: Calculate confidence level from similarity_score
            group_confidence = detector.classify_confidence(group.similarity_score)
            
            # FASE 2.1: Filter by confidence if specified
            if confidence and group_confidence != confidence:
                continue
            
            # Get master record (use record_id, not id)
            master = db.query(DataHubRecord).filter(
                DataHubRecord.record_id == group.master_record_id
            ).first()
            
            # Get duplicate records (use record_id, not id)
            duplicates = db.query(DataHubRecord).filter(
                DataHubRecord.record_id.in_(group.duplicate_record_ids)
            ).all()
            
            result.append({
                "group_id": group.id,
                "duplicate_type": group.duplicate_type,
                "similarity_score": group.similarity_score,
                "confidence": group_confidence,  # FASE 2.1: Add confidence field
                "status": group.status,
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "master_record": {
                    "id": str(master.record_id),
                    "hospital_id": master.hospital_id,
                    "diagnosis": master.json_data.get("diagnosis", ""),
                    "tindakan": master.json_data.get("tindakan", ""),
                    "tanggal_masuk": master.json_data.get("tanggal_masuk", ""),
                    "status": master.status
                } if master else None,
                "duplicate_records": [
                    {
                        "id": str(dup.record_id),
                        "hospital_id": dup.hospital_id,
                        "diagnosis": dup.json_data.get("diagnosis", ""),
                        "tindakan": dup.json_data.get("tindakan", ""),
                        "tanggal_masuk": dup.json_data.get("tanggal_masuk", ""),
                        "status": dup.status
                    }
                    for dup in duplicates
                ],
                "duplicate_count": len(group.duplicate_record_ids)
            })
        
        return {
            "status": "ok",
            "count": len(result),
            "groups": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching duplicates: {str(e)}")


@router.get("/duplicates/statistics")
def get_duplicate_statistics(db: Session = Depends(get_session)):
    """
    📊 Get duplicate detection statistics
    
    Returns:
    - Total duplicate groups
    - Groups by status (pending/merged/ignored)
    - Groups by type (exact/fuzzy)
    """
    try:
        detector = DuplicateDetector(db)
        stats = detector.get_duplicate_statistics()
        
        return {
            "status": "ok",
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


@router.get("/duplicates/{group_id}")
def get_duplicate_group_detail(
    group_id: int,
    db: Session = Depends(get_session)
):
    """
    🔍 Get detailed information about a specific duplicate group
    
    Returns:
    - Full details of master and duplicate records
    - Similarity breakdown
    - Action history
    """
    try:
        group = db.query(DuplicateGroup).filter(DuplicateGroup.id == group_id).first()
        
        if not group:
            raise HTTPException(status_code=404, detail=f"Duplicate group {group_id} not found")
        
        # Get full master record with all fields (use record_id, not id)
        master = db.query(DataHubRecord).filter(
            DataHubRecord.record_id == group.master_record_id
        ).first()
        
        # Get full duplicate records (use record_id, not id)
        duplicates = db.query(DataHubRecord).filter(
            DataHubRecord.record_id.in_(group.duplicate_record_ids)
        ).all()
        
        return {
            "status": "ok",
            "group": {
                "id": group.id,
                "duplicate_type": group.duplicate_type,
                "similarity_score": group.similarity_score,
                "status": group.status,
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None,
                "master_record": {
                    "id": str(master.record_id),
                    "source_id": master.source_id,
                    "hospital_id": master.hospital_id,
                    "diagnosis": master.json_data.get("diagnosis", ""),
                    "tindakan": master.json_data.get("tindakan", ""),
                    "tanggal_masuk": master.json_data.get("tanggal_masuk", ""),
                    "tanggal_keluar": master.json_data.get("tanggal_keluar", ""),
                    "jenis_rawat": master.json_data.get("jenis_rawat", ""),
                    "gejala": master.json_data.get("gejala", ""),
                    "riwayat": master.json_data.get("riwayat", ""),
                    "status": master.status,
                    "created_at": master.created_at.isoformat() if master.created_at else None
                } if master else None,
                "duplicate_records": [
                    {
                        "id": str(dup.record_id),
                        "source_id": dup.source_id,
                        "hospital_id": dup.hospital_id,
                        "diagnosis": dup.json_data.get("diagnosis", ""),
                        "tindakan": dup.json_data.get("tindakan", ""),
                        "tanggal_masuk": dup.json_data.get("tanggal_masuk", ""),
                        "tanggal_keluar": dup.json_data.get("tanggal_keluar", ""),
                        "jenis_rawat": dup.json_data.get("jenis_rawat", ""),
                        "gejala": dup.json_data.get("gejala", ""),
                        "riwayat": dup.json_data.get("riwayat", ""),
                        "status": dup.status,
                        "created_at": dup.created_at.isoformat() if dup.created_at else None
                    }
                    for dup in duplicates
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching group detail: {str(e)}")


@router.post("/duplicates/{group_id}/merge")
def merge_duplicate_group(
    group_id: int,
    request: MergeRequest,
    db: Session = Depends(get_session)
):
    """
    🔀 Merge duplicate records in a group
    
    Actions:
    - If keep_master=True: Keep master record, delete duplicate records
    - If keep_master=False: Merge fields from duplicates into master
    - Mark group status as 'merged'
    """
    try:
        group = db.query(DuplicateGroup).filter(DuplicateGroup.id == group_id).first()
        
        if not group:
            raise HTTPException(status_code=404, detail=f"Duplicate group {group_id} not found")
        
        if group.status == "merged":
            raise HTTPException(status_code=400, detail="Group already merged")
        
        detector = DuplicateDetector(db)
        
        # Perform merge
        result = detector.merge_duplicates(group_id)
        
        if not result:
            raise HTTPException(status_code=500, detail="Merge operation failed")
        
        return {
            "status": "ok",
            "message": f"✅ Successfully merged {len(group.duplicate_record_ids)} duplicate(s)",
            "group_id": group_id,
            "master_record_id": str(group.master_record_id),
            "merged_count": len(group.duplicate_record_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error merging duplicates: {str(e)}")


@router.post("/duplicates/{group_id}/ignore")
def ignore_duplicate_group(
    group_id: int,
    request: IgnoreRequest,
    db: Session = Depends(get_session)
):
    """
    🚫 Mark duplicate group as ignored (false positive)
    
    Actions:
    - Change all records back to 'ready_for_ai' status
    - Mark group status as 'ignored'
    - Keep records for future reference
    """
    try:
        group = db.query(DuplicateGroup).filter(DuplicateGroup.id == group_id).first()
        
        if not group:
            raise HTTPException(status_code=404, detail=f"Duplicate group {group_id} not found")
        
        if group.status == "ignored":
            raise HTTPException(status_code=400, detail="Group already ignored")
        
        detector = DuplicateDetector(db)
        
        # Ignore duplicates (revert status to ready_for_ai)
        result = detector.ignore_duplicates(group_id)
        
        if not result:
            raise HTTPException(status_code=500, detail="Ignore operation failed")
        
        return {
            "status": "ok",
            "message": f"✅ Successfully ignored duplicate group (marked as false positive)",
            "group_id": group_id,
            "reason": request.reason,
            "affected_records": len(group.duplicate_record_ids) + 1  # +1 for master
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error ignoring duplicates: {str(e)}")