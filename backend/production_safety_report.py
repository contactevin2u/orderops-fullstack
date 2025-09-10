#!/usr/bin/env python3
"""
OrderOps Production Safety Report Generator
Full-Stack Engineering Team - Deployment Readiness Assessment
"""
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

def generate_production_safety_report() -> Dict[str, Any]:
    """Generate comprehensive production safety report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "system_name": "OrderOps Unified Inventory System",
        "version": "1.0.0",
        "assessment_summary": {},
        "critical_checks": [],
        "warnings": [],
        "passed_checks": [],
        "recommendations": [],
        "deployment_ready": False
    }
    
    # 1. Route Conflict Analysis
    try:
        from app.utils.route_validator import RouteValidator
        validator = RouteValidator()
        route_report = validator.check_backend_routes()
        
        if route_report.get('total_conflicts', 0) == 0:
            report["passed_checks"].append({
                "check": "Route Conflict Detection",
                "status": "PASSED",
                "message": "No route conflicts detected - all API endpoints unique"
            })
        else:
            report["critical_checks"].append({
                "check": "Route Conflict Detection", 
                "status": "FAILED",
                "message": f"{route_report['total_conflicts']} route conflicts detected",
                "details": route_report.get('conflicts', [])
            })
    except Exception as e:
        report["critical_checks"].append({
            "check": "Route Conflict Detection",
            "status": "ERROR", 
            "message": f"Failed to run route validation: {str(e)}"
        })
    
    # 2. Database Migration Status
    try:
        import os
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        alembic_dir = os.path.join(backend_dir, "alembic", "versions")
        
        if os.path.exists(alembic_dir):
            migration_files = [f for f in os.listdir(alembic_dir) if f.endswith('.py') and not f.startswith('__')]
            if migration_files:
                report["passed_checks"].append({
                    "check": "Database Migrations",
                    "status": "PASSED", 
                    "message": f"Found {len(migration_files)} migration files"
                })
            else:
                report["warnings"].append({
                    "check": "Database Migrations",
                    "status": "WARNING",
                    "message": "No migration files found - ensure database is properly initialized"
                })
        else:
            report["warnings"].append({
                "check": "Database Migrations",
                "status": "WARNING", 
                "message": "Alembic migrations directory not found"
            })
    except Exception as e:
        report["warnings"].append({
            "check": "Database Migrations",
            "status": "ERROR",
            "message": f"Failed to check migrations: {str(e)}"
        })
    
    # 3. Environment Configuration
    try:
        import os
        required_env_vars = ['DATABASE_URL', 'JWT_SECRET']
        missing_env_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_env_vars:
            report["critical_checks"].append({
                "check": "Environment Configuration",
                "status": "FAILED",
                "message": f"Missing required environment variables: {', '.join(missing_env_vars)}"
            })
        else:
            report["passed_checks"].append({
                "check": "Environment Configuration", 
                "status": "PASSED",
                "message": "All required environment variables present"
            })
    except Exception as e:
        report["critical_checks"].append({
            "check": "Environment Configuration",
            "status": "ERROR",
            "message": f"Failed to check environment: {str(e)}"
        })
    
    # 4. Critical API Endpoints Health
    critical_endpoints = [
        "/healthz",
        "/auth/login", 
        "/lorry-management/clock-in-with-stock",
        "/inventory/config",
        "/driver/me"
    ]
    
    try:
        from app.main import app
        
        # Check that critical endpoints are registered
        all_routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                all_routes.append(route.path)
            elif hasattr(route, 'routes'):  # Sub-routers
                for subroute in route.routes:
                    if hasattr(subroute, 'path'):
                        all_routes.append(subroute.path)
        
        missing_endpoints = [ep for ep in critical_endpoints if ep not in all_routes]
        
        if missing_endpoints:
            report["critical_checks"].append({
                "check": "Critical API Endpoints",
                "status": "FAILED", 
                "message": f"Missing critical endpoints: {', '.join(missing_endpoints)}"
            })
        else:
            report["passed_checks"].append({
                "check": "Critical API Endpoints",
                "status": "PASSED",
                "message": "All critical endpoints are registered"
            })
    except Exception as e:
        report["critical_checks"].append({
            "check": "Critical API Endpoints", 
            "status": "ERROR",
            "message": f"Failed to check endpoints: {str(e)}"
        })
    
    # 5. Security Configuration
    auth_warning = {
        "check": "Authentication Security",
        "status": "WARNING",
        "message": "Authentication has been removed - ensure this is intentional for development only",
        "recommendation": "Re-enable authentication for production deployment"
    }
    report["warnings"].append(auth_warning)
    
    # 6. Generate Assessment Summary
    total_checks = len(report["passed_checks"]) + len(report["critical_checks"]) + len(report["warnings"])
    passed_count = len(report["passed_checks"])
    failed_count = len(report["critical_checks"])
    warning_count = len(report["warnings"])
    
    report["assessment_summary"] = {
        "total_checks": total_checks,
        "passed": passed_count,
        "failed": failed_count, 
        "warnings": warning_count,
        "success_rate": f"{(passed_count/total_checks)*100:.1f}%" if total_checks > 0 else "0%"
    }
    
    # 7. Deployment Readiness
    report["deployment_ready"] = (failed_count == 0)
    
    # 8. Recommendations
    if failed_count > 0:
        report["recommendations"].extend([
            "Fix all FAILED checks before deployment",
            "Run comprehensive integration tests",
            "Perform security audit before production"
        ])
    
    if warning_count > 0:
        report["recommendations"].append("Review and address all WARNING items")
    
    if report["deployment_ready"]:
        report["recommendations"].extend([
            "System passed all critical checks",
            "Ready for staging environment deployment",
            "Monitor system performance after deployment"
        ])
    else:
        report["recommendations"].append("CRITICAL: Do not deploy to production until all failures are resolved")
    
    return report

def print_report(report: Dict[str, Any]) -> None:
    """Print formatted production safety report"""
    print("=" * 80)
    print("ORDEROPS PRODUCTION SAFETY ASSESSMENT REPORT")
    print("=" * 80)
    print(f"Generated: {report['timestamp']}")
    print(f"System: {report['system_name']} v{report['version']}")
    print()
    
    # Summary
    summary = report["assessment_summary"]
    print("ASSESSMENT SUMMARY:")
    print("-" * 40)
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Success Rate: {summary['success_rate']}")
    print()
    
    # Deployment Status
    status = "✅ DEPLOYMENT READY" if report["deployment_ready"] else "❌ NOT DEPLOYMENT READY"
    print(f"DEPLOYMENT STATUS: {status}")
    print()
    
    # Failed Checks
    if report["critical_checks"]:
        print("🚨 CRITICAL ISSUES (MUST FIX):")
        print("-" * 40)
        for i, check in enumerate(report["critical_checks"], 1):
            print(f"{i}. {check['check']}: {check['status']}")
            print(f"   {check['message']}")
            if 'details' in check:
                print(f"   Details: {len(check['details'])} items")
            print()
    
    # Warnings
    if report["warnings"]:
        print("⚠️  WARNINGS (REVIEW RECOMMENDED):")
        print("-" * 40)
        for i, check in enumerate(report["warnings"], 1):
            print(f"{i}. {check['check']}: {check['status']}")
            print(f"   {check['message']}")
            print()
    
    # Passed Checks
    if report["passed_checks"]:
        print("✅ PASSED CHECKS:")
        print("-" * 40)
        for i, check in enumerate(report["passed_checks"], 1):
            print(f"{i}. {check['check']}: {check['message']}")
        print()
    
    # Recommendations
    if report["recommendations"]:
        print("📋 RECOMMENDATIONS:")
        print("-" * 40)
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"{i}. {rec}")
        print()
    
    print("=" * 80)

if __name__ == "__main__":
    report = generate_production_safety_report()
    
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    
    # Exit with appropriate code
    sys.exit(0 if report["deployment_ready"] else 1)