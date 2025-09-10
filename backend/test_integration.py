#!/usr/bin/env python3
"""
Integration Test Suite for OrderOps Unified Inventory System
Full-Stack Engineering Team - Production Safety Validation
"""
import pytest
import requests
import json
from datetime import datetime, date
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8000"

class TestInventoryIntegration:
    """Test the integrated inventory system end-to-end"""
    
    def test_server_health(self):
        """Verify server is running"""
        response = requests.get(f"{BASE_URL}/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
    
    def test_authentication_enforcement(self):
        """Verify key protected endpoints require authentication"""
        protected_endpoints = [
            ("GET", "/lorry-management/driver-status"),
            ("GET", "/driver/me"),
            ("GET", "/lorry-management/my-assignment"),
        ]
        
        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            elif method == "POST":
                response = requests.post(f"{BASE_URL}{endpoint}", json={})
            
            # 401 (unauthorized) or 403 (forbidden) both indicate auth protection
            assert response.status_code in [401, 403], f"Endpoint {endpoint} not properly protected"
    
    def test_route_conflicts_resolved(self):
        """Verify no route conflicts exist in the system"""
        from app.utils.route_validator import RouteValidator
        
        validator = RouteValidator()
        report = validator.check_backend_routes()
        
        assert report.get('total_conflicts', 0) == 0, f"Route conflicts detected: {report}"
        assert report.get('is_production_safe', False) == True, "System not production safe"
    
    def test_inventory_endpoints_structure(self):
        """Test that inventory endpoints have proper structure"""
        # Test core inventory endpoints that exist
        endpoints_to_test = [
            ("POST", "/inventory/sku/resolve"), 
            ("POST", "/inventory/sku/alias"),
            ("GET", "/inventory/skus"),
        ]
        
        for method, endpoint in endpoints_to_test:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", json={})
            # Should work (200) or be protected/have validation errors
            assert response.status_code in [200, 401, 403, 422], f"Endpoint {method} {endpoint} may not exist (got {response.status_code})"
    
    def test_driver_endpoints_structure(self):
        """Test that driver endpoints have proper structure"""
        endpoints_to_test = [
            "/driver/me",
            "/drivers/orders",
        ]
        
        for endpoint in endpoints_to_test:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code in [401, 403, 422], f"Endpoint {endpoint} may not exist (got {response.status_code})"
    
    def test_lorry_management_endpoints_structure(self):
        """Test that lorry management endpoints have proper structure"""
        endpoints_to_test = [
            ("POST", "/lorry-management/clock-in-with-stock"),
            ("GET", "/lorry-management/lorries"),
        ]
        
        for method, endpoint in endpoints_to_test:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", json={})
            assert response.status_code in [200, 401, 403, 422], f"Endpoint {method} {endpoint} may not exist (got {response.status_code})"

def run_integration_tests():
    """Run integration tests and return results"""
    import subprocess
    import sys
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "test_integration.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True, cwd=".")
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
            "return_code": result.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "errors": str(e),
            "return_code": -1
        }

if __name__ == "__main__":
    print("=" * 60)
    print("ORDEROPS UNIFIED INVENTORY INTEGRATION TESTS")
    print("=" * 60)
    
    # Run route validation first
    from app.utils.route_validator import generate_route_report
    print(generate_route_report())
    
    # Run integration tests
    print("\n" + "=" * 60)
    print("RUNNING INTEGRATION TEST SUITE")
    print("=" * 60)
    
    results = run_integration_tests()
    
    if results["success"]:
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("System is production-ready")
    else:
        print("❌ INTEGRATION TESTS FAILED")
        print(f"Output: {results['output']}")
        print(f"Errors: {results['errors']}")
        
    exit(0 if results["success"] else 1)