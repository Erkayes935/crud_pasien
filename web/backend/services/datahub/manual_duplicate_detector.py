"""
Manual Input Duplicate Detector Service
========================================
Deteksi duplikasi untuk input manual dengan 3 fase:
1. Patient Duplicate Check (berdasarkan patient_uuid)
2. Visit Duplicate Check (berdasarkan patient + tanggal_kunjungan + jenis_rawat)
3. Medical Record Duplicate Check (berdasarkan visit + record_type + notes_date + all fields)

Berbeda dengan duplicate_detector.py yang untuk upload excel.
"""
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, date
from backend.models.datahub.core import Patient, Visit, MedicalRecord
from backend.services.datahub.logger import log_event


class ManualDuplicateDetector:
    """
    Service untuk deteksi duplicate pada manual input.
    
    Strategi 3-fase:
    - Phase 1: Patient duplicate check (by patient_uuid)
    - Phase 2: Visit duplicate check (by patient + date + type)
    - Phase 3: Medical Record duplicate check (by visit + record_type + notes_date + all fields)
    """
    
    def __init__(self, db: Session):
        """
        Initialize detector.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db
    
    # =====================================================================
    # PHASE 1: PATIENT DUPLICATE CHECK
    # =====================================================================
    
    def check_patient_duplicate(self, patient_uuid: str, hospital_id: str) -> Optional[Patient]:
        """
        Phase 1: Check apakah patient dengan patient_uuid sudah ada.
        
        Patient UUID di-generate dari hash nama/NIK, jadi kalau sama berarti patient sama.
        
        Args:
            patient_uuid: UUID yang di-generate dari hash nama/NIK
            hospital_id: ID rumah sakit
            
        Returns:
            Patient object jika sudah ada, None jika belum ada
        """
        existing_patient = self.db.query(Patient).filter(
            Patient.patient_uuid == patient_uuid,
            Patient.hospital_id == hospital_id,
            Patient.is_deleted == False
        ).first()
        
        if existing_patient:
            log_event(
                self.db,
                str(existing_patient.id),
                "manual_duplicate_detector",
                "info",
                f"Patient duplicate detected: {existing_patient.nama} (UUID: {patient_uuid})"
            )
        
        return existing_patient
    
    # =====================================================================
    # PHASE 2: VISIT DUPLICATE CHECK
    # =====================================================================
    
    def check_visit_duplicate(
        self, 
        patient_id: int, 
        tanggal_kunjungan: date, 
        jenis_rawat: str
    ) -> Optional[Visit]:
        """
        Phase 2: Check apakah visit dengan kombinasi patient + tanggal + jenis_rawat sudah ada.
        
        Logic: Satu patient tidak bisa punya 2 visit dengan tanggal dan jenis rawat yang sama.
        
        Args:
            patient_id: ID patient
            tanggal_kunjungan: Tanggal kunjungan (date object)
            jenis_rawat: Jenis rawat (e.g., "Rawat Inap", "Rawat Jalan")
            
        Returns:
            Visit object jika sudah ada, None jika belum ada
        """
        existing_visit = self.db.query(Visit).filter(
            Visit.patient_id == patient_id,
            Visit.tanggal_kunjungan == tanggal_kunjungan,
            Visit.jenis_rawat == jenis_rawat,
            Visit.is_deleted == False
        ).first()
        
        if existing_visit:
            log_event(
                self.db,
                str(existing_visit.id),
                "manual_duplicate_detector",
                "info",
                f"Visit duplicate detected: Patient {patient_id}, Date {tanggal_kunjungan}, Type {jenis_rawat}"
            )
        
        return existing_visit
    
    # =====================================================================
    # PHASE 3: MEDICAL RECORD DUPLICATE CHECK
    # =====================================================================
    
    def check_medical_record_duplicate(
        self,
        visit_id: int,
        record_type: str,
        notes_date: date,
        record_data: Dict
    ) -> Tuple[Optional[MedicalRecord], bool]:
        """
        Phase 3: Check apakah medical record dengan kombinasi visit + record_type + notes_date sudah ada.
        
        Jika ada, lakukan pengecekan field-by-field:
        - Jika SEMUA field sama persis → Duplicate (return True)
        - Jika ada field yang beda → Bukan duplicate (return False)
        
        Args:
            visit_id: ID visit
            record_type: Tipe record (admission/daily/discharge)
            notes_date: Tanggal catatan (date object)
            record_data: Dict berisi semua field medical record untuk comparison
            
        Returns:
            Tuple (MedicalRecord or None, is_exact_duplicate: bool)
            - (None, False): Tidak ada record dengan kombinasi visit+type+date
            - (record, True): Ada record dan SEMUA field sama persis (exact duplicate)
            - (record, False): Ada record tapi ada field yang beda (bukan duplicate)
        """
        # Cari record dengan kombinasi visit + record_type + notes_date
        existing_record = self.db.query(MedicalRecord).filter(
            MedicalRecord.visit_id == visit_id,
            MedicalRecord.record_type == record_type,
            MedicalRecord.notes_date == notes_date,
            MedicalRecord.is_deleted == False
        ).first()
        
        if not existing_record:
            # Tidak ada record dengan kombinasi ini
            return None, False
        
        # Ada record, sekarang compare semua field
        is_exact_duplicate = self._compare_medical_record_fields(existing_record, record_data)
        
        if is_exact_duplicate:
            log_event(
                self.db,
                str(existing_record.id),
                "manual_duplicate_detector",
                "warning",
                f"Medical Record EXACT duplicate detected: Visit {visit_id}, Type {record_type}, Date {notes_date}"
            )
        else:
            log_event(
                self.db,
                str(existing_record.id),
                "manual_duplicate_detector",
                "info",
                f"Medical Record with same visit+type+date found but fields differ (NOT duplicate)"
            )
        
        return existing_record, is_exact_duplicate
    
    def _compare_medical_record_fields(self, existing_record: MedicalRecord, new_data: Dict) -> bool:
        """
        Compare semua field medical record untuk deteksi exact duplicate.
        
        Args:
            existing_record: Record yang sudah ada di database
            new_data: Data baru yang akan di-insert
            
        Returns:
            True jika SEMUA field sama persis, False jika ada yang beda
        """
        # List semua field yang perlu di-compare
        # Exclude: id, uuid, record_uuid, timestamps, metadata fields
        fields_to_compare = [
            # Doctor info
            'doctor_name',
            
            # Riwayat
            'keluhan', 'riwayat_penyakit', 'riwayat_pengobatan', 'riwayat_operasi',
            'alergi', 'gejala_lain',
            
            # Pemeriksaan Fisik
            'tekanan_darah', 'nadi', 'pernapasan', 'suhu', 'spo2',
            'berat_badan', 'tinggi_badan',
            
            # Lab
            'hemoglobin', 'leukosit', 'trombosit', 'gula_darah', 'creatinin',
            'rontgen_thorax', 'ct_scan', 'usg',
            
            # Diagnosis & Tindakan
            'diagnosis_awal', 'diagnosis', 'komorbid', 'komplikasi',
            'diagnosis_akhir', 'tindakan',
            
            # Obat
            'obat', 'validasi_fornas', 'notes_doctor'
        ]
        
        # Compare setiap field
        for field in fields_to_compare:
            existing_value = getattr(existing_record, field, None)
            new_value = new_data.get(field, None)
            
            # Normalize None dan empty string sebagai sama
            existing_normalized = self._normalize_value(existing_value)
            new_normalized = self._normalize_value(new_value)
            
            if existing_normalized != new_normalized:
                # Ada field yang beda, bukan duplicate
                return False
        
        # Semua field sama persis
        return True
    
    def _normalize_value(self, value) -> str:
        """
        Normalize value untuk comparison.
        - None → ""
        - String → strip whitespace
        - Lainnya → convert to string
        
        Args:
            value: Value to normalize
            
        Returns:
            Normalized string
        """
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()
    
    # =====================================================================
    # HELPER METHODS
    # =====================================================================
    
    def get_duplicate_summary(self) -> Dict:
        """
        Get summary statistik duplicate detection untuk manual input.
        
        Returns:
            Dict dengan statistik duplicate
        """
        # Count patients with duplicate patient_uuid
        total_patients = self.db.query(Patient).filter(
            Patient.source_type == "manual",
            Patient.is_deleted == False
        ).count()
        
        # Count visits
        total_visits = self.db.query(Visit).filter(
            Visit.source_type == "manual",
            Visit.is_deleted == False
        ).count()
        
        # Count medical records
        total_records = self.db.query(MedicalRecord).filter(
            MedicalRecord.source_type == "manual",
            MedicalRecord.is_deleted == False
        ).count()
        
        return {
            "total_manual_patients": total_patients,
            "total_manual_visits": total_visits,
            "total_manual_records": total_records,
            "detector_type": "manual_input"
        }
