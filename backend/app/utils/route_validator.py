"""
Route Conflict Detection System
Prevents duplicate routes and function name conflicts
Full-Stack Engineering Team - Production Safety
"""

from fastapi import FastAPI, APIRouter
from collections import defaultdict
import inspect
import logging

logger = logging.getLogger(__name__)


class RouteConflictError(Exception):
    """Raised when route conflicts are detected"""
    pass


class RouteValidator:
    """
    Production-grade route conflict detection
    Prevents silent function overwriting and route conflicts
    """
    
    def __init__(self):
        self.route_registry = defaultdict(list)
        self.function_registry = {}
        self.conflicts = []
    
    def validate_router(self, router: APIRouter, router_name: str = "") -> list:
        """
        Validate a FastAPI router for conflicts
        Returns list of conflicts found
        """
        conflicts = []
        route_patterns = {}
        function_names = {}
        
        for route in router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                # Check for route pattern conflicts
                pattern = route.path
                methods = tuple(sorted(route.methods)) if route.methods else ('GET',)
                route_key = (pattern, methods)
                
                if route_key in route_patterns:
                    conflicts.append({
                        'type': 'ROUTE_CONFLICT',
                        'severity': 'CRITICAL',
                        'pattern': pattern,
                        'methods': methods,
                        'router': router_name,
                        'message': f'Duplicate route: {methods} {pattern}'
                    })
                else:
                    route_patterns[route_key] = route
                
                # Check for function name conflicts
                if hasattr(route, 'endpoint') and route.endpoint:
                    func_name = route.endpoint.__name__ if hasattr(route.endpoint, '__name__') else 'unknown'
                    
                    if func_name in function_names:
                        conflicts.append({
                            'type': 'FUNCTION_CONFLICT',
                            'severity': 'CRITICAL', 
                            'function_name': func_name,
                            'pattern': pattern,
                            'router': router_name,
                            'message': f'Duplicate function name: {func_name} for route {pattern}',
                            'existing_route': function_names[func_name]
                        })
                    else:
                        function_names[func_name] = {
                            'pattern': pattern,
                            'methods': methods,
                            'router': router_name
                        }
        
        return conflicts
    
    def validate_app(self, app: FastAPI) -> dict:
        """
        Validate entire FastAPI app for conflicts
        Returns comprehensive conflict report
        """
        all_conflicts = []
        global_routes = {}
        global_functions = {}
        
        # Check main app routes
        app_conflicts = self.validate_router(app.router, "main_app")
        all_conflicts.extend(app_conflicts)
        
        # Check included routers
        for route in app.router.routes:
            if hasattr(route, 'app') and hasattr(route.app, 'routes'):
                # This is an included router
                router_prefix = getattr(route, 'path', '') or getattr(route, 'prefix', '')
                router_conflicts = self.validate_router(route.app, f"router_{router_prefix}")
                all_conflicts.extend(router_conflicts)
        
        # Generate report
        report = {
            'total_conflicts': len(all_conflicts),
            'critical_conflicts': len([c for c in all_conflicts if c.get('severity') == 'CRITICAL']),
            'conflicts': all_conflicts,
            'is_production_safe': len(all_conflicts) == 0,
            'recommendations': []
        }
        
        if all_conflicts:
            report['recommendations'].extend([
                'Fix all route and function conflicts before deployment',
                'Implement automated route testing in CI/CD',
                'Use unique function names across all routers',
                'Consider using FastAPI dependency injection for shared logic'
            ])
        
        return report
    
    def check_backend_routes(self) -> dict:
        """
        Check the current backend for route conflicts
        Production safety validation
        """
        try:
            from app.main import app
            return self.validate_app(app)
        except Exception as e:
            return {
                'total_conflicts': -1,
                'error': str(e),
                'is_production_safe': False,
                'message': 'Failed to load app for validation'
            }


def validate_production_safety() -> bool:
    """
    Quick production safety check
    Returns True if safe for deployment
    """
    validator = RouteValidator()
    report = validator.check_backend_routes()
    
    if report.get('total_conflicts', 0) > 0:
        logger.error(f"PRODUCTION SAFETY VIOLATION: {report['total_conflicts']} route conflicts detected")
        for conflict in report.get('conflicts', []):
            logger.error(f"  - {conflict['type']}: {conflict['message']}")
        return False
    
    logger.info("PRODUCTION SAFETY: All route validations passed")
    return True


def generate_route_report() -> str:
    """
    Generate detailed route report for engineering team
    """
    validator = RouteValidator()
    report = validator.check_backend_routes()
    
    output = ["=" * 60]
    output.append("ROUTE CONFLICT VALIDATION REPORT")
    output.append("=" * 60)
    
    if report.get('error'):
        output.append(f"ERROR: {report['error']}")
        return "\n".join(output)
    
    output.append(f"Total Conflicts Found: {report['total_conflicts']}")
    output.append(f"Critical Conflicts: {report['critical_conflicts']}")
    output.append(f"Production Safe: {report['is_production_safe']}")
    output.append("")
    
    if report['conflicts']:
        output.append("CONFLICTS DETECTED:")
        output.append("-" * 40)
        for i, conflict in enumerate(report['conflicts'], 1):
            output.append(f"{i}. {conflict['type']}: {conflict['message']}")
            if 'existing_route' in conflict:
                output.append(f"   Existing: {conflict['existing_route']}")
            output.append("")
    else:
        output.append("✓ No conflicts detected - System is production ready")
    
    if report.get('recommendations'):
        output.append("RECOMMENDATIONS:")
        output.append("-" * 40)
        for i, rec in enumerate(report['recommendations'], 1):
            output.append(f"{i}. {rec}")
    
    output.append("=" * 60)
    return "\n".join(output)


if __name__ == "__main__":
    # Run validation when executed directly
    print(generate_route_report())
    
    # Exit with error code if conflicts found
    validator = RouteValidator()
    report = validator.check_backend_routes()
    if report.get('total_conflicts', 0) > 0:
        exit(1)
    else:
        print("\nAll validations passed - System ready for deployment")
        exit(0)