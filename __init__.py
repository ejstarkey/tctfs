from flask import Flask
from .extensions import db, migrate, login_manager, mail, cache, socketio
from .config import Config
from .blueprints.web import web_bp
from .blueprints.api import api_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    cache.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # Register blueprints
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # Simple health check
    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app

