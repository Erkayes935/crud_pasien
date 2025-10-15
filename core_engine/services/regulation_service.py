from datetime import date
from typing import List, Dict
from sqlalchemy import or_
from ..database import SessionLocal
from ..models import RulesMaster

def process_regulation_detail(payload: dict, field: str):
    """
    Ambil regulasi multilayer (DB + JSON).
    Jika kosong, fallback ke AI generator.
    Output: satu list berisi aturan dari berbagai layer (untuk 1 modal tabel).
    """
    claim_id  = payload.get("claim_id")
    kategori  = payload.get("kategori") or payload.get("diagnosis") or ""
    rs_id     = payload.get("rs_id")
    region_id = payload.get("region_id")
    original_field = field

    print(f"[CORE_ENGINE] ⚙️ process_regulation_detail for '{field}' ({kategori})")

    try:
        # 1️⃣ Ambil dari DB / multilayer JSON (logika milikmu)
        results = get_rules_from_db_or_json(payload, field)

        # 2️⃣ Jika kosong → fallback ke AI multilayer generator
        if not results or (len(results) == 1 and results[0].get("layer") == "default"):
            print(f"[CORE_ENGINE] No rules found for {field}, using AI fallback")
            ai_result = generate_ai_rules_for_field(field, kategori)
            results = ai_result.get("data", [])

        # 3️⃣ Format output sederhana (untuk tabel tunggal di UI)
        return {
            "status": "success",
            "claim_id": claim_id,
            "field": original_field,
            "diagnosis": kategori,
            "data": results,
            "total_rules": len(results),
            "engine_version": f"regulation_flat@{date.today().isoformat()}"
        }

    except Exception as e:
        print(f"[CORE_ENGINE] ❌ Error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "data": [{
                "layer": "error",
                "sumber": "System",
                "isi": f"Terjadi kesalahan: {e}",
                "update": None,
                "status": "Error",
                "color": "#ef4444",
            }]
        }


def get_rules_from_db_or_json(payload: dict, field: str) -> List[Dict]:
    """Logika pengambilan aturan multilayer dari DB (punyamu sebelumnya)"""
    db = SessionLocal()
    kategori  = payload.get("kategori") or payload.get("diagnosis") or ""
    rs_id     = payload.get("rs_id")
    region_id = payload.get("region_id")

    try:
        field_aliases = get_field_aliases(field)
        q = db.query(RulesMaster).filter(or_(*[RulesMaster.field == a for a in field_aliases]))

        if kategori:
            q = q.filter(RulesMaster.diagnosis.ilike(f"%{kategori}%"))

        matched_rules = q.all()
        print(f"[CORE_ENGINE] Found {len(matched_rules)} rules in DB")

        results = []
        for rule in matched_rules:
            if rule.rs_id and rs_id and rule.rs_id.lower() != rs_id.lower():
                continue
            if rule.region_id and region_id and rule.region_id.lower() != region_id.lower():
                continue

            results.append({
                "layer": rule.layer or "nasional",
                "sumber": rule.sumber or f"Aturan {rule.layer.upper()}",
                "isi": format_rule_content(rule.isi),
                "update": rule.updated_at.strftime("%Y-%m-%d") if rule.updated_at else "-",
                "status": rule.status.capitalize() if rule.status else "Unverified",
                "color": get_layer_color(rule.layer),
            })

        # urutkan RS > regional > nasional > lainnya
        order = ["rs", "regional", "nasional", "permenkes", "ppk", "bridging", "fraud", "temporary", "default"]
        results.sort(key=lambda r: order.index(r["layer"]) if r["layer"] in order else 999)

        if not results:
            results = [{
                "layer": "default",
                "sumber": f"Aturan umum untuk field '{field}'",
                "isi": f"Tidak ada regulasi spesifik untuk '{field}' dan diagnosis '{kategori}'.",
                "update": "-",
                "status": "Default",
                "color": "#9ca3af"
            }]
        return results
    finally:
        db.close()


# 🔹 Reuse dari temanmu
def generate_ai_rules_for_field(field_name: str, diagnosis_name: str):
    """AI fallback generator versi ringkas"""
    try:
        sources = ["Permenkes", "PNPK", "BPJS"]
        rules = []
        for src in sources:
            rules.append({
                "layer": map_source_to_layer(src),
                "sumber": src,
                "isi": generate_rule_content(src, field_name, diagnosis_name),
                "update": date.today().isoformat(),
                "status": "AI-Generated",
                "color": get_layer_color(map_source_to_layer(src)),
            })
        return {"status": "success", "data": rules}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Helper dari temanmu (ringkas)
def map_source_to_layer(source: str) -> str:
    mapping = {
        "Permenkes": "permenkes",
        "PNPK": "nasional",
        "BPJS": "regional",
        "CP": "ppk"
    }
    return mapping.get(source, "nasional")


def generate_rule_content(source: str, field_name: str, diagnosis_name: str) -> str:
    templates = {
        "PNPK": f"Field {field_name} mengikuti kriteria klinis PNPK {diagnosis_name}",
        "Permenkes": f"Field {field_name} diatur sesuai Permenkes untuk {diagnosis_name}",
        "BPJS": f"Ketentuan BPJS untuk {diagnosis_name} terkait {field_name}",
    }
    return templates.get(source, f"Aturan umum untuk {field_name}")


def get_layer_color(layer):
    """Warna konsisten antar layer"""
    colors = {
        "nasional": "#3b82f6",
        "regional": "#22c55e", 
        "rs": "#eab308",
        "bridging": "#a855f7",
        "fraud": "#ef4444",
        "temporary": "#9ca3af",
        "default": "#9ca3af",
        "error": "#ef4444"
    }
    return colors.get(layer, "#3b82f6")
