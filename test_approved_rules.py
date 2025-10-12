#!/usr/bin/env python3
"""
Test script to verify rules loader works with approved rules
"""
import sys
import os
sys.path.append('core_engine')

from services.rules_loader import load_rules_for_diagnosis

def test_approved_rule():
    print("🧪 Testing Rules Loader with Official Rules")
    print("=" * 50)
    
    # Test load rules untuk Hipertensi Esensial dengan rs_id rs_2
    result = load_rules_for_diagnosis('Hipertensi Esensial', rs_id='rs_2')
    
    print(f"✅ Rules loaded successfully!")
    print(f"Total rules: {len(result['rules'])}")
    print(f"Diagnosis: {result['diagnosis']}")
    print()
    
    for field, rules in result['rules'].items():
        print(f"📋 Field: {field}")
        for rule in rules:
            status = rule.get('status', 'N/A')
            layer = rule['layer']
            source = rule['sumber'][:50] + "..." if len(rule['sumber']) > 50 else rule['sumber']
            print(f"  ├─ Layer: {layer} | Status: {status}")
            print(f"  └─ Source: {source}")
        print()

if __name__ == '__main__':
    test_approved_rule()