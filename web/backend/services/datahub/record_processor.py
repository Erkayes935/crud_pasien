"""
Record Processor Service

Split DataHubRecord (raw staging) → Structured tables (Patient, Visit, MedicalRecord)
Also creates PatientUUIDMap for hybrid sync with Gateway
"""
from sqlalchemy.orm import Session
from datetime import date, datetime
import uuid
import logging
import hashlib
from typing import Dict, Any, Optional

from backend.models.datahub.core import DataHubRecord, Patient, Visit, MedicalRecord, PatientUUIDMap

# Setup logger
logger = logging.getLogger(__name__)


def clean_value(value: Any) -> Optional[str]:
    """
    Clean value from frontend - convert sentinel values to None.
    
    Args:
        value: Value from frontend (may be '__default__', 'TBD', empty string, or actual value)
        
    Returns:
        None if value is sentinel/empty, otherwise the value as string
    """
    if value is None:
        return None
    
    # Convert to string first (handle integers from pandas)
    if not isinstance(value, str):
        value = str(value)
    
    # Strip whitespace
    value = value.strip()
    
    # Convert sentinel values to None (case-insensitive for TBD)
    if value.upper() in ('__DEFAULT__', '__BLOCK__', 'TBD', ''):
        return None
    
    # Clean float artifacts (e.g., "1234567890.0" → "1234567890")
    # This happens when pandas reads numbers from CSV/Excel
    if value.endswith('.0'):
        try:
            # Check if it's a valid float that ends with .0
            float_val = float(value)
            if float_val == int(float_val):  # e.g., 1234.0 == 1234
                value = str(int(float_val))
        except ValueError:
            pass  # Not a number, keep original value
    
    return value


def create_sha256_hash(value: str) -> str:
    """
    Create SHA256 hash for sensitive data (nama, NIK).
    
    Args:
        value: String to hash
        
    Returns:
        64-character hex string (SHA256 hash)
    """
    if not value:
        return ""
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def get_or_create_patient_uuid_map(
    patient_uuid: str,
    nama: Optional[str],
    nik: Optional[str],
    hospital_id: str,
    source_record_id: str,
    db: Session
) -> PatientUUIDMap:
    """
    Get existing or create new PatientUUIDMap for hybrid sync.
    
    Purpose:
    - Gateway sends masked data with hashes
    - DataHub needs to identify same patient across sources
    - This map stores SHA256 hashes for deduplication
    
    Args:
        patient_uuid: UUID for this patient
        nama: Patient name (will be hashed)
        nik: NIK/KTP number (will be hashed)
        hospital_id: Hospital ID
        source_record_id: Source record ID for tracking
        db: Database session
        
    Returns:
        PatientUUIDMap entry
    """
    # Check if patient_uuid already exists
    existing = db.query(PatientUUIDMap).filter_by(
        patient_uuid=patient_uuid
    ).first()
    
    if existing:
        # Update last_synced timestamp
        existing.last_synced = datetime.utcnow()
        logger.info(f"Updated PatientUUIDMap for patient_uuid: {patient_uuid}")
        return existing
    
    # Create hashes (only if values exist)
    name_hash = create_sha256_hash(nama) if nama else None
    nik_hash = create_sha256_hash(nik) if nik else None
    
    # Create new mapping
    mapping = PatientUUIDMap(
        patient_uuid=patient_uuid,
        source_type="excel",
        hospital_id=hospital_id,
        source_record_id=source_record_id,
        name_hash=name_hash,
        nik_hash=nik_hash
    )
    
    db.add(mapping)
    logger.info(f"Created PatientUUIDMap for patient_uuid: {patient_uuid}")
    
    return mapping


