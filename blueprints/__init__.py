"""
Blueprints package - Flask blueprints for web and API routes.
"""
from flask import Flask


def register_blueprints(app: Flask):
    """
    Register all blueprints with the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Import blueprints
    from .web import dashboard_bp, storm_detail_bp, archive_bp, account_bp, admin_bp
    from .api import storms_bp, forecast_bp, zones_bp, subscriptions_bp, auth_bp, health_bp
    
    # Register web blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(storm_detail_bp)
    app.register_blueprint(archive_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)
    
    # Register API blueprints
    app.register_blueprint(storms_bp, url_prefix='/api')
    app.register_blueprint(forecast_bp, url_prefix='/api')
    app.register_blueprint(zones_bp, url_prefix='/api')
    app.register_blueprint(subscriptions_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(health_bp, url_prefix='/api')
