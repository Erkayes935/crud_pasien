import os, json
import sys
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Import dari core_engine
from database_connection import SessionLocal, get_db_session
from models import RulesMaster

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

# Layer priorities (lower number = higher priority)
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

def load_rules_for_diagnosis(diagnosis, rs_id=None, region_id=None):
    """
    Load dan merge rules multilayer untuk diagnosis tertentu
    
    Args:
        diagnosis (str): Nama diagnosis (e.g., "Pneumonia")
        rs_id (str): ID rumah sakit
        region_id (str): ID wilayah/region
        
    Returns:
        dict: Merged rules dari semua layer yang berlaku
    """
    db = SessionLocal()
    try:
        # Query rules yang berlaku
        query = db.query(RulesMaster).filter(
            RulesMaster.diagnosis.ilike(f"%{diagnosis}%"),
            RulesMaster.status == "official"
        )
        
        # Filter berdasarkan rs_id dan region_id
        rules = query.filter(
            (RulesMaster.rs_id == rs_id) |
            (RulesMaster.region_id == region_id) |
            (RulesMaster.rs_id.is_(None) & RulesMaster.region_id.is_(None))
        ).all()
                
        # Group rules by field dan sort by priority
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
                "rs_specific": rule.rs_id is not None,
                "region_specific": rule.region_id is not None
            }
                        
            merged_rules[field].append(rule_data)
        
        # Sort rules by priority (RS rules override others)
        for field in merged_rules:
            # RS rules get priority boost
            for rule in merged_rules[field]:
                if rule["rs_specific"]:
                    rule["priority"] = 0  # Highest priority
            
            merged_rules[field].sort(key=lambda x: x["priority"])
        
        return {
            "diagnosis": diagnosis,
            "rs_id": rs_id,
            "region_id": region_id,
            "rules": merged_rules,
            "total_rules": len(rules)
        }
        
    finally:
        db.close()

def get_active_rule_for_field(diagnosis, field, rs_id=None, region_id=None):
    """Get the active (highest priority) rule for a specific field"""
    all_rules = load_rules_for_diagnosis(diagnosis, rs_id, region_id)
    field_rules = all_rules["rules"].get(field, [])
    
    if field_rules:
        return field_rules[0]  # Highest priority rule
    return None

def get_rules_summary(diagnosis, rs_id=None, region_id=None):
    """Get summary of rules by layer"""
    all_rules = load_rules_for_diagnosis(diagnosis, rs_id, region_id)
    
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
        "layers": summary,
        "total_layers": len(summary)
    }

def load_rules_multilayer(diagnoses: list, rs_id=None, region_id=None) -> dict:
    """
    Gabungkan rules multilayer dari DB + JSON nasional untuk kombinasi diagnosis & tindakan.
    """
    # Initialize merged dictionary
    merged = {}
    
    try:
        # Skip processing if empty diagnoses list
        if not diagnoses or len(diagnoses) == 0:
            print("[RULES_LOADER] Warning: Empty diagnoses list")
            return {}
            
        # 1. Process rules from database for each diagnosis
        for d in diagnoses:
            # Skip empty diagnoses
            if not d or d.strip() == "":
                continue
                
            dx_rules = load_rules_for_diagnosis(d, rs_id, region_id)
            if not dx_rules or not isinstance(dx_rules, dict) or "rules" not in dx_rules:
                print(f"[RULES_LOADER] Warning: No rules found for diagnosis '{d}'")
                continue
                
            # Merge rules for each field into the merged dictionary
            for field, items in dx_rules["rules"].items():
                if field not in merged:
                    merged[field] = []
                    
                # Always ensure we're extending a list
                if isinstance(items, list):
                    merged[field].extend(items)
                else:
                    merged[field].append(items)

        # 2. Add global/national rules that are not diagnosis-specific
        
        # Handle ICD10 rules
        if "icd10_mapping" not in merged:
            merged["icd10_mapping"] = []
            
        # Add ICD10 rules if they exist, converting to list item if necessary
        if icd10_rules:
            if isinstance(icd10_rules, dict):
                merged["icd10_mapping"].append({
                    "layer": "nasional",
                    "sumber": "ICD-10 WHO",
                    "isi": icd10_rules,
                    "priority": LAYER_PRIORITIES.get("nasional", 2)
                })
            elif isinstance(icd10_rules, list):
                merged["icd10_mapping"].extend(icd10_rules)
        
        # Handle ICD9 rules
        if "icd9_mapping" not in merged:
            merged["icd9_mapping"] = []
            
        # Add ICD9 rules if they exist, converting to list item if necessary  
        if icd9_rules:
            if isinstance(icd9_rules, dict):
                merged["icd9_mapping"].append({
                    "layer": "nasional",
                    "sumber": "ICD-9-CM",
                    "isi": icd9_rules,
                    "priority": LAYER_PRIORITIES.get("nasional", 2)
                })
            elif isinstance(icd9_rules, list):
                merged["icd9_mapping"].extend(icd9_rules)
                
        # Handle INACBG rules
        if "ina_cbg" not in merged:
            merged["ina_cbg"] = []
            
        # Add INACBG rules if they exist, converting to list item if necessary
        if inacbg_rules:
            if isinstance(inacbg_rules, dict):
                merged["ina_cbg"].append({
                    "layer": "nasional", 
                    "sumber": "INA-CBG",
                    "isi": inacbg_rules,
                    "priority": LAYER_PRIORITIES.get("nasional", 2)
                })
            elif isinstance(inacbg_rules, list):
                merged["ina_cbg"].extend(inacbg_rules)
        
        # 3. CRITICAL: Ensure ALL values are lists before sorting
        for field_name in list(merged.keys()):
            field_value = merged[field_name]
            
            # Fix non-list values
            if not isinstance(field_value, list):
                print(f"[RULES_LOADER] Converting non-list field '{field_name}' to list")
                if field_value is None:
                    merged[field_name] = []
                else:
                    merged[field_name] = [field_value]
        
        # 4. Sort fields only if they contain lists
        for field_name in list(merged.keys()):
            field_value = merged[field_name]
            
            # Attempt to sort only if it's a list
            if isinstance(field_value, list):
                try:
                    field_value.sort(key=lambda x: x.get("priority", 99) if isinstance(x, dict) else 99)
                except Exception as e:
                    print(f"[RULES_LOADER] Sort error for field '{field_name}': {e}")
        
        return merged
        
    except Exception as e:
        print(f"[RULES_LOADER] Error in load_rules_multilayer: {e}")
        return {}  # Return empty dict on error
