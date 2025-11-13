"""
FASE 1.2: Anonymizer Service

Anonymize PHI (Personal Health Information) data untuk Manual & Excel input.
Gateway input sudah anonymous, jadi skip.

Fitur:
- Remove sensitive fields (nama_pasien, NIK, alamat, dll)
- Generate atau reuse patient_uuid
- Store mapping di patient_uuid_map table (hashed, bukan plaintext!)
- Consistent UUID untuk pasien yang sama
"""

import hashlib
import uuid
from typing import Dict, Optional
from sqlalchemy.orm import Session
from ..models.core import PatientUUIDMap


class Anonymizer:
    """
    Service untuk anonymize data patient.
    
    Security:
    - TIDAK simpan nama/NIK plaintext
    - Hanya simpan SHA256 hash
    - UUID bersifat one-way (tidak bisa di-reverse)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def _generate_hash(self, value: str) -> str:
        """
        Generate SHA256 hash dari string.
        
        Args:
            value: String yang akan di-hash (nama_pasien atau NIK)
        
        Returns:
            64-character hex string (SHA256 hash)
        """
        if not value:
            return None
        
        # Convert to string first (in case it's int/float from pandas)
        value_str = str(value)
        
        # Normalize: lowercase, strip whitespace
        normalized = value_str.lower().strip()
        
        # Generate SHA256 hash
        hash_object = hashlib.sha256(normalized.encode('utf-8'))
        return hash_object.hexdigest()
    
    def _get_or_create_patient_uuid(
        self, 
        name: Optional[str], 
        nik: Optional[str],
        source_type: str,
        source_record_id: Optional[str] = None
    ) -> str:
        """
        Get existing patient UUID atau create new.
        
        Lookup strategy:
        1. Cari by nik_hash (paling unik)
        2. Jika tidak ada, cari by name_hash
        3. Jika tidak ada, buat UUID baru
        
        Args:
            name: Nama pasien (akan di-hash)
            nik: NIK pasien (akan di-hash)
            source_type: "manual" atau "excel"
            source_record_id: Reference ke record ID (optional)
        
        Returns:
            patient_uuid string (UUID format)
        """
        # Kalau ga ada PHI, generate random UUID
        if not name and not nik:
            return str(uuid.uuid4())
        
        # Generate hashes
        name_hash = self._generate_hash(name) if name else None
        nik_hash = self._generate_hash(nik) if nik else None
        
        # Strategy 1: Lookup by NIK hash (most unique)
        if nik_hash:
            existing = self.db.query(PatientUUIDMap).filter(
                PatientUUIDMap.nik_hash == nik_hash
            ).first()
            
            if existing:
                return existing.patient_uuid
        
        # Strategy 2: Lookup by name hash (if NIK not available)
        if name_hash and not nik_hash:
            existing = self.db.query(PatientUUIDMap).filter(
                PatientUUIDMap.name_hash == name_hash
            ).first()
            
            if existing:
                return existing.patient_uuid
        
        # Strategy 3: Create new UUID mapping
        patient_uuid = str(uuid.uuid4())
        
        mapping = PatientUUIDMap(
            patient_uuid=patient_uuid,
            source_type=source_type,
            source_record_id=source_record_id,
            name_hash=name_hash,
            nik_hash=nik_hash
        )
        
        self.db.add(mapping)
        self.db.flush()  # Get ID without committing
        
        return patient_uuid
    
    def anonymize_record(
        self, 
        data: Dict, 
        source_type: str,
        source_record_id: Optional[str] = None
    ) -> Dict:
        """
        Anonymize satu record data.
        
        Process:
        1. Extract PHI fields (nama, NIK, dll)
        2. Generate atau reuse patient_uuid
        3. Remove PHI fields dari data
        4. Add patient_uuid ke data
        
        Args:
            data: Dictionary dengan PHI fields
            source_type: "manual" atau "excel"
            source_record_id: Reference ke record ID (optional)
        
        Returns:
            Dictionary anonymous (PHI removed, patient_uuid added)
        
        Example:
            Input:
            {
                "nama_pasien": "Budi Santoso",
                "nik": "3374012345678901",
                "diagnosis": "Pneumonia",
                ...
            }
            
            Output:
            {
                "patient_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "diagnosis": "Pneumonia",
                ...
            }
        """
        # Get or create patient UUID
        patient_uuid = self._get_or_create_patient_uuid(
            name=data.get("nama_pasien"),
            nik=data.get("nik"),
            source_type=source_type,
            source_record_id=source_record_id
        )
        
        # Copy data untuk avoid mutation
        anonymized = data.copy()
        
        # PHI fields to remove (sesuai HIPAA/GDPR guidelines)
        phi_fields = [
            "nama_pasien",      # Patient name
            "nik",              # National ID
            "alamat",           # Address
            "no_telepon",       # Phone number
            "email",            # Email
            "nama_keluarga",    # Family name
            "kontak_darurat",   # Emergency contact
            "no_bpjs",          # Insurance number (could be PHI)
            "no_rm",            # Medical record number (could be PHI)
        ]
        
        # Remove PHI fields
        for field in phi_fields:
            if field in anonymized:
                del anonymized[field]
        
        # Add anonymous identifier
        anonymized["patient_uuid"] = patient_uuid
        
        return anonymized
    
    def should_anonymize(self, data: Dict, source_type: str) -> bool:
        """
        Check apakah data perlu di-anonymize.
        
        Rules:
        - Gateway input: SKIP (sudah anonymous dari gateway)
        - Manual input: ANONYMIZE jika ada PHI
        - Excel input: ANONYMIZE jika ada PHI
        
        Args:
            data: Data dictionary
            source_type: "manual", "excel", atau "gateway"
        
        Returns:
            True jika perlu anonymize, False jika skip
        """
        # Gateway sudah anonymous, skip
        if source_type == "gateway":
            return False
        
        # Check apakah ada PHI fields
        phi_fields = ["nama_pasien", "nik", "alamat", "no_telepon", "email"]
        has_phi = any(data.get(field) for field in phi_fields)
        
        return has_phi
    
    def get_patient_stats(self) -> Dict:
        """
        Get statistik anonymization.
        
        Returns:
            Dictionary dengan statistik:
            - total_patients: Total unique patients
            - from_manual: Patients dari manual input
            - from_excel: Patients dari excel upload
        """
        total = self.db.query(PatientUUIDMap).count()
        
        manual = self.db.query(PatientUUIDMap).filter(
            PatientUUIDMap.source_type == "manual"
        ).count()
        
        excel = self.db.query(PatientUUIDMap).filter(
            PatientUUIDMap.source_type == "excel"
        ).count()
        
        return {
            "total_patients": total,
            "from_manual": manual,
            "from_excel": excel
        }
    
    def verify_anonymization(self, data: Dict) -> Dict:
        """
        Verify bahwa data sudah anonymous (no PHI).
        
        Args:
            data: Data dictionary untuk di-check
        
        Returns:
            Dictionary dengan hasil verifikasi:
            - is_anonymous: True/False
            - phi_found: List of PHI fields yang masih ada
            - has_patient_uuid: True/False
        """
        phi_fields = ["nama_pasien", "nik", "alamat", "no_telepon", "email"]
        phi_found = [field for field in phi_fields if data.get(field)]
        
        return {
            "is_anonymous": len(phi_found) == 0 and "patient_uuid" in data,
            "phi_found": phi_found,
            "has_patient_uuid": "patient_uuid" in data
        }
