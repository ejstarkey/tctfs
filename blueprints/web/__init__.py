"""
Web blueprints - Server-rendered pages.
"""
from .dashboard import bp as dashboard_bp
from .storm_detail import bp as storm_detail_bp
from .archive import bp as archive_bp
from .account import bp as account_bp
from .admin import bp as admin_bp

__all__ = [
    'dashboard_bp',
    'storm_detail_bp',
    'archive_bp',
    'account_bp',
    'admin_bp',
]
