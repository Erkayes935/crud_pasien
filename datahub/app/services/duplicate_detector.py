"""
Duplicate Detector Service - Deteksi Exact & Fuzzy Duplicates
Menggunakan hash matching dan RapidFuzz untuk similarity scoring
"""
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from rapidfuzz import fuzz
from ..models.core import DataHubRecord, DuplicateGroup
from ..services.hasher import generate_content_hash, generate_fingerprint
from ..services.logger import log_event


class DuplicateDetector:
    """
    Service untuk deteksi duplicate records.
    
    Strategi deteksi:
    1. Exact Match - Pakai content_hash (super cepat via index)
    2. Fuzzy Match - Pakai similarity_fingerprint dengan RapidFuzz
    
    Threshold default: 85% (configurable)
    """
    
    def __init__(self, db: Session, similarity_threshold: int = 85):
        """
        Initialize detector.
        
        Args:
            db: SQLAlchemy session
            similarity_threshold: Minimum similarity score (0-100) untuk flag duplicate
        """
        self.db = db
        self.similarity_threshold = similarity_threshold
    
    def check_duplicate(self, new_record: DataHubRecord) -> Optional[Dict]:
        """
        Check apakah new_record adalah duplicate.
        
        FASE 2.6 UPDATE: Selalu return similarity info, even if < threshold!
        - >= 85%: Duplicate detected, create group
        - < 85%: NOT duplicate, tapi tetap record similarity info
        
        Returns:
            None jika tidak ada record untuk dicompare
            Dict dengan similarity info: {
                "type": "exact" atau "fuzzy" atau "no_duplicate",
                "match": DataHubRecord yang paling mirip (or None),
                "score": similarity score (0-100),
                "confidence": confidence level or None,
                "is_duplicate": True/False (based on threshold)
            }
        """
        # Step 1: Check exact duplicate via content_hash
        if new_record.content_hash:
            exact_match = self._check_exact_duplicate(new_record)
            if exact_match:
                return {
                    "type": "exact",
                    "match": exact_match,
                    "score": 100,
                    "confidence": "exact",
                    "is_duplicate": True  # Always duplicate
                }
        
        # Step 2: Check fuzzy duplicate via similarity_fingerprint
        if new_record.similarity_fingerprint:
            fuzzy_result = self._check_fuzzy_duplicate(new_record)
            if fuzzy_result:
                return fuzzy_result
        
        return None
    
    def _check_exact_duplicate(self, new_record: DataHubRecord) -> Optional[DataHubRecord]:
        """
        Check exact duplicate menggunakan content_hash.
        Super cepat karena pakai index.
        """
        existing = self.db.query(DataHubRecord).filter(
            DataHubRecord.content_hash == new_record.content_hash,
            DataHubRecord.hospital_id == new_record.hospital_id,
            DataHubRecord.id != new_record.id  # Exclude diri sendiri
        ).first()
        
        return existing
    
    def _check_fuzzy_duplicate(self, new_record: DataHubRecord) -> Optional[Dict]:
        """
        Check fuzzy duplicate menggunakan RapidFuzz.
        
        Strategy:
        1. Filter kandidat: hospital sama + tanggal masuk sama (narrow down search)
        2. Compare fingerprint pakai RapidFuzz
        3. Return jika score >= threshold
        """
        # Get tanggal_masuk dari json_data untuk filtering
        new_tanggal = new_record.json_data.get("tanggal_masuk", "")
        
        # Ambil kandidat (hospital sama, tanggal masuk sama)
        # Limit 100 untuk performa
        candidates = self.db.query(DataHubRecord).filter(
            DataHubRecord.hospital_id == new_record.hospital_id,
            DataHubRecord.id != new_record.id,
            DataHubRecord.similarity_fingerprint.isnot(None)
        ).limit(100).all()
        
        # Filter candidates dengan tanggal sama (di Python karena json_data)
        if new_tanggal:
            candidates = [
                c for c in candidates 
                if c.json_data.get("tanggal_masuk") == new_tanggal
            ]
        
        # Compare dengan RapidFuzz
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            # Hitung similarity score
            score = fuzz.ratio(
                new_record.similarity_fingerprint,
                candidate.similarity_fingerprint
            )
            
            # Track best match (even if < threshold)
            if score > best_score:
                best_score = score
                best_match = candidate
        
        # FASE 2.6: Return similarity info even if < threshold
        if best_match:
            is_duplicate = best_score >= self.similarity_threshold
            confidence = self.classify_confidence(best_score) if is_duplicate else None
            
            return {
                "type": "fuzzy",
                "match": best_match,
                "score": best_score,
                "confidence": confidence,
                "is_duplicate": is_duplicate  # True if >= threshold
            }
        
        return None
    
    def classify_confidence(self, score: float) -> str:
        """
        Classify duplicate confidence level berdasarkan similarity score.
        
        Classification:
        - exact (100%): Hash collision atau identical text
        - very_high (98-99%): Hampir pasti duplicate (auto-merge recommended)
        - high (93-97%): Kemungkinan besar duplicate (auto-merge safe)
        - medium (88-92%): Perlu review manual (flagging)
        - low (85-87%): Suspicious tapi tidak yakin (manual verification required)
        
        Args:
            score: Similarity score dari RapidFuzz (0-100)
            
        Returns:
            Confidence level string
        """
        if score == 100:
            return "exact"
        elif score >= 98:
            return "very_high"
        elif score >= 93:
            return "high"
        elif score >= 88:
            return "medium"
        else:
            return "low"
    
    def create_duplicate_group(
        self, 
        master_record_id: str, 
        duplicate_record_ids: List[str], 
        similarity_score: float,
        duplicate_type: str
    ) -> DuplicateGroup:
        """
        Buat grup duplicate di database.
        
        Args:
            master_record_id: Record ID yang dianggap master
            duplicate_record_ids: List of duplicate record IDs
            similarity_score: Score similarity (0-100)
            duplicate_type: "exact" atau "fuzzy"
            
        Returns:
            DuplicateGroup object
        """
        group = DuplicateGroup(
            master_record_id=master_record_id,
            duplicate_record_ids=duplicate_record_ids,
            similarity_score=similarity_score,
            duplicate_type=duplicate_type,
            status="pending"
        )
        
        self.db.add(group)
        self.db.flush()  # Get ID
        
        return group
    
    def mark_as_duplicate(self, record: DataHubRecord, duplicate_type: str):
        """
        Mark record sebagai duplicate (update status).
        
        Args:
            record: DataHubRecord to mark
            duplicate_type: "exact" atau "fuzzy"
        """
        if duplicate_type == "exact":
            record.status = "duplicate_exact"
        else:
            record.status = "possible_duplicate"
        
        self.db.flush()
    
    def get_pending_duplicates(self, limit: int = 50) -> List[DuplicateGroup]:
        """
        Get semua duplicate groups yang masih pending.
        
        Returns:
            List of DuplicateGroup
        """
        return self.db.query(DuplicateGroup).filter(
            DuplicateGroup.status == "pending"
        ).order_by(DuplicateGroup.created_at.desc()).limit(limit).all()
    
    def merge_duplicates(self, group_id: int) -> bool:
        """
        Merge duplicate records (mark as merged).
        
        Logic:
        - Keep master record
        - Mark duplicate records as merged
        - Update group status
        
        Args:
            group_id: ID dari DuplicateGroup
            
        Returns:
            bool: Success or not
        """
        group = self.db.query(DuplicateGroup).get(group_id)
        if not group:
            return False
        
        # Update duplicate records status
        for dup_id in group.duplicate_record_ids:
            record = self.db.query(DataHubRecord).filter_by(record_id=dup_id).first()
            if record:
                record.status = "merged"
        
        # Update group status
        group.status = "merged"
        self.db.commit()
        
        # Log event
        log_event(
            self.db, 
            group.master_record_id, 
            "duplicate_detector", 
            "info",
            f"Merged {len(group.duplicate_record_ids)} duplicate records"
        )
        
        return True
    
    def ignore_duplicates(self, group_id: int) -> bool:
        """
        Ignore duplicate group (bukan duplicate setelah review).
        
        Args:
            group_id: ID dari DuplicateGroup
            
        Returns:
            bool: Success or not
        """
        group = self.db.query(DuplicateGroup).get(group_id)
        if not group:
            return False
        
        # Update duplicate records status kembali ke ready_for_ai
        for dup_id in group.duplicate_record_ids:
            record = self.db.query(DataHubRecord).filter_by(record_id=dup_id).first()
            if record and record.status in ["duplicate_exact", "possible_duplicate"]:
                record.status = "ready_for_ai"
        
        # Update group status
        group.status = "ignored"
        self.db.commit()
        
        # Log event
        log_event(
            self.db,
            group.master_record_id,
            "duplicate_detector",
            "info",
            f"Ignored duplicate group (not actually duplicate)"
        )
        
        return True
    
    def get_duplicate_statistics(self) -> Dict:
        """
        Get statistik duplicate detection.
        
        Returns:
            dict: {
                "total_groups": int,
                "pending": int,
                "merged": int,
                "ignored": int,
                "exact_duplicates": int,
                "fuzzy_duplicates": int
            }
        """
        total = self.db.query(DuplicateGroup).count()
        pending = self.db.query(DuplicateGroup).filter_by(status="pending").count()
        merged = self.db.query(DuplicateGroup).filter_by(status="merged").count()
        ignored = self.db.query(DuplicateGroup).filter_by(status="ignored").count()
        exact = self.db.query(DuplicateGroup).filter_by(duplicate_type="exact").count()
        fuzzy = self.db.query(DuplicateGroup).filter_by(duplicate_type="fuzzy").count()
        
        return {
            "total_groups": total,
            "pending": pending,
            "merged": merged,
            "ignored": ignored,
            "exact_duplicates": exact,
            "fuzzy_duplicates": fuzzy
        }