def split_to_structured_tables(data_hub_record: DataHubRecord, db: Session) -> Dict[str, Any]:
    """
    Auto-split raw DataHubRecord to structured tables.
    
    Flow:
    1. Extract data from json_data
    2. Create/Update Patient (by nik or generate new)
    3. Create/Update PatientUUIDMap (for hybrid sync with Gateway)
    4. Create Visit (linked to patient)
    5. Create MedicalRecord (linked to patient + visit)
    
    Args:
        data_hub_record: Raw record from Excel import
        db: Database session
        
    Returns:
        Dict with created records: {"patient": Patient, "visit": Visit, "medical_record": MedicalRecord, "uuid_map": PatientUUIDMap}
    """
    data = data_hub_record.json_data
    hospital_id = data_hub_record.hospital_id
    
    try:
        # 1. Create/Get Patient
        patient = get_or_create_patient(data, hospital_id, db)
        
        # 2. Create/Update PatientUUIDMap (for hybrid sync)
        nama = data.get('nama_pasien') or patient.nama
        nik = str(data.get('nik')) if data.get('nik') else patient.no_ktp
        uuid_map = get_or_create_patient_uuid_map(
            patient_uuid=patient.patient_uuid,
            nama=nama,
            nik=nik,
            hospital_id=hospital_id,
            source_record_id=data_hub_record.record_id,
            db=db
        )
        
        # 3. Create Visit
        visit = create_visit(patient, data, hospital_id, db)
        
        # 4. Create MedicalRecord
        medical_record = create_medical_record(patient, visit, data, hospital_id, db)
        
        db.flush()
        
        logger.info(f"Split record {data_hub_record.record_id}: Patient {patient.patient_uuid}, Visit {visit.visit_uuid}, MedRec {medical_record.record_uuid}, UUIDMap created/updated")
        
        return {
            "patient": patient,
            "visit": visit,
            "medical_record": medical_record,
            "uuid_map": uuid_map
        }
        
    except Exception as e:
        logger.error(f"Failed to split record {data_hub_record.record_id}: {e}")
        raise


def get_or_create_patient(data: Dict[str, Any], hospital_id: str, db: Session) -> Patient:
    """
    Get existing patient by NIK or create new patient.
    
    Logic:
    - If NIK exists → Find existing patient in same hospital
    - If NIK not found or missing → Create new patient
    
    Args:
        data: Parsed Excel data
        hospital_id: Hospital ID
        db: Database session
        
    Returns:
        Patient record (existing or new)
    """
    nik_raw = data.get('nik')
    
    # Convert NIK to string (handle both string and numeric input)
    nik = str(nik_raw) if nik_raw else None
    
    # Try to find existing patient by NIK
    if nik:
        existing_patient = db.query(Patient).filter_by(
            no_ktp=nik,
            hospital_id=hospital_id,
            is_deleted=False
        ).first()
        
        if existing_patient:
            logger.info(f"Found existing patient {existing_patient.patient_uuid} with NIK {nik}")
            return existing_patient
    
    # Create new patient
    patient_uuid = str(uuid.uuid4())
    
    # Minimal default: Generate unique identifier if nama missing
    nama = data.get('nama_pasien') or f"Patient_{uuid.uuid4().hex[:8]}"
    
    # Parse tanggal_lahir if exists (clean sentinel values first)
    tanggal_lahir = None
    tgl_lahir_raw = clean_value(data.get('tanggal_lahir'))
    if tgl_lahir_raw:
        try:
            if isinstance(tgl_lahir_raw, str):
                tanggal_lahir = datetime.strptime(tgl_lahir_raw, '%Y-%m-%d').date()
            elif isinstance(tgl_lahir_raw, (date, datetime)):
                tanggal_lahir = tgl_lahir_raw if isinstance(tgl_lahir_raw, date) else tgl_lahir_raw.date()
        except Exception as e:
            logger.warning(f"Failed to parse tanggal_lahir '{tgl_lahir_raw}': {e}")
    
    patient = Patient(
        patient_uuid=patient_uuid,
        hospital_id=hospital_id,
        
        # Identifier (minimal default)
        nama=nama,  # Default if missing: "Patient_xxxxx"
        
        # Optional fields (honest NULL) - clean sentinel values
        no_ktp=nik,  # Already converted to string above
        no_rm=clean_value(data.get('no_rm')),
        no_bpjs=clean_value(data.get('no_bpjs')),
        alamat=clean_value(data.get('alamat')),
        email=clean_value(data.get('email')),
        no_hp=clean_value(data.get('no_telepon')),
        tanggal_lahir=tanggal_lahir,
        jenis_kelamin=clean_value(data.get('jenis_kelamin')),
        
        # System fields
        eksternal_id=clean_value(data.get('eksternal_id')),
        source=clean_value(data.get('sumber')),
        
        # Metadata
        source_type="import_excel",
        is_deleted=False,
        is_dummy=False
    )
    
    db.add(patient)
    db.flush()  # Get patient.id
    
    logger.info(f"Created new patient {patient_uuid}: {nama}")
    return patient


