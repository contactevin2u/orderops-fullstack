"""
Quick test script to verify the inventory endpoint fix
"""
import requests
import json
from datetime import date

# Test configuration
BASE_URL = "http://localhost:8000"  # Adjust if needed
DRIVER_ID = 2
TEST_DATE = "2025-09-12"

def test_endpoints():
    print(f"Testing inventory endpoints for driver {DRIVER_ID} on {TEST_DATE}")
    print("=" * 60)
    
    # Test 1: Lorry stock endpoint (should work)
    print("\n1. Testing GET /inventory/lorry/{driver_id}/stock")
    lorry_url = f"{BASE_URL}/inventory/lorry/{DRIVER_ID}/stock?date={TEST_DATE}"
    print(f"   URL: {lorry_url}")
    
    try:
        # Note: This will require authentication in real deployment
        response = requests.get(lorry_url)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                items_count = len(data['data'].get('items', []))
                total_expected = data['data'].get('total_expected', 0)
                print(f"   Items: {items_count}, Total Expected: {total_expected}")
            else:
                print(f"   Response: {data}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Connection error: {e}")
    
    # Test 2: Stock status endpoint (should now match)
    print("\n2. Testing GET /inventory/drivers/{driver_id}/stock-status")
    status_url = f"{BASE_URL}/inventory/drivers/{DRIVER_ID}/stock-status?date={TEST_DATE}"
    print(f"   URL: {status_url}")
    
    try:
        # Note: This will require authentication in real deployment
        response = requests.get(status_url)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                items_count = len(data['data'].get('items', []))
                total_expected = data['data'].get('total_expected', 0)
                print(f"   Items: {items_count}, Total Expected: {total_expected}")
                print(f"   Message: {data['data'].get('message', 'No message')}")
            else:
                print(f"   Response: {data}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Connection error: {e}")
    
    print("\n" + "=" * 60)
    print("Both endpoints should now return the same total_expected value")
    print("and use the same event-sourced data from lorry transactions.")

if __name__ == "__main__":
    test_endpoints()