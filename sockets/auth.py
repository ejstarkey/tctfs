"""
WebSocket authentication.
"""
import logging
from flask import request
from flask_login import current_user

logger = logging.getLogger(__name__)


def setup_socket_auth(socketio):
    """
    Setup WebSocket authentication handlers.
    
    Args:
        socketio: Flask-SocketIO instance
    """
    
    @socketio.on_error(namespace='/ws/live')
    def error_handler(e):
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error: {e}")
    
    @socketio.on_error_default
    def default_error_handler(e):
        """Handle default errors."""
        logger.error(f"WebSocket error (default): {e}")


def check_socket_auth():
    """
    Check if WebSocket connection is authenticated.
    
    Returns:
        True if authenticated, False otherwise
    """
    return current_user.is_authenticated if current_user else False
