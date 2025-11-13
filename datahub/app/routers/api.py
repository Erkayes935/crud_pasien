"""
API Router for Web AI Claim Integration
========================================
Provides REST API endpoints for Web AI Claim to consume Data Hub data.

Key Features:
- GET /api/records: Fetch multiple records with filters (status, pagination)
- GET /api/records/{id}: Get single record detail
- POST /api/records/{id}/status: Update record status after AI processing

Note: Web AI Claim has its own separate database.
      This API only provides data, doesn't share database.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime
import logging

from app.db import get_session
from app.models.core import DataHubRecord
from pydantic import BaseModel


router = APIRouter(prefix="/api", tags=["API"])
logger = logging.getLogger(__name__)


# ============================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================

class StatusUpdateRequest(BaseModel):
    """Request body for updating record status after AI processing"""
    status: str
    ai_result_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    notes: Optional[str] = None


class RecordResponse(BaseModel):
    """Response schema for single record"""
    id: int
    record_id: str
    hospital_id: str
    source_id: int
    status: str
    json_data: dict
    content_hash: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RecordListResponse(BaseModel):
    """Response schema for list of records with pagination"""
    total: int
    page: int
    page_size: int
    records: List[RecordResponse]


# ============================================================
# API ENDPOINTS
# ============================================================

@router.get("/records", response_model=RecordListResponse)
async def get_records(
    status: Optional[str] = Query(None, description="Filter by status (e.g., 'ready_for_ai', 'processed')"),
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    page: int = Query(1, ge=1, description="Page number (starting from 1)"),
    page_size: int = Query(100, ge=1, le=500, description="Number of records per page (max 500)"),
    db: Session = Depends(get_session)
):
    """
    Fetch multiple records with filters and pagination.
    
    **Use Case:** Web AI Claim fetches records ready for AI processing
    
    **Example:**
    ```
    GET /api/records?status=ready_for_ai&page=1&page_size=100
    ```
    
    **Returns:**
    - List of records matching filters
    - Total count and pagination info
    """
    try:
        # Build query with filters
        query = db.query(DataHubRecord)
        
        filters = []
        if status:
            filters.append(DataHubRecord.status == status)
        if hospital_id:
            filters.append(DataHubRecord.hospital_id == hospital_id)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        records = query.order_by(DataHubRecord.created_at.desc())\
                      .offset(offset)\
                      .limit(page_size)\
                      .all()
        
        # Log the API request
        logger.info(
            f"API: Fetched {len(records)} records (page {page}/{total}, "
            f"status={status}, hospital_id={hospital_id})"
        )
        
        return RecordListResponse(
            total=total,
            page=page,
            page_size=page_size,
            records=[RecordResponse.model_validate(r) for r in records]
        )
    
    except Exception as e:
        logger.error(f"API Error fetching records: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching records: {str(e)}")


@router.get("/records/{record_id}", response_model=RecordResponse)
async def get_record_by_id(
    record_id: int,
    db: Session = Depends(get_session)
):
    """
    Get single record by ID.
    
    **Use Case:** Web AI Claim fetches full details for a specific record
    
    **Example:**
    ```
    GET /api/records/123
    ```
    
    **Returns:**
    - Full record details including json_data
    - 404 if record not found
    """
    try:
        record = db.query(DataHubRecord)\
                  .filter(DataHubRecord.id == record_id)\
                  .first()
        
        if not record:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
        
        logger.info(f"API: Fetched record {record_id}")
        
        return RecordResponse.model_validate(record)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Error fetching record {record_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching record: {str(e)}")


@router.post("/records/{record_id}/status")
async def update_record_status(
    record_id: int,
    request: StatusUpdateRequest,
    db: Session = Depends(get_session)
):
    """
    Update record status after AI processing.
    
    **Use Case:** Web AI Claim updates status after sending to Core Engine
    
    **Example:**
    ```
    POST /api/records/123/status
    {
        "status": "processed",
        "ai_result_id": "ai-result-456",
        "processed_at": "2024-01-15T10:30:00",
        "notes": "Successfully processed by Core Engine"
    }
    ```
    
    **Valid Status Values:**
    - `pending`: Initial status
    - `ready_for_ai`: Ready for AI processing
    - `processing`: Currently being processed
    - `processed`: Successfully processed
    - `failed`: Processing failed
    
    **Returns:**
    - Updated record with new status
    - 404 if record not found
    """
    try:
        record = db.query(DataHubRecord)\
                  .filter(DataHubRecord.id == record_id)\
                  .first()
        
        if not record:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
        
        # Update status
        old_status = record.status
        record.status = request.status
        record.updated_at = datetime.utcnow()
        
        # Update json_data with additional info
        if not record.json_data:
            record.json_data = {}
        
        if request.ai_result_id:
            record.json_data["ai_result_id"] = request.ai_result_id
        if request.processed_at:
            record.json_data["processed_at"] = request.processed_at.isoformat()
        if request.notes:
            record.json_data["processing_notes"] = request.notes
        
        db.commit()
        db.refresh(record)
        
        logger.info(
            f"API: Updated record {record_id} status: {old_status} → {request.status} "
            f"(ai_result_id={request.ai_result_id})"
        )
        
        return {
            "success": True,
            "message": f"Record {record_id} status updated to '{request.status}'",
            "record": RecordResponse.model_validate(record)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"API Error updating record {record_id} status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating status: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    **Example:**
    ```
    GET /api/health
    ```
    
    **Returns:**
    - API status and timestamp
    """
    return {
        "status": "healthy",
        "service": "Data Hub API",
        "timestamp": datetime.utcnow().isoformat()
    }
