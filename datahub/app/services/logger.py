from ..models.core import AuditLog

def log_event(db, record_id, source, level, message):
    log = AuditLog(record_id=record_id, source=source, level=level, message=message)
    db.add(log)
    db.commit()
