"""
routers/claim/claim_procedure_router.py
Refactor modular dari claim_router.py
Fokus: endpoint procedure detail (verifikator) dengan AI fallback.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import require_roles_session
from backend import models

router = APIRouter(tags=["Claim Procedures"])


# ======================================================
# 🩺 STORED PROCEDURE DETAIL (VERIFIKATOR VIEW)
# ======================================================

@router.get("/{claim_id}/stored-procedure-detail/{procedure_name}", name="get_stored_procedure_detail")
async def get_stored_procedure_detail(
    claim_id: int,
    procedure_name: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator", "coder", "admin_rs", "superadmin")),
):
    """
    Read-only endpoint untuk verifikator:
    - Menampilkan detail tindakan/procedure yang sudah disimpan dokter.
    - Jika data kosong, fallback otomatis ke core_engine (AI).
    - Struktur hasil sama dengan /analyze_procedure milik dokter.
    """
    import json
    from ...services import claim_ai

    try:
        print(f"[STORED_PROCEDURE_DETAIL] Loading stored data for claim {claim_id}, procedure: {procedure_name}")

        # 🔍 Cari tindakan di database
        procedure = (
            db.query(models.ClaimProcedure)
            .filter(
                models.ClaimProcedure.claim_id == claim_id,
                models.ClaimProcedure.procedure_text.ilike(f"%{procedure_name}%"),
                models.ClaimProcedure.is_deleted == False,
            )
            .first()
        )

        if not procedure:
            raise HTTPException(status_code=404, detail=f"Stored procedure '{procedure_name}' not found")

        # 🔍 Ambil detail tindakan
        detail = (
            db.query(models.ClaimProcedureDetail)
            .filter(
                models.ClaimProcedureDetail.procedure_id == procedure.id,
                models.ClaimProcedureDetail.is_deleted == False,
            )
            .first()
        )

        # ==== ✅ Kalau ada data di DB ====
        if detail:
            related_regs = (
                db.query(models.ClaimRegulationDetail)
                .filter(
                    models.ClaimRegulationDetail.claim_id == claim_id,
                    models.ClaimRegulationDetail.procedure_id == procedure.id,
                )
                .all()
            )

            result = {
                "status": "success",
                "mode": "stored_data",
                "claim_id": claim_id,
                "procedure_name": procedure_name,
                "read_only_mode": True,
                "message": f"✅ Stored procedure loaded successfully for '{procedure_name}'",
                "data": {
                    "procedure_text": procedure.procedure_text,
                    "procedure_source": procedure.procedure_source,
                    "stage": procedure.stage,
                    "requirement_flag": procedure.requirement_flag,
                    "icd9_code": getattr(detail, "icd9_tindakan", "-"),
                    "validitas": getattr(detail, "validitas_tindakan", "Belum diverifikasi"),
                    "status_tindakan": getattr(detail, "status_tindakan", "Belum diisi oleh doctor"),
                    "ina_cbg": getattr(detail, "ina_cbg_tindakan", "Belum diisi oleh doctor"),
                    "faskes_tindakan": getattr(detail, "faskes_tindakan", "Belum diisi oleh doctor"),
                    "rawat_inap_tindakan": getattr(detail, "rawat_inap_tindakan", "Belum diisi oleh doctor"),
                    "syarat_klinis": getattr(detail, "syarat_klinis_tindakan", "Belum diisi oleh doctor"),
                    "deskripsi_tindakan": getattr(detail, "deskripsi_tindakan", "Belum diisi oleh doctor"),
                },
            }

            if related_regs:
                result["regulasi"] = [
                    {
                        "judul": reg.judul_regulasi,
                        "dasar_hukum": reg.dasar_hukum or "",
                        "bab_pasal": reg.bab_pasal or "",
                        "isi": reg.isi or "",
                    }
                    for reg in related_regs
                ]

            print(
                f"[STORED_PROCEDURE_DETAIL] ✅ Loaded stored data (regulasi={len(result.get('regulasi', []))})"
            )
            return result

        # ==== ⚙️ Kalau tidak ada di DB → fallback ke AI ====
        print(f"[STORED_PROCEDURE_DETAIL] ⚠️ No stored data found, requesting AI fallback for '{procedure_name}'...")
        payload = {"claim_id": claim_id, "procedure_text": procedure_name, "stage": "admission"}

        try:
            ai_result = await claim_ai.proxy_core_engine("/analyze_procedure", payload)
            print("[STORED_PROCEDURE_DETAIL] ✅ AI result type:", type(ai_result))

            data = ai_result.get("data") if isinstance(ai_result, dict) and "data" in ai_result else ai_result
            if not isinstance(data, dict):
                print("[STORED_PROCEDURE_DETAIL] ⚠️ AI result invalid, using dummy fallback")
                data = {}
        except Exception as e:
            print(f"[STORED_PROCEDURE_DETAIL] ❌ AI call failed: {e}")
            data = {}

        flat = {
            "icd9_code": data.get("icd9_code", "-"),
            "validitas": data.get("validitas", "Belum diverifikasi"),
            "status_tindakan": data.get("status_tindakan", "Belum diisi oleh doctor"),
            "ina_cbg": data.get("ina_cbg", "Belum diisi oleh doctor"),
            "faskes_tindakan": data.get("faskes_tindakan", "Belum diisi oleh doctor"),
            "rawat_inap_tindakan": data.get("rawat_inap_tindakan", "Belum diisi oleh doctor"),
            "syarat_klinis": data.get("syarat_klinis", "Belum diisi oleh doctor"),
            "deskripsi_tindakan": data.get("deskripsi_tindakan", "Belum diisi oleh doctor"),
        }

        print("[STORED_PROCEDURE_DETAIL] ✅ Got AI fallback result")
        print(json.dumps(flat, indent=2, ensure_ascii=False))

        return {
            **flat,
            "status": "success",
            "mode": "ai_fallback",
            "claim_id": claim_id,
            "procedure_name": procedure_name,
            "read_only_mode": True,
            "message": "🧠 Data kosong, diambil langsung dari AI (flattened for FE)",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[STORED_PROCEDURE_DETAIL] ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load stored procedure detail: {str(e)}")
