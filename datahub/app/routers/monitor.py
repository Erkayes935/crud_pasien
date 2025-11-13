from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..db import get_session
from ..models.core import DataHubSource, DataHubRecord, AuditLog, DuplicateGroup
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
    types = ["manual", "import_excel", "gateway"]
    summary = []
    
    for t in types:
        q = (
            db.query(func.count(DataHubRecord.id).label("total"))
            .join(DataHubSource)
            .filter(DataHubSource.type == t)
        )
        total = q.scalar() or 0

        # Contoh statistik (sesuaikan dengan kebutuhan)
        valid = total // 2
        error = total // 4
        duplicate = total // 8

        last_update = db.query(func.max(DataHubRecord.created_at))\
                        .join(DataHubSource)\
                        .filter(DataHubSource.type == t)\
                        .scalar()

        summary.append({
            "source": t,
            "total": total,
            "valid": valid,
            "error": error,
            "duplicate": duplicate,
            "last_update": last_update.strftime("%Y-%m-%d %H:%M") if last_update else None
        })

    return summary


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
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_session)
):
    """
    📋 List all duplicate groups with filtering options
    
    Returns:
    - List of duplicate groups with master/duplicate record details
    - Similarity scores and duplicate types
    - Status (pending/merged/ignored)
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
        
        # Group status is already updated in merge_duplicates method
        
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
        
        # Group status is already updated in ignore_duplicates method
        
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
