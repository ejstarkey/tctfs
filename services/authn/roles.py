"""
Roles Service - Role-based access control helpers.
"""
import logging
from functools import wraps
from flask import abort
from flask_login import current_user

logger = logging.getLogger(__name__)


class RolesService:
    """
    Manage role-based access control and permissions.
    """
    
    # Role hierarchy (higher value = more permissions)
    ROLE_HIERARCHY = {
        'viewer': 1,
        'forecaster': 2,
        'admin': 3,
    }
    
    # Permission mappings
    PERMISSIONS = {
        'view_storms': ['viewer', 'forecaster', 'admin'],
        'view_forecasts': ['viewer', 'forecaster', 'admin'],
        'subscribe_alerts': ['viewer', 'forecaster', 'admin'],
        
        'reingest_storm': ['forecaster', 'admin'],
        'rebuild_forecast': ['forecaster', 'admin'],
        'regenerate_zones': ['forecaster', 'admin'],
        
        'manage_users': ['admin'],
        'view_audit_logs': ['admin'],
        'modify_system_settings': ['admin'],
    }
    
    def has_role(self, user, *roles) -> bool:
        """
        Check if user has any of the specified roles.
        
        Args:
            user: User object
            roles: Role names to check
        
        Returns:
            True if user has any of the roles
        """
        if not user or not user.is_authenticated:
            return False
        
        return user.role in roles
    
    def has_permission(self, user, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user: User object
            permission: Permission name
        
        Returns:
            True if user has permission
        """
        if not user or not user.is_authenticated:
            return False
        
        allowed_roles = self.PERMISSIONS.get(permission, [])
        return user.role in allowed_roles
    
    def require_role(self, *roles):
        """
        Decorator to require specific role(s) for a route.
        
        Usage:
            @app.route('/admin')
            @require_role('admin')
            def admin_page():
                return "Admin only"
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated:
                    abort(401, description="Authentication required")
                
                if not self.has_role(current_user, *roles):
                    abort(403, description=f"Required role: {', '.join(roles)}")
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def require_permission(self, permission: str):
        """
        Decorator to require specific permission for a route.
        
        Usage:
            @app.route('/storms/reingest')
            @require_permission('reingest_storm')
            def reingest():
                return "OK"
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated:
                    abort(401, description="Authentication required")
                
                if not self.has_permission(current_user, permission):
                    abort(403, description=f"Permission required: {permission}")
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def get_role_level(self, role: str) -> int:
        """
        Get numeric level for a role (for comparison).
        
        Args:
            role: Role name
        
        Returns:
            Numeric level (higher = more permissions)
        """
        return self.ROLE_HIERARCHY.get(role, 0)
    
    def is_role_higher(self, role1: str, role2: str) -> bool:
        """
        Check if role1 has higher permissions than role2.
        
        Args:
            role1: First role
            role2: Second role
        
        Returns:
            True if role1 > role2
        """
        return self.get_role_level(role1) > self.get_role_level(role2)


# Singleton instance
_roles_service = None

def get_roles_service() -> RolesService:
    """Get or create the singleton roles service."""
    global _roles_service
    if _roles_service is None:
        _roles_service = RolesService()
    return _roles_service


# Convenience decorators
def require_role(*roles):
    """Convenience wrapper for role requirement decorator."""
    return get_roles_service().require_role(*roles)


def require_permission(permission: str):
    """Convenience wrapper for permission requirement decorator."""
    return get_roles_service().require_permission(permission)
