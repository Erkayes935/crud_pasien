import os, json
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database_connection import SessionLocal, get_db_session
from models import RulesMaster

BASE_RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "rules")

def load_json(filename):
    filepath = os.path.join(BASE_RULES_PATH, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_diagnosis_rule(diagnosis_name):
    filename = f"diagnosis/{diagnosis_name.lower().replace(' ', '_')}.json"
    filepath = os.path.join(BASE_RULES_PATH, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ============== RULE FILES ==============
icd10_rules   = load_json("icd10_mapping.json")
icd9_rules    = load_json("icd9_mapping.json")
fornas_rules  = load_json("fornas.json")
inacbg_rules  = load_json("ina_cbg.json")
cp_pnpk_rules = load_json("cp_pnpk.json")

LAYER_PRIORITIES = {
    "permenkes": 1,
    "nasional": 2,
    "ppk": 3,
    "regional": 4,
    "rs": 5,
    "bridging": 6,
    "fraud": 7,
    "temporary": 8
}

# ==========================================================
# 🔹 Revised: support per-scope loading (diagnosis / tindakan / idrg)
# ==========================================================
def load_rules_for_diagnosis(diagnosis, rs_id=None, region_id=None, scope: str = "diagnosis", procedure: Optional[str] = None):
    """
    Load dan merge multilayer rules untuk diagnosis tertentu berdasarkan scope.
    Scope default = 'diagnosis' agar backward compatible.

    Args:
        diagnosis (str): Nama diagnosis (e.g., "Pneumonia")
        rs_id (str): ID rumah sakit (opsional)
        region_id (str): ID wilayah (opsional)
        scope (str): Jenis aturan ("diagnosis", "tindakan", "idrg", dst.)
        procedure (str): Nama tindakan (opsional, hanya untuk scope='tindakan')

    Returns:
        dict: Hasil merge rules multilayer
    """
    db = SessionLocal()
    try:
        query = db.query(RulesMaster).filter(
            RulesMaster.diagnosis.ilike(f"%{diagnosis}%"),
            RulesMaster.status.in_(["official", "active"])
        )

        # 🔸 filter scope
        if hasattr(RulesMaster, "scope"):
            query = query.filter(RulesMaster.scope == scope)

        # 🔸 jika scope = tindakan, filter berdasarkan nama prosedur
        if procedure and hasattr(RulesMaster, "procedure"):
            query = query.filter(RulesMaster.procedure.ilike(f"%{procedure}%"))

        rules = query.all()
        print(f"🔍 Found {len(rules)} rules for {scope}: {diagnosis} ({procedure or '-'})")

        merged_rules = {}
        for rule in rules:
            field = rule.field
            layer = rule.layer

            if field not in merged_rules:
                merged_rules[field] = []

            rule_data = {
                "layer": layer,
                "isi": rule.isi,
                "sumber": rule.sumber,
                "priority": LAYER_PRIORITIES.get(layer, 99),
                "rs_specific": bool(rule.rs_id),
                "region_specific": bool(rule.region_id),
                "scope": getattr(rule, "scope", None),
                "procedure": getattr(rule, "procedure", None)
            }
            merged_rules[field].append(rule_data)

        # 🔸 Sorting sesuai prioritas
        for field, items in merged_rules.items():
            for r in items:
                if r["rs_specific"]:
                    r["priority"] = 0
            items.sort(key=lambda x: x["priority"])

        return {
            "diagnosis": diagnosis,
            "scope": scope,
            "procedure": procedure,
            "rs_id": rs_id,
            "region_id": region_id,
            "rules": merged_rules,
            "total_rules": len(rules)
        }
    finally:
        db.close()


def get_active_rule_for_field(diagnosis, field, rs_id=None, region_id=None, scope="diagnosis"):
    """Ambil rule aktif (prioritas tertinggi) untuk 1 field"""
    all_rules = load_rules_for_diagnosis(diagnosis, rs_id, region_id, scope)
    field_rules = all_rules["rules"].get(field, [])
    if field_rules:
        return field_rules[0]
    return None


def get_rules_summary(diagnosis, rs_id=None, region_id=None, scope="diagnosis"):
    """Ringkasan rules per-layer"""
    all_rules = load_rules_for_diagnosis(diagnosis, rs_id, region_id, scope)
    summary = {}
    for field, rules in all_rules["rules"].items():
        for rule in rules:
            layer = rule["layer"]
            if layer not in summary:
                summary[layer] = []
            summary[layer].append({
                "field": field,
                "isi": rule["isi"],
                "sumber": rule["sumber"]
            })
    return {
        "diagnosis": diagnosis,
        "scope": scope,
        "layers": summary,
        "total_layers": len(summary)
    }


# ==========================================================
# 🔹 Fungsi lama tetap dipertahankan, otomatis pakai scope='diagnosis'
# ==========================================================
def load_rules_multilayer(diagnoses: list, rs_id=None, region_id=None, scope="diagnosis", procedure=None) -> dict:
    """
    Gabungkan multilayer rules dari DB + JSON nasional.
    (Tetap untuk scope diagnosis agar kompatibel ke belakang.)
    """
    merged = {}
    if not diagnoses:
        print("[RULES_LOADER] Warning: Empty diagnoses list")
        return {}

    try:
        for d in diagnoses:
            if not d or d.strip() == "":
                continue

            # gunakan loader per-scope
            dx_rules = load_rules_for_diagnosis(d, rs_id, region_id, scope=scope, procedure=procedure)
            if not dx_rules or "rules" not in dx_rules:
                continue

            for field, items in dx_rules["rules"].items():
                if field not in merged:
                    merged[field] = []
                if isinstance(items, list):
                    merged[field].extend(items)
                else:
                    merged[field].append(items)

        # tambahkan global JSON hanya jika scope diagnosis (agar tidak dobel di tindakan/idrg)
        if scope == "diagnosis":
            if "icd10_mapping" not in merged and icd10_rules:
                merged["icd10_mapping"] = [{
                    "layer": "nasional",
                    "sumber": "ICD-10 WHO",
                    "isi": icd10_rules,
                    "priority": LAYER_PRIORITIES.get("nasional", 2)
                }]
            if "icd9_mapping" not in merged and icd9_rules:
                merged["icd9_mapping"] = [{
                    "layer": "nasional",
                    "sumber": "ICD-9-CM",
                    "isi": icd9_rules,
                    "priority": LAYER_PRIORITIES.get("nasional", 2)
                }]
            if "ina_cbg" not in merged and inacbg_rules:
                merged["ina_cbg"] = [{
                    "layer": "nasional",
                    "sumber": "INA-CBG",
                    "isi": inacbg_rules,
                    "priority": LAYER_PRIORITIES.get("nasional", 2)
                }]

        # sort semua list by priority
        for field, value in merged.items():
            if not isinstance(value, list):
                merged[field] = [value]
            merged[field].sort(key=lambda x: x.get("priority", 99))

        return merged
    except Exception as e:
        print(f"[RULES_LOADER] Error in load_rules_multilayer: {e}")
        return {}