def create_visit(patient: Patient, data: Dict[str, Any], hospital_id: str, db: Session) -> Visit:
    """
    Create visit record linked to patient.
    
    Args:
        patient: Patient record
        data: Parsed Excel data
        hospital_id: Hospital ID
        db: Database session
        
    Returns:
        Visit record
    """
    visit_uuid = str(uuid.uuid4())
    
    # Parse tanggal_masuk with default to today (clean sentinel values first)
    tanggal_kunjungan = date.today()  # Minimal default
    tgl_masuk_raw = clean_value(data.get('tanggal_masuk'))
    if tgl_masuk_raw:
        try:
            if isinstance(tgl_masuk_raw, str):
                tanggal_kunjungan = datetime.strptime(tgl_masuk_raw, '%Y-%m-%d').date()
            elif isinstance(tgl_masuk_raw, (date, datetime)):
                tanggal_kunjungan = tgl_masuk_raw if isinstance(tgl_masuk_raw, date) else tgl_masuk_raw.date()
        except Exception as e:
            logger.warning(f"Failed to parse tanggal_masuk '{tgl_masuk_raw}', using today: {e}")
    
    # Minimal default for jenis_rawat
    jenis_rawat = data.get('jenis_rawat') or "Rawat Inap"
    
    # Honest NULL for optional fields
    lama_rawat = None
    if data.get('lama_rawat'):
        try:
            lama_rawat = int(data['lama_rawat'])
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse lama_rawat: {data.get('lama_rawat')}")
    
    # Parse visit_no (default to 1)
    visit_no = 1
    if data.get('visit_no'):
        try:
            visit_no = int(data['visit_no'])
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse visit_no: {data.get('visit_no')}")
    
    visit = Visit(
        visit_uuid=visit_uuid,
        patient_id=patient.id,
        hospital_id=hospital_id,
        
        # Required with minimal defaults
        tanggal_kunjungan=tanggal_kunjungan,
        jenis_rawat=jenis_rawat,
        jenis_kunjungan=clean_value(data.get('jenis_kunjungan')) or jenis_rawat,  # Use jenis_kunjungan if provided, else alias to jenis_rawat
        
        # Visit metadata
        visit_no=visit_no,
        episode_id=clean_value(data.get('episode_id')),
        eksternal_id=clean_value(data.get('eksternal_id')),
        
        # Optional clinical info
        lama_rawat=lama_rawat,
        poli=clean_value(data.get('poli')),
        gejala=clean_value(data.get('gejala')),
        riwayat=clean_value(data.get('riwayat')),
        
        # Doctor info
        doctor_id=clean_value(data.get('doctor_id')),
        doctor_name=clean_value(data.get('doctor_name')),
        
        # Source
        sumber=clean_value(data.get('sumber')),
        
        # Metadata
        source_type="import_excel",
        is_deleted=False,
        is_dummy=False
    )
    
    db.add(visit)
    db.flush()  # Get visit.id
    
    logger.info(f"Created visit {visit_uuid} for patient {patient.patient_uuid}")
    return visit


