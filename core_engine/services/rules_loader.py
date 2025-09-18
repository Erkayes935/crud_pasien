import os, json

BASE_RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "rules")

def load_json(filename):
    """Helper untuk load file JSON"""
    filepath = os.path.join(BASE_RULES_PATH, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_diagnosis_rule(diagnosis_name):
    """Load file JSON spesifik diagnosis"""
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
