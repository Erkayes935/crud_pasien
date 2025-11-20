"""
routers/claim/claim_diagnosis_router.py
Refactor modular dari claim_router.py
Fokus: endpoint diagnosis detail (verifikator) dengan AI fallback.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import require_roles_session
from backend import models

router = APIRouter(tags=["Claim Diagnoses"])


# ======================================================
# 🩺 STORED DIAGNOSIS DETAIL (VERIFIKATOR VIEW)
# ======================================================

@router.get("/{claim_id}/stored-diagnosis-detail/{diagnosis_name}", name="get_stored_diagnosis_detail")
async def get_stored_diagnosis_detail(
    claim_id: int,
    diagnosis_name: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles_session("verifikator", "coder", "admin_rs", "superadmin")),
):
    """
    Read-only endpoint untuk verifikator:
    - Menampilkan detail diagnosis yang sudah disimpan dokter.
    - Jika data kosong, fallback otomatis ke core_engine (AI).
    - Struktur hasil sama dengan /analyze_diagnosis milik dokter.
    """
    try:
        print(f"[STORED_DIAGNOSIS_DETAIL] Loading stored data for claim {claim_id}, diagnosis: {diagnosis_name}")

        # 🔍 Ambil diagnosis di DB
        diagnosis = (
            db.query(models.ClaimDiagnosis)
            .filter(
                models.ClaimDiagnosis.claim_id == claim_id,
                models.ClaimDiagnosis.diagnosis_text.ilike(f"%{diagnosis_name}%"),
                models.ClaimDiagnosis.is_deleted == False,
            )
            .first()
        )

        if not diagnosis:
            raise HTTPException(status_code=404, detail=f"Stored diagnosis '{diagnosis_name}' not found")

        # 🔍 Ambil tarif INA-CBG (kalau ada)
        tariff = (
            db.query(models.ClaimTariff)
            .filter_by(claim_id=claim_id, is_deleted=False)
            .order_by(models.ClaimTariff.updated_at.desc())
            .first()
        )

        # ==== kalau data klinis kosong, auto fallback ke AI ====
        is_empty = not (diagnosis.justifikasi_klinis or diagnosis.syarat_klinis or diagnosis.bukti_klinis)
        if is_empty:
            try:
                print("[STORED_DIAGNOSIS_DETAIL] ⚠️ Empty record, requesting AI fallback...")
                from ...services import claim_ai

                payload = {
                    "claim_id": claim_id,
                    "disease_name": diagnosis_name,
                    "stage": "admission",
                }
                ai_result = await claim_ai.proxy_core_engine("/analyze_diagnosis", payload)
                print("[STORED_DIAGNOSIS_DETAIL] ✅ Got AI fallback result")

                flattened = ai_result.get("data") if isinstance(ai_result, dict) and "data" in ai_result else ai_result
                return {
                    "status": "success",
                    "mode": "ai_fallback",
                    "claim_id": claim_id,
                    "diagnosis_name": diagnosis_name,
                    "read_only_mode": True,
                    "message": "⚙️ Data kosong, diambil langsung dari AI (flattened untuk FE)",
                    "data": flattened,
                }

            except Exception as e:
                print(f"[STORED_DIAGNOSIS_DETAIL] ❌ AI fallback failed: {e}")

        print(f"[STORED_DIAGNOSIS_DETAIL] is_empty? {is_empty}")
        print(f"[STORED_DIAGNOSIS_DETAIL] ✅ Sending stored data in doctor-like format")

        # ==== kalau data ada, kirim dari DB ====
        result = {
            "status": "success",
            "mode": "stored_data",
            "claim_id": claim_id,
            "diagnosis_name": diagnosis_name,
            "read_only_mode": True,
            "message": f"✅ Stored data loaded successfully for '{diagnosis_name}'",
            "data": {
                "klinis": {
                    "justifikasi": diagnosis.justifikasi_klinis or "Belum diisi oleh doctor",
                    "bukti_klinis": diagnosis.bukti_klinis or "Belum diisi oleh doctor",
                    "syarat_klinis": diagnosis.syarat_klinis or "Belum diisi oleh doctor",
                },
                "icd10": {
                    "kode_icd": diagnosis.icd10_code or "-",
                    "kode_ganda": diagnosis.kode_ganda_icd10 or "-",
                    "z_code": diagnosis.z_code_icd10 or "-",
                },
                "faskes": {
                    "tingkat": diagnosis.tingkat_faskes or "-",
                    "justifikasi": diagnosis.justifikasi_faskes or "-",
                    "kompetensi": diagnosis.kompetensi_faskes or "-",
                },
                "rawat_inap": {
                    "lama_rawat": diagnosis.lama_rawat_inap or "-",
                    "indikasi": diagnosis.indikasi_rawat_inap or "-",
                    "kriteria": diagnosis.kriteria_rawat_inap or "-",
                },
                "rujukan": {
                    "indikasi": diagnosis.indikasi_rujukan or "-",
                    "kriteria": diagnosis.kriteria_rujukan or "-",
                    "tujuan": diagnosis.tujuan_rujukan or "-",
                },
                "inaCbg": {
                    "kode": tariff.cbg_code if tariff else "-",
                    "tarif": (
                        f"Rp{int(tariff.tariff_amount):,}".replace(",", ".")
                        if tariff and tariff.tariff_amount
                        else "-"
                    ),
                    "deskripsi": tariff.description if tariff else "-",
                },
                "aspek_lainnya": (
                    json.dumps(diagnosis.aspek_lainnya, ensure_ascii=False, indent=2)
                    if isinstance(diagnosis.aspek_lainnya, (dict, list))
                    else (diagnosis.aspek_lainnya or "-")
                ),
            },
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[STORED_DIAGNOSIS_DETAIL] ❌ Error: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load stored diagnosis detail: {e}")
