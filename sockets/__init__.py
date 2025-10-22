"""
Sockets package - WebSocket handlers for real-time updates.
"""
from .live import register_live_events, emit_advisory_update, emit_forecast_update, emit_zone_update
from .auth import setup_socket_auth, check_socket_auth

__all__ = [
    'register_live_events',
    'emit_advisory_update',
    'emit_forecast_update',
    'emit_zone_update',
    'setup_socket_auth',
    'check_socket_auth',
]


def init_socketio(socketio):
    """
    Initialize all socket handlers.
    
    Args:
        socketio: Flask-SocketIO instance
    """
    register_live_events(socketio)
    setup_socket_auth(socketio)