def create_medical_record(patient: Patient, visit: Visit, data: Dict[str, Any], hospital_id: str, db: Session) -> MedicalRecord:
    """
    Create medical record linked to patient and visit.
    
    Args:
        patient: Patient record
        visit: Visit record
        data: Parsed Excel data
        hospital_id: Hospital ID
        db: Database session
        
    Returns:
        MedicalRecord
    """
    record_uuid = str(uuid.uuid4())
    
    # Parse record_type (default to "admission")
    record_type = clean_value(data.get('record_type')) or "admission"
    
    # Parse is_final (default to False)
    is_final = False
    if data.get('is_final'):
        is_final = str(data.get('is_final')).lower() in ('true', '1', 'yes', 'final')
    
    # Parse notes_date (default to visit date)
    notes_date = visit.tanggal_kunjungan
    notes_date_raw = clean_value(data.get('notes_date'))
    if notes_date_raw:
        try:
            if isinstance(notes_date_raw, str):
                notes_date = datetime.strptime(notes_date_raw, '%Y-%m-%d').date()
            elif isinstance(notes_date_raw, (date, datetime)):
                notes_date = notes_date_raw if isinstance(notes_date_raw, date) else notes_date_raw.date()
        except Exception as e:
            logger.warning(f"Failed to parse notes_date '{notes_date_raw}': {e}")
    
    medical_record = MedicalRecord(
        record_uuid=record_uuid,
        patient_id=patient.id,
        visit_id=visit.id,
        hospital_id=hospital_id,
        
        # Record metadata
        record_type=record_type,
        is_final=is_final,
        notes_date=notes_date,
        
        # Doctor info
        doctor_id=clean_value(data.get('doctor_id')),
        doctor_name=clean_value(data.get('doctor_name')),
        
        # ========== MEDICAL HISTORY ==========
        riwayat_penyakit=clean_value(data.get('riwayat_penyakit')) or clean_value(data.get('riwayat')),
        riwayat_pengobatan=clean_value(data.get('riwayat_pengobatan')),
        riwayat_operasi=clean_value(data.get('riwayat_operasi')),
        alergi=clean_value(data.get('alergi')),
        
        # ========== SYMPTOMS & COMPLAINTS ==========
        keluhan=clean_value(data.get('keluhan')) or clean_value(data.get('gejala')),
        gejala_lain=clean_value(data.get('gejala_lain')),
        
        # ========== VITAL SIGNS ==========
        tekanan_darah=clean_value(data.get('tekanan_darah')),
        nadi=clean_value(data.get('nadi')),
        pernapasan=clean_value(data.get('pernapasan')),
        suhu=clean_value(data.get('suhu')),
        spo2=clean_value(data.get('spo2')),
        berat_badan=clean_value(data.get('berat_badan')),
        tinggi_badan=clean_value(data.get('tinggi_badan')),
        
        # ========== LAB RESULTS ==========
        hemoglobin=clean_value(data.get('hemoglobin')),
        leukosit=clean_value(data.get('leukosit')),
        trombosit=clean_value(data.get('trombosit')),
        gula_darah=clean_value(data.get('gula_darah')),
        creatinin=clean_value(data.get('creatinin')),
        
        # ========== IMAGING ==========
        rontgen_thorax=clean_value(data.get('rontgen_thorax')),
        ct_scan=clean_value(data.get('ct_scan')),
        usg=clean_value(data.get('usg')),
        
        # ========== DIAGNOSIS ==========
        diagnosis_awal=clean_value(data.get('diagnosis_awal')) or clean_value(data.get('diagnosis')),
        diagnosis=clean_value(data.get('diagnosis')),
        komorbid=clean_value(data.get('komorbid')),
        komplikasi=clean_value(data.get('komplikasi')),
        diagnosis_akhir=clean_value(data.get('diagnosis_akhir')),
        
        # ========== TREATMENT ==========
        tindakan=clean_value(data.get('tindakan')),
        obat=clean_value(data.get('obat')),
        validasi_fornas=clean_value(data.get('validasi_fornas')),
        
        # ========== NOTES ==========
        notes_doctor=clean_value(data.get('notes_doctor')),
        
        # Metadata
        source_type="import_excel",
        status=clean_value(data.get('status')) or "ready_for_ai",
        is_deleted=False,
        is_dummy=False
    )
    
    db.add(medical_record)
    db.flush()
    
    logger.info(f"Created medical record {record_uuid} for visit {visit.visit_uuid}")
    return medical_record
