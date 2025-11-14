"""
FASE 1.2: Anonymizer Service - DataHub Version

Anonymize PHI (Personal Health Information) data untuk Manual & Excel input.
Gateway input sudah anonymous, jadi skip.

Fitur:
- Mask nama (3 huruf depan per kata)
- Mask NIK (4 digit terakhir)
- Mask no HP (4 digit terakhir)
- Generate atau reuse patient_uuid
- Store mapping di patient_uuid_map table (hashed, bukan plaintext!)
- Tetap simpan tanggal lahir, alamat, email (tidak diubah)
"""

import hashlib
import uuid
import re
from typing import Dict, Optional
from sqlalchemy.orm import Session
from ..models.core import PatientUUIDMap


class Anonymizer:
    """
    Service untuk anonymize data patient di DataHub.
    
    Security:
    - Mask nama, NIK, no HP tapi TETAP SIMPAN (bukan hapus)
    - Hash untuk UUID mapping
    - Tanggal lahir, alamat, email: TETAP ASLI
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # =====================================================================
    # MASKING FUNCTIONS (sama seperti Gateway)
    # =====================================================================
    
    def _mask_name(self, name: str) -> str:
        """
        Mask nama: tampilkan 3 huruf depan per kata, sisanya asterisk.
        
        Input:  "Septian Ridho"
        Output: "Sep**** Rid**"
        """
        if not name:
            return ""
        
        parts = name.split()
        masked = []
        
        for p in parts:
            if len(p) == 0:
                continue
            
            # Tampilkan 3 huruf depan (atau kurang jika nama pendek)
            visible = min(3, len(p))
            masked_part = p[:visible] + "*" * max(0, len(p) - visible)
            masked.append(masked_part)
        
        return " ".join(masked)
    
    def _mask_nik(self, nik: str) -> str:
        """
        Tampilkan 4 digit terakhir saja.
        
        Input:  "3578123456789012"
        Output: "************3456"
        """
        if not nik:
            return ""
        
        # Convert to string & extract only digits
        nik_str = str(nik)
        nik_clean = ''.join(filter(str.isdigit, nik_str))
        
        if not nik_clean:
            return ""
        
        # Minimal 4 digit untuk di-mask
        if len(nik_clean) < 4:
            return "*" * len(nik_clean)
        
        return "*" * (len(nik_clean) - 4) + nik_clean[-4:]
    
    def _mask_phone(self, phone: str) -> str:
        """
        Masking nomor HP: tampilkan 4 digit terakhir saja.
        
        Input:  "081234567890"
        Output: "********7890"
        """
        if not phone:
            return ""
        
        # Convert to string & extract only digits
        phone_str = str(phone)
        phone_clean = ''.join(filter(str.isdigit, phone_str))
        
        if not phone_clean:
            return ""
        
        # Minimal 4 digit untuk di-mask
        if len(phone_clean) < 4:
            return "*" * len(phone_clean)
        
        return "*" * (len(phone_clean) - 4) + phone_clean[-4:]
    
    # =====================================================================
    # HASH FUNCTIONS (untuk UUID mapping)
    # =====================================================================
    
    def _generate_hash(self, value: str) -> str:
        """
        Generate SHA256 hash dari string ASLI (SEBELUM mask).
        
        Args:
            value: String yang akan di-hash (nama_pasien atau NIK ASLI)
        
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
    
    # =====================================================================
    # UUID MANAGEMENT
    # =====================================================================
    
    def _get_or_create_patient_uuid(
        self, 
        name: Optional[str], 
        nik: Optional[str],
        hospital_id: str,
        source_type: str,
        source_record_id: Optional[str] = None
    ) -> str:
        """
        Get existing patient UUID atau create new.
        
        PENTING: Hash menggunakan data ASLI (sebelum mask)!
        
        Lookup strategy:
        1. Cari by nik_hash + hospital_id (paling unik)
        2. Jika tidak ada, cari by name_hash + hospital_id
        3. Jika tidak ada, buat UUID baru
        
        Args:
            name: Nama pasien ASLI (akan di-hash)
            nik: NIK pasien ASLI (akan di-hash)
            hospital_id: ID rumah sakit
            source_type: "manual" atau "excel"
            source_record_id: Reference ke record ID (optional)
        
        Returns:
            patient_uuid string (UUID format)
        """
        # Kalau ga ada PHI, generate random UUID
        if not name and not nik:
            return str(uuid.uuid4())
        
        # Generate hashes dari data ASLI
        name_hash = self._generate_hash(name) if name else None
        nik_hash = self._generate_hash(nik) if nik else None
        
        # Strategy 1: Lookup by NIK hash + hospital_id (most unique)
        if nik_hash:
            existing = self.db.query(PatientUUIDMap).filter(
                PatientUUIDMap.nik_hash == nik_hash,
                PatientUUIDMap.hospital_id == hospital_id
            ).first()
            
            if existing:
                return existing.patient_uuid
        
        # Strategy 2: Lookup by name hash + hospital_id (if NIK not available)
        if name_hash and not nik_hash:
            existing = self.db.query(PatientUUIDMap).filter(
                PatientUUIDMap.name_hash == name_hash,
                PatientUUIDMap.hospital_id == hospital_id
            ).first()
            
            if existing:
                return existing.patient_uuid
        
        # Strategy 3: Create new UUID mapping
        patient_uuid = str(uuid.uuid4())
        
        mapping = PatientUUIDMap(
            patient_uuid=patient_uuid,
            source_type=source_type,
            hospital_id=hospital_id,
            source_record_id=source_record_id,
            name_hash=name_hash,
            nik_hash=nik_hash
        )
        
        self.db.add(mapping)
        self.db.flush()  # Get ID without committing
        
        return patient_uuid
    
    # =====================================================================
    # MAIN ANONYMIZATION FUNCTION
    # =====================================================================
    
    def anonymize_record(
        self, 
        data: Dict, 
        source_type: str,
        source_record_id: Optional[str] = None
    ) -> Dict:
        """
        Anonymize satu record data (DataHub version).
        
        Process:
        1. Extract PHI fields (nama, NIK, dll) - DATA ASLI
        2. Generate hash dari data ASLI (untuk UUID matching)
        3. Generate atau reuse patient_uuid
        4. MASK nama, NIK, no HP (bukan hapus!)
        5. TETAP simpan tanggal lahir, alamat, email (tidak diubah)
        6. Add patient_uuid ke data
        
        Args:
            data: Dictionary dengan PHI fields
            source_type: "manual" atau "excel"
            source_record_id: Reference ke record ID (optional)
        
        Returns:
            Dictionary dengan PHI yang sudah di-mask
        
        Example:
            Input:
            {
                "nama": "Septian Ridho",
                "no_ktp": "3578123456789012",
                "no_hp": "081234567890",
                "tanggal_lahir": "1990-05-15",
                "alamat": "Jl. Kenari 123, Surabaya",
                "email": "septian@email.com",
                "diagnosis": "Pneumonia",
                ...
            }
            
            Output:
            {
                "nama": "Sep**** Rid**",                  # MASKED
                "no_ktp": "************3456",             # MASKED
                "no_hp": "********7890",                  # MASKED
                "tanggal_lahir": "1990-05-15",            # ASLI (tidak diubah)
                "alamat": "Jl. Kenari 123, Surabaya",     # ASLI (tidak diubah)
                "email": "septian@email.com",             # ASLI (tidak diubah)
                "patient_uuid": "550e8400-...",           # ADDED
                "diagnosis": "Pneumonia",
                ...
            }
        """
        # Copy data untuk avoid mutation
        anonymized = data.copy()
        
        # Extract data ASLI sebelum mask (untuk UUID generation)
        original_name = data.get("nama") or data.get("nama_pasien")
        original_nik = data.get("no_ktp") or data.get("nik")
        hospital_id = data.get("hospital_id", "unknown")
        
        # Get or create patient UUID (menggunakan hash dari data ASLI)
        patient_uuid = self._get_or_create_patient_uuid(
            name=original_name,
            nik=original_nik,
            hospital_id=hospital_id,
            source_type=source_type,
            source_record_id=source_record_id
        )
        
        # ✅ MASK sensitive fields (tapi tetap simpan!)
        
        # Nama
        if "nama" in anonymized and anonymized["nama"]:
            anonymized["nama"] = self._mask_name(anonymized["nama"])
        elif "nama_pasien" in anonymized and anonymized["nama_pasien"]:
            anonymized["nama"] = self._mask_name(anonymized["nama_pasien"])
            del anonymized["nama_pasien"]  # Rename to 'nama'
        
        # NIK
        if "no_ktp" in anonymized and anonymized["no_ktp"]:
            anonymized["no_ktp"] = self._mask_nik(anonymized["no_ktp"])
        elif "nik" in anonymized and anonymized["nik"]:
            anonymized["no_ktp"] = self._mask_nik(anonymized["nik"])
            del anonymized["nik"]  # Rename to 'no_ktp'
        
        # No HP
        if "no_hp" in anonymized and anonymized["no_hp"]:
            anonymized["no_hp"] = self._mask_phone(anonymized["no_hp"])
        elif "no_telepon" in anonymized and anonymized["no_telepon"]:
            anonymized["no_hp"] = self._mask_phone(anonymized["no_telepon"])
            del anonymized["no_telepon"]  # Rename to 'no_hp'
        
        # 🟢 TETAP ASLI (tidak diubah):
        # - tanggal_lahir
        # - alamat
        # - email
        
        # ❌ HAPUS field yang tidak perlu
        fields_to_remove = ["rt", "rw"]
        for field in fields_to_remove:
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
        phi_fields = ["nama", "nama_pasien", "no_ktp", "nik", "no_hp", "no_telepon"]
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
            - from_gateway: Patients dari gateway sync
        """
        total = self.db.query(PatientUUIDMap).count()
        
        manual = self.db.query(PatientUUIDMap).filter(
            PatientUUIDMap.source_type == "manual"
        ).count()
        
        excel = self.db.query(PatientUUIDMap).filter(
            PatientUUIDMap.source_type == "excel"
        ).count()
        
        gateway = self.db.query(PatientUUIDMap).filter(
            PatientUUIDMap.source_type == "gateway"
        ).count()
        
        return {
            "total_patients": total,
            "from_manual": manual,
            "from_excel": excel,
            "from_gateway": gateway
        }
    
    def verify_anonymization(self, data: Dict) -> Dict:
        """
        Verify bahwa data sudah di-anonymize (fields masked).
        
        Args:
            data: Data dictionary untuk di-check
        
        Returns:
            Dictionary dengan hasil verifikasi:
            - is_masked: True jika nama/NIK/HP sudah di-mask
            - has_patient_uuid: True/False
            - masked_fields: List of fields yang sudah di-mask
        """
        masked_fields = []
        
        # Check if nama masked
        nama = data.get("nama")
        if nama and "*" in str(nama):
            masked_fields.append("nama")
        
        # Check if NIK masked
        nik = data.get("no_ktp")
        if nik and "*" in str(nik):
            masked_fields.append("no_ktp")
        
        # Check if no_hp masked
        no_hp = data.get("no_hp")
        if no_hp and "*" in str(no_hp):
            masked_fields.append("no_hp")
        
        return {
            "is_masked": len(masked_fields) > 0,
            "has_patient_uuid": "patient_uuid" in data,
            "masked_fields": masked_fields
        }