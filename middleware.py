"""
Security middleware for TCTFS.
Implements CSP, HSTS, secure headers, and correlation ID tracking.
"""
import uuid
from flask import g, request
from functools import wraps


def setup_security_headers(app):
    """
    Configure security headers for all responses.
    
    Args:
        app: Flask application instance
    """
    
    @app.after_request
    def add_security_headers(response):
        """Add security headers to every response."""
        
        # Content Security Policy - ALLOW MAPLIBRE AND EXTERNAL RESOURCES
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net https://cdn.socket.io blob:; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' wss: ws: https: http:; "
            "worker-src 'self' blob:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # HSTS - Force HTTPS (31536000 = 1 year)
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Prevent MIME sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # XSS Protection (legacy but harmless)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (formerly Feature-Policy)
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=()'
        )
        
        return response
    
    @app.before_request
    def add_correlation_id():
        """Add correlation ID to request context for tracing."""
        g.correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        g.request_start_time = uuid.uuid1().time


def require_https(f):
    """
    Decorator to enforce HTTPS on specific routes.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, abort, current_app
        
        if not current_app.debug and not request.is_secure:
            abort(403, description="HTTPS required")
        
        return f(*args, **kwargs)
    
    return decorated_function


def setup_rate_limiting(app):
    """
    Configure rate limiting for the application.
    """
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://'),
            strategy="fixed-window"
        )
        
        return limiter
    except ImportError:
        app.logger.warning("Flask-Limiter not installed, rate limiting disabled")
        return None
