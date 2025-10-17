#!/usr/bin/env python3
"""
Test script untuk menguji semua read-only endpoints yang sudah diimplementasi
untuk akses verificator ke data yang disimpan doctor.
"""

import requests
import json

base_url = 'http://127.0.0.1:8001'  # Web service port
claim_id = 107

print('=== Testing Read-Only Endpoints for Verificator ===')
print()

# Create session for authentication
session = requests.Session()

# Try to login first (we'll use doctor to test read-only access)
print('🔐 Step 0: Authentication')
print('-' * 40)

# Login credentials for doctor (yang punya data)
login_data = {
    'username': 'yey@mail.com',
    'password': 'CE4tL4nSmiR9sq3'
}

try:
    login_response = session.post(f'{base_url}/login', data=login_data)
    if login_response.status_code in [200, 302]:  # 200 for API, 302 for redirect
        print('✅ Login successful')
        # Session now has authentication cookies
    else:
        print(f'⚠️  Login failed: {login_response.status_code}')
        print('   Trying without authentication...')
except Exception as e:
    print(f'⚠️  Login error: {str(e)}')
    print('   Trying without authentication...')

print()

# Headers for requests
headers = {'Content-Type': 'application/json'}

# Test 1: Stored Data Summary
print('🔍 Test 1: Stored Data Summary')
print('-' * 40)
try:
    response = session.get(f'{base_url}/claims/{claim_id}/stored-data-summary', headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f'✅ Summary loaded successfully')
        print(f'   📊 Diagnoses: {data["summary"]["statistics"]["total_diagnoses"]}')
        print(f'   🔧 Procedures: {data["summary"]["statistics"]["total_procedures"]} (Modal: {data["summary"]["statistics"]["modal_procedures"]})')
        print(f'   📋 Regulations: {data["summary"]["statistics"]["total_regulations"]}')
        print(f'   🏥 IDRG Records: {data["summary"]["statistics"]["idrg_records"]}')
        print(f'   📈 Data Richness: {data["summary"]["statistics"]["data_richness_score"]}/100')
        
        # Store summary for other tests
        global_summary = data
    else:
        print(f'❌ Failed: {response.status_code} - {response.text}')
        global_summary = None
except Exception as e:
    print(f'❌ Error: {str(e)}')
    global_summary = None

print()

# Test 2: Stored Diagnosis Detail (using first diagnosis if exists)
print('🔍 Test 2: Stored Diagnosis Detail')
print('-' * 40)
try:
    if global_summary and global_summary['summary']['diagnoses']:
        first_diagnosis = global_summary['summary']['diagnoses'][0]
        diag_name = first_diagnosis['name']
        
        response = session.get(f'{base_url}/claims/{claim_id}/stored-diagnosis-detail/{diag_name}', headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f'✅ Diagnosis detail loaded: {diag_name}')
            print(f'   🔧 Related procedures: {len(data.get("tindakan", []))}')
            print(f'   📋 Regulations: {len(data.get("regulasi", []))}')
            print(f'   🏥 IDRG data: {"Available" if data.get("idrg_data") else "None"}')
            print(f'   🔒 Read-only mode: {data.get("read_only_mode", False)}')
        else:
            print(f'❌ Failed: {response.status_code} - {response.text}')
    else:
        print('⚠️  No diagnoses found to test')
except Exception as e:
    print(f'❌ Error: {str(e)}')

print()

# Test 3: Stored Procedure Detail (using first procedure if exists)
print('🔍 Test 3: Stored Procedure Detail')
print('-' * 40)
try:
    if global_summary and global_summary['summary']['procedures']:
        first_procedure = global_summary['summary']['procedures'][0]
        proc_name = first_procedure['name']
        
        response = session.get(f'{base_url}/claims/{claim_id}/stored-procedure-detail/{proc_name}', headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f'✅ Procedure detail loaded: {proc_name}')
            print(f'   📋 Analysis details: {"Available" if data.get("analysis") else "None"}')
            print(f'   📋 Regulations: {len(data.get("regulasi", []))}')
            print(f'   🔒 Read-only mode: {data.get("read_only_mode", False)}')
        else:
            print(f'❌ Failed: {response.status_code} - {response.text}')
    else:
        print('⚠️  No procedures found to test')
except Exception as e:
    print(f'❌ Error: {str(e)}')

print()

# Test 4: Stored Regulation Detail
print('🔍 Test 4: Stored Regulation Detail')
print('-' * 40)
try:
    response = session.get(f'{base_url}/claims/{claim_id}/stored-regulation-detail/diagnosis', headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f'✅ Regulation detail loaded for field: diagnosis')
        print(f'   📋 Regulation count: {len(data.get("regulations", []))}')
        print(f'   🔒 Read-only mode: {data.get("read_only_mode", False)}')
    else:
        print(f'❌ Failed: {response.status_code} - {response.text}')
except Exception as e:
    print(f'❌ Error: {str(e)}')

print()
print('=== Read-Only Endpoints Testing Complete ===')