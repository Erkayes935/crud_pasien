# ==================================================
# REGULATION SERVICE (Multilayer Rules & Summary)
# ==================================================

from sqlalchemy.orm import Session
from datetime import datetime
import os, requests, json
from fastapi import HTTPException
from .. import models


# ==================================================
# 1️⃣ CORE ENGINE PROXY - MULTILAYER LOAD
# ==================================================

def load_multilayer_rules(db: Session, diagnosis: str, rs_id: str = None, region_id: str = None, claim_id: int = None):
    """
    Load multilayer rules dari core_engine service.
    Menggabungkan regulasi nasional dan lokal sesuai RS & region.
    """
    try:
        # 🔍 kalau diagnosis berupa field (contoh 'z_code', 'syarat_klinis'),
        # coba ambil diagnosis utama dari ClaimDiagnosis di DB
        from backend.models import ClaimDiagnosis
        if diagnosis and len(diagnosis) <= 20:  # indikasi ini field, bukan nama penyakit
            possible_diag = (
                db.query(ClaimDiagnosis.diagnosis_text)
                .filter(ClaimDiagnosis.is_deleted == False)
                .filter(ClaimDiagnosis.claim_id == claim_id)
                .first()
            )
            if possible_diag and possible_diag[0]:
                print(f"[REGULATION_SERVICE] 🧭 Fallback diagnosis → {possible_diag[0]}")
                diagnosis = possible_diag[0]
            else:
                print(f"[REGULATION_SERVICE] ⚠️ Tidak ditemukan ClaimDiagnosis untuk claim_id={claim_id}")

        core_engine_url = os.getenv("CORE_ENGINE_URL", "http://core_engine:8002")
        payload = {"diagnosis": diagnosis}
        if rs_id:
            payload["rs_id"] = rs_id
        if region_id:
            payload["region_id"] = region_id

        response = requests.post(f"{core_engine_url}/regulation_detail", json=payload, timeout=30)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Core engine error: {response.text}")

        data = response.json()
        print(f"[REGULATION_SERVICE] ✅ Loaded {data.get('total_rules', 0)} rules for {diagnosis} (RS: {rs_id})")

        return {
            "status": "success",
            "diagnosis": diagnosis,
            "rs_id": rs_id,
            "region_id": region_id,
            "total_rules": data.get("total_rules", 0),
            "rules": data.get("rules", []),
            "engine_version": f"multilayer@{datetime.now().strftime('%Y-%m-%d')}"
        }

    except Exception as e:
        print(f"[REGULATION_SERVICE] ❌ Error load_multilayer_rules: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load multilayer rules: {str(e)}")



# ==================================================
# 2️⃣ RULES SUMMARY PER LAYER
# ==================================================

def get_rules_summary(db: Session, diagnosis: str, rs_id: str = None, region_id: str = None):
    """
    Ambil ringkasan jumlah aturan per layer (1-8).
    Kombinasi dari database + core_engine summary.
    """
    try:
        core_engine_url = os.getenv("CORE_ENGINE_URL", "http://core_engine:8002")
        payload = {"diagnosis": diagnosis}
        if rs_id:
            payload["rs_id"] = rs_id
        if region_id:
            payload["region_id"] = region_id

        response = requests.post(f"{core_engine_url}/rules/summary", json=payload, timeout=30)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        core_summary = response.json()

        # Tambahkan ringkasan dari DB (layer 3 & 5)
        db_rules = db.query(models.RulesMaster).filter(
            models.RulesMaster.diagnosis.ilike(f"%{diagnosis}%")
        ).all()

        layer_count = {}
        for rule in db_rules:
            layer_count[rule.layer] = layer_count.get(rule.layer, 0) + 1

        merged = {
            "diagnosis": diagnosis,
            "core_engine_summary": core_summary,
            "db_layers": layer_count,
            "timestamp": datetime.now().isoformat()
        }

        print(f"[REGULATION_SERVICE] ✅ Summary merged for {diagnosis}: {merged}")
        return merged

    except Exception as e:
        print(f"[REGULATION_SERVICE] ❌ Error get_rules_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to summarize multilayer rules: {str(e)}")


