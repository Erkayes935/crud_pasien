"""
routers/claim/claim_export_router.py
Refactor modular dari claim_router.py
Fokus: export data klaim ke Excel, PDF, dan JSON (modular dengan helper di _utils.py)
"""

import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer

from backend.database import get_db
from backend.auth import require_roles_session
from backend import models
from backend.utils.claim_utils import (
    normalize_str,
    parse_int,
    aggregate_ai_notifications,
    get_primary_diagnosis,
    get_secondary_diagnoses,
    get_primary_procedure,
    get_tariffs_optimized,
    calculate_length_of_stay,
)

router = APIRouter(tags=["Claim Export"])


# ==================================================
# 🧾 EXPORT EXCEL
# ==================================================

@router.get("/export/excel", name="export_claims_excel")
def export_claims_excel(
    status: Optional[str] = Query(None),
    tanggal_kunjungan: Optional[str] = Query(None),
    patient_name: Optional[str] = Query(None),
    claim_id: Optional[str] = Query(None),
    visit_id: Optional[str] = Query(None),
    workflow_status: Optional[str] = Query(None),
    diagnosis: Optional[str] = Query(None),
    tindakan: Optional[str] = Query(None),
    doctor_name: Optional[str] = Query(None),
    ai_status: Optional[str] = Query(None),
    tarif_cbg_min: Optional[str] = Query(None),
    tarif_cbg_max: Optional[str] = Query(None),
    los_min: Optional[str] = Query(None),
    los_max: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """
    Export data klaim ke Excel (openpyxl)
    Menggunakan filter dan role-based query sama seperti list_claims.
    """
    try:
        # Normalisasi input
        status = normalize_str(status)
        tanggal_kunjungan = normalize_str(tanggal_kunjungan)
        patient_name = normalize_str(patient_name)
        claim_id = normalize_str(claim_id)
        visit_id = normalize_str(visit_id)
        workflow_status = normalize_str(workflow_status)
        diagnosis = normalize_str(diagnosis)
        tindakan = normalize_str(tindakan)
        doctor_name = normalize_str(doctor_name)
        ai_status = normalize_str(ai_status)

        tarif_cbg_min = parse_int(tarif_cbg_min)
        tarif_cbg_max = parse_int(tarif_cbg_max)
        los_min = parse_int(los_min)
        los_max = parse_int(los_max)

        # Query base
        joined_patient = joined_visit = joined_diagnosis = joined_procedure = joined_user = False
        query = db.query(models.Claim)

        # Role-based filter
        roles = user.role_names or []
        if "verifikator" in roles and "coder" not in roles and "doctor" not in roles:
            query = query.filter(models.Claim.workflow_status.in_(
                ["coder_verified", "verifikator_review", "finalized"]))
        elif "coder" in roles and "verifikator" not in roles and "doctor" not in roles:
            query = query.filter(models.Claim.workflow_status.in_(
                ["doctor_submitted", "coder_review", "coder_verified"]))
        elif "doctor" in roles and "coder" not in roles and "verifikator" not in roles:
            query = query.filter(models.Claim.doctor_id == user.id)

        # Filters
        if status:
            query = query.filter(models.Claim.status == status)
        if workflow_status:
            query = query.filter(models.Claim.workflow_status == workflow_status)
        if patient_name:
            if not joined_patient:
                query = query.join(models.Patient, models.Claim.patient_id == models.Patient.id)
                joined_patient = True
            query = query.filter(models.Patient.nama.ilike(f"%{patient_name}%"))
        if tanggal_kunjungan:
            if not joined_visit:
                query = query.join(models.Visit, models.Claim.visit_id == models.Visit.id)
                joined_visit = True
            query = query.filter(models.Visit.tanggal_kunjungan == tanggal_kunjungan)
        if claim_id and str(claim_id).isdigit():
            query = query.filter(models.Claim.id == int(claim_id))
        if visit_id and str(visit_id).isdigit():
            query = query.filter(models.Claim.visit_id == int(visit_id))
        if diagnosis:
            if not joined_diagnosis:
                query = query.join(models.ClaimDiagnosis, models.Claim.id == models.ClaimDiagnosis.claim_id)
                joined_diagnosis = True
            query = query.filter(
                or_(
                    models.ClaimDiagnosis.diagnosis_text.ilike(f"%{diagnosis}%"),
                    models.ClaimDiagnosis.icd10_code.ilike(f"%{diagnosis}%")
                ),
                models.ClaimDiagnosis.is_deleted == False
            )
        if tindakan:
            if not joined_procedure:
                query = query.join(models.ClaimProcedure, models.Claim.id == models.ClaimProcedure.claim_id)
                joined_procedure = True
            query = query.filter(
                or_(
                    models.ClaimProcedure.procedure_text.ilike(f"%{tindakan}%"),
                    models.ClaimProcedure.icd9_final_by_coder.ilike(f"%{tindakan}%")
                ),
                models.ClaimProcedure.is_deleted == False
            )
        if doctor_name:
            if not joined_user:
                query = query.outerjoin(models.User, models.Claim.doctor_id == models.User.id)
                joined_user = True
            query = query.filter(
                or_(
                    models.Claim.doctor_name.ilike(f"%{doctor_name}%"),
                    models.User.name.ilike(f"%{doctor_name}%")
                )
            )

        if not joined_patient:
            query = query.options(joinedload(models.Claim.patient))
        if not joined_visit:
            query = query.options(joinedload(models.Claim.visit))
        query = query.options(
            joinedload(models.Claim.hospital),
            joinedload(models.Claim.group),
            joinedload(models.Claim.diagnoses),
            joinedload(models.Claim.procedures),
            joinedload(models.Claim.tariffs),
            joinedload(models.Claim.ai_recommendations),
        )
        if joined_diagnosis or joined_procedure:
            query = query.distinct()

        claims = query.all()

        # Build Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Laporan Klaim"

        headers = [
            "ID Klaim", "Tanggal Klaim", "Nama Pasien", "No. RM",
            "Dokter", "Status", "Workflow Status",
            "Diagnosis Utama", "Jumlah Sekunder", "Tindakan Utama",
            "Tarif INA-CBG", "Tarif RS", "Length of Stay",
            "AI Status", "Total AI Notif", "Dibuat"
        ]
        ws.append(headers)

        for claim in claims:
            ai_agg = aggregate_ai_notifications(claim)
            tarif_cbg, tarif_rs = get_tariffs_optimized(claim)

            ws.append([
                claim.id,
                claim.tanggal_klaim.strftime("%Y-%m-%d") if claim.tanggal_klaim else "-",
                claim.patient.nama if claim.patient else "-",
                claim.patient.no_rm if claim.patient else "-",
                claim.doctor.username if claim.doctor else "-",
                claim.status or "-",
                claim.workflow_status or "-",
                get_primary_diagnosis(claim),
                get_secondary_diagnoses(claim),
                get_primary_procedure(claim),
                tarif_cbg,
                tarif_rs,
                calculate_length_of_stay(claim),
                ai_agg["max_severity"],
                ai_agg["total_count"],
                claim.created_at.strftime("%Y-%m-%d %H:%M") if claim.created_at else "-"
            ])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"laporan_klaim_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        print(f"[EXPORT_EXCEL] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal export Excel: {e}")


# ==================================================
# 🧾 EXPORT PDF
# ==================================================

@router.get("/export/pdf", name="export_claims_pdf")
def export_claims_pdf(
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "coder", "verifikator", "admin_rs", "superadmin")),
):
    """Export data klaim ke PDF (ReportLab)"""
    try:
        claims = db.query(models.Claim).all()
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            "Title", parent=styles["Heading1"], fontSize=16, alignment=1, spaceAfter=20
        )
        story.append(Paragraph("LAPORAN DATA KLAIM", title_style))
        story.append(Spacer(1, 20))

        table_data = [["ID", "Pasien", "Dokter", "Status", "Workflow", "AI"]]
        for c in claims:
            ai_agg = aggregate_ai_notifications(c)
            table_data.append([
                c.id,
                c.patient.nama if c.patient else "-",
                c.doctor.username if c.doctor else "-",
                c.status or "-",
                c.workflow_status or "-",
                ai_agg["status_icon"],
            ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        story.append(table)

        doc.build(story)
        buffer.seek(0)

        filename = f"laporan_klaim_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        print(f"[EXPORT_PDF] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal export PDF: {e}")


# ==================================================
# 🧩 EXPORT JSON (placeholder)
# ==================================================

@router.get("/export/json", name="export_claims_json")
def export_claims_json(
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("admin_rs", "superadmin")),
):
    """(Placeholder) Export data klaim ke JSON untuk AI suggestion atau API eksternal"""
    claims = db.query(models.Claim).limit(50).all()
    data = [
        {
            "id": c.id,
            "patient": c.patient.nama if c.patient else "-",
            "workflow": c.workflow_status,
            "ai_summary": aggregate_ai_notifications(c),
        }
        for c in claims
    ]
    return {"status": "ok", "count": len(data), "data": data}
