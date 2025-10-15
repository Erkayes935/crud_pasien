from sqlalchemy.orm import Session
from sqlalchemy import or_  # ✅ penting! biar filter or_() jalan
from backend import models


# ==============================
# BAGIAN: CRUD KLAIM UTAMA
# ==============================

def get_claim(db: Session, claim_id: int):
    """Ambil satu klaim berdasarkan ID"""
    return db.query(models.Claim).filter(models.Claim.id == claim_id).first()


def get_claims(
    db: Session,
    status=None,
    tanggal_kunjungan=None,
    patient_name=None,
    jenis_kunjungan=None,
    claim_id=None,
    visit_id=None,
):
    """Ambil daftar klaim dengan filter opsional"""
    query = db.query(models.Claim)

    if status:
        query = query.filter(models.Claim.status == status)
    if claim_id:
        query = query.filter(models.Claim.id == claim_id)
    if visit_id:
        query = query.filter(models.Claim.visit_id == visit_id)
    # Tambahkan filter lain sesuai kebutuhan
    return query.all()


def delete_claim(db: Session, id: int):
    """Hapus klaim"""
    claim = db.query(models.Claim).get(id)
    if claim:
        db.delete(claim)
        db.commit()


def export_claims(db: Session, status=None, start_date=None, end_date=None):
    """Ambil semua klaim untuk diexport"""
    query = db.query(models.Claim)
    if status:
        query = query.filter(models.Claim.status == status)
    if start_date and end_date:
        query = query.filter(models.Claim.created_at.between(start_date, end_date))
    return query.all()


# ==============================
# BAGIAN: CATATAN (NOTES)
# ==============================

def create_note(
    db: Session,
    claim_id: int,
    item_id: int | None,
    user_id: int,
    role: str,
    note_text: str,
    parent_id: int | None = None,
    field_key: str | None = None,
    stage: str | None = None,
    timestamp=None,
    origin_item_id: int | None = None,  # ✅ tambahkan dukungan kolom baru
):
    """Buat catatan baru untuk klaim"""
    note = models.ClaimNote(
        claim_id=claim_id,
        item_id=item_id,
        user_id=user_id,
        role=role,
        note_text=note_text,
        parent_id=parent_id,
        field_key=field_key,
        stage=stage,
        timestamp=timestamp,
        origin_item_id=origin_item_id  # ✅ ikut disimpan
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_notes(db: Session, claim_id: int, stage: str | None = None, item_id: int | None = None):
    """Ambil semua note berdasarkan klaim + filter opsional"""
    query = db.query(models.ClaimNote).filter(models.ClaimNote.claim_id == claim_id)
    if stage:
        query = query.filter(models.ClaimNote.stage == stage)
    if item_id:
        # 🔍 tampilkan semua note yang terkait (baik item_id atau origin_item_id)
        query = query.filter(
            or_(
                models.ClaimNote.item_id == item_id,
                models.ClaimNote.origin_item_id == item_id
            )
        )
    return query.all()


def delete_note(db: Session, note_id: int):
    """Hapus satu note"""
    note = db.query(models.ClaimNote).get(note_id)
    if note:
        db.delete(note)
        db.commit()