# ==================================================
# 3️⃣ STATIC INFO: 8 LAYER STRUCTURE
# ==================================================

def get_layer_info():
    """Kembalikan struktur 8 layer dengan prioritas override."""
    return {
        "status": "success",
        "layers": [
            {"id": "permenkes", "name": "Permenkes/BPJS Pusat", "priority": 1, "source": "Regulasi resmi", "override": False},
            {"id": "nasional", "name": "Nasional (CP/PNPK/FORNAS/ICD/INA-CBG)", "priority": 2, "source": "Kemenkes/WHO", "override": False},
            {"id": "ppk", "name": "PPK RS", "priority": 3, "source": "Dokumen PPK RS", "override": True},
            {"id": "regional", "name": "Regional (Wilayah/SE BPJS Cabang)", "priority": 4, "source": "SE BPJS/Dinkes", "override": False},
            {"id": "rs", "name": "RS Lokal (BA/SOP)", "priority": 5, "source": "BA/SOP RS", "override": True},
            {"id": "bridging", "name": "Bridging (Teknis SIMRS/BPJS)", "priority": 6, "source": "Panduan BPJS", "override": False},
            {"id": "fraud", "name": "Fraud Rules (AI Anti-Anomali)", "priority": 7, "source": "Model AI", "override": False},
            {"id": "temporary", "name": "Temporary Policy", "priority": 8, "source": "Kebijakan Nasional", "override": False}
        ],
        "priority_rule": "RS rules (layer 3 & 5) override semua layer di atasnya jika tersedia",
        "total_layers": 8,
        "engine_version": f"multilayer_system@{datetime.now().strftime('%Y-%m-%d')}"
    }


# ==================================================
# 4️⃣ STORED REGULATION (DB CACHE)
# ==================================================

def get_stored_regulation_detail(db: Session, claim_id: int, field_name: str):
    """
    Ambil regulasi yang sudah tersimpan di DB (ClaimRegulationDetail)
    jika tidak ada, fallback ke AI multilayer.
    """
    try:
        regulations = db.query(models.ClaimRegulationDetail).filter(
            models.ClaimRegulationDetail.claim_id == claim_id
        ).all()

        relevant_regs = [
            {
                "judul": reg.judul_regulasi,
                "dasar_hukum": reg.dasar_hukum or "",
                "isi": reg.isi or "",
                "layer": getattr(reg, "layer", "-"),
                "sumber": getattr(reg, "sumber", "-"),
            }
            for reg in regulations
            if field_name.lower() in (reg.judul_regulasi or "").lower()
            or field_name.lower() in (reg.isi or "").lower()
        ]

        if relevant_regs:
            print(f"[REGULATION_SERVICE] ✅ Found {len(relevant_regs)} stored rules for {field_name}")
            return {
                "status": "success",
                "mode": "stored_data",
                "claim_id": claim_id,
                "field_name": field_name,
                "regulations": relevant_regs,
                "read_only_mode": True,
            }

        # fallback ke AI jika kosong
        print(f"[REGULATION_SERVICE] ⚠️ Fallback ke AI multilayer (no stored rules)")
        core_engine_url = os.getenv("CORE_ENGINE_URL", "http://core_engine:8002")
        payload = {"claim_id": claim_id, "field": field_name}
        resp = requests.post(f"{core_engine_url}/rules/load", json=payload, timeout=30)

        rules = []
        if resp.status_code == 200:
            data = resp.json()
            rules = data.get("rules", [])

        if not rules:
            rules = [{
                "judul": f"Belum ada aturan untuk '{field_name}'",
                "isi": "-",
                "layer": "-",
                "sumber": "AI META"
            }]

        return {
            "status": "success",
            "mode": "ai_fallback",
            "claim_id": claim_id,
            "field_name": field_name,
            "regulations": rules,
            "read_only_mode": True,
        }

    except Exception as e:
        print(f"[REGULATION_SERVICE] ❌ Error get_stored_regulation_detail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get regulation detail: {str(e)}")
