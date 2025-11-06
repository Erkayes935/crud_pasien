"""
routers/claim/claim_regulation_router.py
Fokus: endpoint multilayer regulasi & laporan regional.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.auth import require_roles_session
from backend import models
from backend.services import regulation_service

router = APIRouter(tags=["Claim Regulation"])

@router.post("/regulation/detail")
async def regulation_detail(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "verifikator", "coder", "admin_rs", "superadmin")),
):
    try:
        field = payload.get("field")
        rs_id = payload.get("rs_id")
        region_id = payload.get("region_id")
        scope = (payload.get("scope") or "diagnosis_eval").lower()
        claim_id = payload.get("claim_id")

        print(f"[LEGACY_REGULATION_DETAIL] 🔍 field={field}, scope={scope}, rs_id={rs_id}, region_id={region_id}")

        # 🧠 ambil diagnosis utama kalau scope bukan eval
        diagnosis_name = None
        if scope.startswith("diagnosis"):
            from backend.models import ClaimDiagnosis
            diag = db.query(ClaimDiagnosis).filter_by(claim_id=claim_id, is_deleted=False).first()
            diagnosis_name = diag.diagnosis_text if diag else field
        else:
            diagnosis_name = field

        print(f"[LEGACY_REGULATION_DETAIL] 🔎 diagnosis_name={diagnosis_name}")

        # panggil service utama
        from backend.services import claim_ai
        result = await claim_ai.regulation_detail(payload)
        return result

        # pastikan bentuk array
        if isinstance(data, dict):
            data = [data]
        elif data is None:
            data = []

        for item in data:
            if not item.get("layer"):
                item["layer"] = item.get("dasar_hukum") or item.get("sumber") or "Unknown"

        return {"status": "ok", "data": data}
    except Exception as e:
        print(f"[LEGACY_REGULATION_DETAIL] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal memuat regulasi: {e}")


@router.get("/rules/load")
async def load_multilayer_rules(
    diagnosis: str = Query(..., description="Nama diagnosis yang ingin dicari regulasinya"),
    rs_id: str | None = Query(None, description="ID Rumah Sakit"),
    region_id: str | None = Query(None, description="ID Wilayah (Region)"),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "verifikator", "coder", "admin_rs", "superadmin")),
):
    try:
        data = regulation_service.load_multilayer_rules(db, diagnosis, rs_id, region_id)
        return {"status": "ok", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memuat regulasi multilayer: {e}")

@router.get("/api/regional-reports/{report_id}")
async def get_regional_report_detail(
    report_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin", "admin_rs")),
):
    report = db.query(models.RegionalReports).filter_by(id=report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Regional report tidak ditemukan")
    return {
        "status": "ok",
        "data": {
            "id": report.id,
            "judul": getattr(report, "judul", "-"),
            "region_id": getattr(report, "region_id", "-"),
            "content": getattr(report, "content", "-"),
        },
    }


# ======================================================
# 📊 RULES SUMMARY
# ======================================================

@router.get("/rules/summary")
async def get_rules_summary(
    diagnosis: str = Query(...),
    rs_id: str | None = Query(None),
    region_id: str | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("doctor", "verifikator", "coder", "admin_rs", "superadmin")),
):
    """Ringkasan aturan multilayer per layer untuk diagnosis tertentu."""
    try:
        return regulation_service.get_rules_summary(db, diagnosis, rs_id, region_id)
    except Exception as e:
        print(f"[RULES_SUMMARY] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal ambil summary regulasi: {e}")


# ======================================================
# 🧱 8-LAYER INFO
# ======================================================

@router.get("/rules/layers")
async def get_layer_info(
    user=Depends(require_roles_session("doctor", "verifikator", "coder", "admin_rs", "superadmin")),
):
    """Informasi struktur 8 layer regulasi dan prioritasnya."""
    return regulation_service.get_layer_info()


# ======================================================
# 📊 REGIONAL REPORT DETAIL
# ======================================================

@router.get("/api/regional-reports/{report_id}")
async def get_regional_report_detail(
    report_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("superadmin", "admin_rs")),
):
    """Ambil detail laporan regional dari tabel RegionalReports."""
    try:
        report = db.query(models.RegionalReports).filter_by(id=report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Regional report tidak ditemukan")

        return {
            "status": "success",
            "message": "Regional report berhasil diambil",
            "data": {
                "id": report.id,
                "judul": getattr(report, "judul", "-"),
                "region_id": getattr(report, "region_id", "-"),
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "updated_at": report.updated_at.isoformat() if report.updated_at else None,
                "content": getattr(report, "content", "-"),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[REGIONAL_REPORT] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal ambil laporan regional: {e}")
