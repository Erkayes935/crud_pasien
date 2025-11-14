"""
Test Manual Duplicate Detector
================================
Unit tests untuk ManualDuplicateDetector service.
"""
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.core import Base, Patient, Visit, MedicalRecord
from app.services.manual_duplicate_detector import ManualDuplicateDetector


# Setup test database
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def db_session():
    """Create test database session."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def detector(db_session):
    """Create ManualDuplicateDetector instance."""
    return ManualDuplicateDetector(db_session)


# =====================================================================
# PHASE 1: PATIENT DUPLICATE TESTS
# =====================================================================

def test_patient_duplicate_detected(db_session, detector):
    """Test: Patient duplicate terdeteksi berdasarkan patient_uuid."""
    # Create patient pertama
    patient1 = Patient(
        patient_uuid="test-uuid-123",
        hospital_id="RS001",
        nama="John Doe",
        is_deleted=False
    )
    db_session.add(patient1)
    db_session.commit()
    
    # Check duplicate
    existing = detector.check_patient_duplicate(
        patient_uuid="test-uuid-123",
        hospital_id="RS001"
    )
    
    assert existing is not None
    assert existing.patient_uuid == "test-uuid-123"
    assert existing.nama == "John Doe"


def test_patient_no_duplicate(db_session, detector):
    """Test: Patient tidak duplicate jika UUID berbeda."""
    # Create patient pertama
    patient1 = Patient(
        patient_uuid="test-uuid-123",
        hospital_id="RS001",
        nama="John Doe",
        is_deleted=False
    )
    db_session.add(patient1)
    db_session.commit()
    
    # Check dengan UUID berbeda
    existing = detector.check_patient_duplicate(
        patient_uuid="test-uuid-456",  # Different UUID
        hospital_id="RS001"
    )
    
    assert existing is None


def test_patient_different_hospital(db_session, detector):
    """Test: Patient tidak duplicate jika hospital berbeda."""
    # Create patient di RS001
    patient1 = Patient(
        patient_uuid="test-uuid-123",
        hospital_id="RS001",
        nama="John Doe",
        is_deleted=False
    )
    db_session.add(patient1)
    db_session.commit()
    
    # Check di RS002
    existing = detector.check_patient_duplicate(
        patient_uuid="test-uuid-123",
        hospital_id="RS002"  # Different hospital
    )
    
    assert existing is None


# =====================================================================
# PHASE 2: VISIT DUPLICATE TESTS
# =====================================================================

def test_visit_duplicate_detected(db_session, detector):
    """Test: Visit duplicate terdeteksi berdasarkan patient + date + type."""
    # Create patient
    patient = Patient(
        patient_uuid="test-uuid-123",
        hospital_id="RS001",
        nama="John Doe",
        is_deleted=False
    )
    db_session.add(patient)
    db_session.commit()
    
    # Create visit
    visit1 = Visit(
        visit_uuid="visit-uuid-123",
        patient_id=patient.id,
        hospital_id="RS001",
        tanggal_kunjungan=date(2024, 1, 15),
        jenis_rawat="Rawat Inap",
        is_deleted=False
    )
    db_session.add(visit1)
    db_session.commit()
    
    # Check duplicate
    existing = detector.check_visit_duplicate(
        patient_id=patient.id,
        tanggal_kunjungan=date(2024, 1, 15),
        jenis_rawat="Rawat Inap"
    )
    
    assert existing is not None
    assert existing.visit_uuid == "visit-uuid-123"


def test_visit_no_duplicate_different_date(db_session, detector):
    """Test: Visit tidak duplicate jika tanggal berbeda."""
    # Create patient
    patient = Patient(
        patient_uuid="test-uuid-123",
        hospital_id="RS001",
        nama="John Doe",
        is_deleted=False
    )
    db_session.add(patient)
    db_session.commit()
    
    # Create visit
    visit1 = Visit(
        visit_uuid="visit-uuid-123",
        patient_id=patient.id,
        hospital_id="RS001",
        tanggal_kunjungan=date(2024, 1, 15),
        jenis_rawat="Rawat Inap",
        is_deleted=False
    )
    db_session.add(visit1)
    db_session.commit()
    
    # Check dengan tanggal berbeda
    existing = detector.check_visit_duplicate(
        patient_id=patient.id,
        tanggal_kunjungan=date(2024, 1, 16),  # Different date
        jenis_rawat="Rawat Inap"
    )
    
    assert existing is None


def test_visit_no_duplicate_different_type(db_session, detector):
    """Test: Visit tidak duplicate jika jenis rawat berbeda."""
    # Create patient
    patient = Patient(
        patient_uuid="test-uuid-123",
        hospital_id="RS001",
        nama="John Doe",
        is_deleted=False
    )
    db_session.add(patient)
    db_session.commit()
    
    # Create visit
    visit1 = Visit(
        visit_uuid="visit-uuid-123",
        patient_id=patient.id,
        hospital_id="RS001",
        tanggal_kunjungan=date(2024, 1, 15),
        jenis_rawat="Rawat Inap",
        is_deleted=False
    )
    db_session.add(visit1)
    db_session.commit()
    
    # Check dengan jenis rawat berbeda
    existing = detector.check_visit_duplicate(
        patient_id=patient.id,
        tanggal_kunjungan=date(2024, 1, 15),
        jenis_rawat="Rawat Jalan"  # Different type
    )
    
    assert existing is None


# =====================================================================
# PHASE 3: MEDICAL RECORD DUPLICATE TESTS
# =====================================================================

def test_medical_record_exact_duplicate(db_session, detector):
    """Test: Medical record exact duplicate terdeteksi (semua field sama)."""
    # Create patient
    patient = Patient(
        patient_uuid="test-uuid-123",
        hospital_id="RS001",
        nama="John Doe",
        is_deleted=False
    )
    db_session.add(patient)
    db_session.commit()
    
    # Create visit
    visit = Visit(
        visit_uuid="visit-uuid-123",
        patient_id=patient.id,
        hospital_id="RS001",
        tanggal_kunjungan=date(2024, 1, 15),
        jenis_rawat="Rawat Inap",
        is_deleted=False
    )
    db_session.add(visit)
    db_session.commit()
    
    # Create medical record
    record1 = MedicalRecord(
        record_uuid="record-uuid-123",
        patient_id=patient.id,
        visit_id=visit.id,
        hospital_id="RS001",
        record_type="admission",
        notes_date=date(2024, 1, 15),
        doctor_name="Dr. Budi",
        keluhan="Demam tinggi",
        diagnosis="Typhoid fever",
        tekanan_darah="120/80",
        is_deleted=False
    )
    db_session.add(record1)
    db_session.commit()
    
    # Check duplicate dengan data yang sama persis
    record_data = {
        'doctor_name': "Dr. Budi",
        'keluhan': "Demam tinggi",
        'diagnosis': "Typhoid fever",
        'tekanan_darah': "120/80",
        'riwayat_penyakit': None,
        'riwayat_pengobatan': None,
        'riwayat_operasi': None,
        'alergi': None,
        'gejala_lain': None,
        'nadi': None,
        'pernapasan': None,
        'suhu': None,
        'spo2': None,
        'berat_badan': None,
        'tinggi_badan': None,
        'hemoglobin': None,
        'leukosit': None,
        'trombosit': None,
        'gula_darah': None,
        'creatinin': None,
        'rontgen_thorax': None,
        'ct_scan': None,
        'usg': None,
        'diagnosis_awal': None,
        'komorbid': None,
        'komplikasi': None,
        'diagnosis_akhir': None,
        'tindakan': None,
        'obat': None,
        'validasi_fornas': None,
        'notes_doctor': None
    }
    
    existing, is_exact = detector.check_medical_record_duplicate(
        visit_id=visit.id,
        record_type="admission",
        notes_date=date(2024, 1, 15),
        record_data=record_data
    )
    
    assert existing is not None
    assert is_exact is True
    assert existing.record_uuid == "record-uuid-123"


def test_medical_record_not_duplicate_different_field(db_session, detector):
    """Test: Medical record tidak duplicate jika ada field yang beda."""
    # Create patient
    patient = Patient(
        patient_uuid="test-uuid-123",
        hospital_id="RS001",
        nama="John Doe",
        is_deleted=False
    )
    db_session.add(patient)
    db_session.commit()
    
    # Create visit
    visit = Visit(
        visit_uuid="visit-uuid-123",
        patient_id=patient.id,
        hospital_id="RS001",
        tanggal_kunjungan=date(2024, 1, 15),
        jenis_rawat="Rawat Inap",
        is_deleted=False
    )
    db_session.add(visit)
    db_session.commit()
    
    # Create medical record
    record1 = MedicalRecord(
        record_uuid="record-uuid-123",
        patient_id=patient.id,
        visit_id=visit.id,
        hospital_id="RS001",
        record_type="admission",
        notes_date=date(2024, 1, 15),
        doctor_name="Dr. Budi",
        keluhan="Demam tinggi",
        diagnosis="Typhoid fever",
        tekanan_darah="120/80",
        is_deleted=False
    )
    db_session.add(record1)
    db_session.commit()
    
    # Check duplicate dengan diagnosis berbeda
    record_data = {
        'doctor_name': "Dr. Budi",
        'keluhan': "Demam tinggi",
        'diagnosis': "Dengue fever",  # BERBEDA!
        'tekanan_darah': "120/80",
        'riwayat_penyakit': None,
        'riwayat_pengobatan': None,
        'riwayat_operasi': None,
        'alergi': None,
        'gejala_lain': None,
        'nadi': None,
        'pernapasan': None,
        'suhu': None,
        'spo2': None,
        'berat_badan': None,
        'tinggi_badan': None,
        'hemoglobin': None,
        'leukosit': None,
        'trombosit': None,
        'gula_darah': None,
        'creatinin': None,
        'rontgen_thorax': None,
        'ct_scan': None,
        'usg': None,
        'diagnosis_awal': None,
        'komorbid': None,
        'komplikasi': None,
        'diagnosis_akhir': None,
        'tindakan': None,
        'obat': None,
        'validasi_fornas': None,
        'notes_doctor': None
    }
    
    existing, is_exact = detector.check_medical_record_duplicate(
        visit_id=visit.id,
        record_type="admission",
        notes_date=date(2024, 1, 15),
        record_data=record_data
    )
    
    assert existing is not None
    assert is_exact is False  # Bukan exact duplicate


def test_medical_record_no_existing_record(db_session, detector):
    """Test: Tidak ada record dengan kombinasi visit+type+date."""
    # Create patient
    patient = Patient(
        patient_uuid="test-uuid-123",
        hospital_id="RS001",
        nama="John Doe",
        is_deleted=False
    )
    db_session.add(patient)
    db_session.commit()
    
    # Create visit
    visit = Visit(
        visit_uuid="visit-uuid-123",
        patient_id=patient.id,
        hospital_id="RS001",
        tanggal_kunjungan=date(2024, 1, 15),
        jenis_rawat="Rawat Inap",
        is_deleted=False
    )
    db_session.add(visit)
    db_session.commit()
    
    # Check duplicate tanpa ada record sebelumnya
    record_data = {
        'doctor_name': "Dr. Budi",
        'keluhan': "Demam tinggi",
        'diagnosis': "Typhoid fever",
        'tekanan_darah': "120/80"
    }
    
    existing, is_exact = detector.check_medical_record_duplicate(
        visit_id=visit.id,
        record_type="admission",
        notes_date=date(2024, 1, 15),
        record_data=record_data
    )
    
    assert existing is None
    assert is_exact is False


# =====================================================================
# HELPER TESTS
# =====================================================================

def test_get_duplicate_summary(db_session, detector):
    """Test: Get duplicate statistics."""
    # Create test data
    patient = Patient(
        patient_uuid="test-uuid-123",
        hospital_id="RS001",
        nama="John Doe",
        source_type="manual",
        is_deleted=False
    )
    db_session.add(patient)
    db_session.commit()
    
    visit = Visit(
        visit_uuid="visit-uuid-123",
        patient_id=patient.id,
        hospital_id="RS001",
        tanggal_kunjungan=date(2024, 1, 15),
        jenis_rawat="Rawat Inap",
        source_type="manual",
        is_deleted=False
    )
    db_session.add(visit)
    db_session.commit()
    
    record = MedicalRecord(
        record_uuid="record-uuid-123",
        patient_id=patient.id,
        visit_id=visit.id,
        hospital_id="RS001",
        record_type="admission",
        notes_date=date(2024, 1, 15),
        source_type="manual",
        is_deleted=False
    )
    db_session.add(record)
    db_session.commit()
    
    # Get summary
    stats = detector.get_duplicate_summary()
    
    assert stats['total_manual_patients'] == 1
    assert stats['total_manual_visits'] == 1
    assert stats['total_manual_records'] == 1
    assert stats['detector_type'] == "manual_input"


def test_normalize_value(detector):
    """Test: Value normalization untuk comparison."""
    assert detector._normalize_value(None) == ""
    assert detector._normalize_value("  test  ") == "test"
    assert detector._normalize_value("") == ""
    assert detector._normalize_value(123) == "123"
