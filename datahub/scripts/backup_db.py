"""
Database Backup Script
Untuk backup data sebelum migration atau perubahan schema
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from app.db import SessionLocal
from app.models.core import DataHubSource, DataHubRecord, AuditLog
import json

def backup_database():
    """Backup semua data ke JSON files"""
    db = SessionLocal()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backups/backup_{timestamp}"
    
    # Create backup directory
    os.makedirs(backup_dir, exist_ok=True)
    
    try:
        print(f"🔄 Starting backup to: {backup_dir}")
        
        # Backup DataHubSource
        sources = db.query(DataHubSource).all()
        sources_data = [{
            "id": s.id,
            "type": s.type,
            "filename": s.filename,
            "uploader": s.uploader,
            "created_at": s.created_at.isoformat() if s.created_at else None
        } for s in sources]
        
        with open(f"{backup_dir}/data_hub_sources.json", "w") as f:
            json.dump(sources_data, f, indent=2)
        print(f"  ✅ Backed up {len(sources_data)} sources")
        
        # Backup DataHubRecord
        records = db.query(DataHubRecord).all()
        records_data = [{
            "id": r.id,
            "record_id": r.record_id,
            "hospital_id": r.hospital_id,
            "source_id": r.source_id,
            "json_data": r.json_data,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in records]
        
        with open(f"{backup_dir}/data_hub_records.json", "w") as f:
            json.dump(records_data, f, indent=2)
        print(f"  ✅ Backed up {len(records_data)} records")
        
        # Backup AuditLog
        logs = db.query(AuditLog).all()
        logs_data = [{
            "id": l.id,
            "record_id": l.record_id,
            "source": l.source,
            "level": l.level,
            "message": l.message,
            "created_at": l.created_at.isoformat() if l.created_at else None
        } for l in logs]
        
        with open(f"{backup_dir}/audit_logs.json", "w") as f:
            json.dump(logs_data, f, indent=2)
        print(f"  ✅ Backed up {len(logs_data)} audit logs")
        
        # Create backup info
        info = {
            "backup_time": timestamp,
            "total_sources": len(sources_data),
            "total_records": len(records_data),
            "total_logs": len(logs_data)
        }
        
        with open(f"{backup_dir}/backup_info.json", "w") as f:
            json.dump(info, f, indent=2)
        
        print(f"\n✅ Backup completed successfully!")
        print(f"📁 Backup location: {backup_dir}")
        
        return backup_dir
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    backup_database()
