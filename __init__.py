from flask import Flask
from .extensions import db, migrate, login_manager, mail, cache, socketio
from .config import Config
from .blueprints.web import dashboard_bp, storm_detail_bp, archive_bp, account_bp, admin_bp
from .blueprints.api import auth_bp, storms_bp
from .middleware import setup_security_headers
from .logging_config import setup_logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Setup logging
    setup_logging(app)
    
    # Setup security headers
    setup_security_headers(app)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    cache.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Configure login manager
    login_manager.login_view = 'account.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Register user loader
    @login_manager.user_loader
    def load_user(user_id):
        from .models.user import User
        return User.query.get(int(user_id))
    
    # Register web blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(storm_detail_bp)
    app.register_blueprint(archive_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)
    
    # Register API blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(storms_bp)
    app.register_blueprint(archive_bp)
    
    # Simple health check
    @app.route("/health")
    def health():
        return {"status": "ok"}
    
    return app
