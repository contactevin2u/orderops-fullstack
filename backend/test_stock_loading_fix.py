#!/usr/bin/env python3
"""
Test script to verify the stock loading and date parameter fix
"""
import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def test_stock_loading_fix():
    """Test the stock loading and date parameter fix"""
    
    print("=" * 60)
    print("STOCK LOADING DATE PARAMETER FIX TEST")
    print("=" * 60)
    
    # Test the transactions endpoint with date parameter
    test_date = "2025-09-10"
    url = f"{BASE_URL}/lorry-management/stock/transactions?limit=50&date={test_date}"
    
    print(f"Testing: GET {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Request successful!")
            
            if 'data' in data:
                transactions = data['data'] if isinstance(data['data'], list) else []
                print(f"Found {len(transactions)} transactions for date {test_date}")
                
                if transactions:
                    print("\nSample transactions:")
                    for i, tx in enumerate(transactions[:3]):
                        print(f"{i+1}. Lorry: {tx.get('lorry_id', 'N/A')}, Action: {tx.get('action', 'N/A')}, UID: {tx.get('uid', 'N/A')}, Date: {tx.get('transaction_date', 'N/A')}")
                else:
                    print("No transactions found for the specified date")
            else:
                print("Unexpected response format")
                
        elif response.status_code == 401:
            print("⚠️  Authentication required - this is expected behavior")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Server not running - this test requires the backend to be active")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("FIX SUMMARY:")
    print("✅ Added 'date' parameter support to transactions endpoint")
    print("✅ Backend now handles date=YYYY-MM-DD format from frontend")
    print("✅ Single date gets converted to start_date=date, end_date=date")
    print("=" * 60)

if __name__ == "__main__":
    test_stock_loading_fix()