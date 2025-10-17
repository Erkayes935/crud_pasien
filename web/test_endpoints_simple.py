#!/usr/bin/env python3
"""
Test script sederhana untuk cek endpoint read-only tanpa authentication
Kita akan test apakah endpoint sudah terdaftar dengan benar
"""

import requests
import json

base_url = 'http://127.0.0.1:8001'
claim_id = 107

print('=== Testing Read-Only Endpoints (Simple Test) ===')
print()

# Test 1: Cek apakah endpoint terdaftar (akan dapat 401 jika terdaftar)
print('🔍 Test 1: Check if endpoints are registered')
print('-' * 50)

endpoints_to_test = [
    f'/claims/{claim_id}/stored-data-summary',
    f'/claims/{claim_id}/stored-diagnosis-detail/test',
    f'/claims/{claim_id}/stored-procedure-detail/test',
    f'/claims/{claim_id}/stored-regulation-detail/diagnosis'
]

for endpoint in endpoints_to_test:
    try:
        response = requests.get(f'{base_url}{endpoint}')
        if response.status_code == 401:
            print(f'✅ {endpoint} -> Endpoint found (needs auth)')
        elif response.status_code == 404:
            print(f'❌ {endpoint} -> Endpoint NOT found')
        elif response.status_code == 422:
            print(f'⚠️  {endpoint} -> Endpoint found but validation error')
        else:
            print(f'🔄 {endpoint} -> Status: {response.status_code}')
    except Exception as e:
        print(f'❌ {endpoint} -> Error: {str(e)}')

print()
print('=== Simple Test Complete ===')
print()
print('📝 Next Steps:')
print('   1. If endpoints show "needs auth", they are registered correctly')
print('   2. Login via browser to get session cookies for full test')
print('   3. Or test directly in frontend template')