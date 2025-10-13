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