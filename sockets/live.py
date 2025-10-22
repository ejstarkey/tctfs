"""
Live WebSocket events - Push real-time updates to clients.
"""
import logging
from flask import request
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user

logger = logging.getLogger(__name__)


def register_live_events(socketio):
    """
    Register WebSocket event handlers.
    
    Args:
        socketio: Flask-SocketIO instance
    """
    
    @socketio.on('connect', namespace='/ws/live')
    def handle_connect():
        """Handle client connection."""
        logger.info(f"Client connected: {request.sid}")
        emit('connected', {'message': 'Connected to TCTFS live updates'})
    
    @socketio.on('disconnect', namespace='/ws/live')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info(f"Client disconnected: {request.sid}")
    
    @socketio.on('subscribe_storm', namespace='/ws/live')
    def handle_subscribe_storm(data):
        """
        Subscribe to updates for a specific storm.
        
        Args:
            data: Dict with 'storm_id' key
        """
        storm_id = data.get('storm_id')
        if storm_id:
            room = f"storm_{storm_id}"
            join_room(room)
            logger.info(f"Client {request.sid} subscribed to {storm_id}")
            emit('subscribed', {'storm_id': storm_id})
    
    @socketio.on('unsubscribe_storm', namespace='/ws/live')
    def handle_unsubscribe_storm(data):
        """
        Unsubscribe from storm updates.
        
        Args:
            data: Dict with 'storm_id' key
        """
        storm_id = data.get('storm_id')
        if storm_id:
            room = f"storm_{storm_id}"
            leave_room(room)
            logger.info(f"Client {request.sid} unsubscribed from {storm_id}")
            emit('unsubscribed', {'storm_id': storm_id})
    
    @socketio.on('ping', namespace='/ws/live')
    def handle_ping():
        """Handle ping from client."""
        emit('pong')


def emit_advisory_update(socketio, storm_id, advisory_data):
    """
    Emit advisory update to subscribed clients.
    
    Args:
        socketio: Flask-SocketIO instance
        storm_id: Storm identifier
        advisory_data: Advisory data dict
    """
    room = f"storm_{storm_id}"
    socketio.emit('advisory_updated', {
        'storm_id': storm_id,
        'advisory': advisory_data
    }, room=room, namespace='/ws/live')
    
    logger.info(f"Emitted advisory update for {storm_id}")


def emit_forecast_update(socketio, storm_id, forecast_data):
    """
    Emit forecast update to subscribed clients.
    
    Args:
        socketio: Flask-SocketIO instance
        storm_id: Storm identifier
        forecast_data: Forecast data dict
    """
    room = f"storm_{storm_id}"
    socketio.emit('forecast_updated', {
        'storm_id': storm_id,
        'forecast': forecast_data
    }, room=room, namespace='/ws/live')
    
    logger.info(f"Emitted forecast update for {storm_id}")


def emit_zone_update(socketio, storm_id, zones_data):
    """
    Emit zone update to subscribed clients.
    
    Args:
        socketio: Flask-SocketIO instance
        storm_id: Storm identifier
        zones_data: Zones data dict
    """
    room = f"storm_{storm_id}"
    socketio.emit('zones_updated', {
        'storm_id': storm_id,
        'zones': zones_data
    }, room=room, namespace='/ws/live')
    
    logger.info(f"Emitted zone update for {storm_id}")
