"""
Zone Tasks - Generate watch/warning zones based on AP-mean forecast.
"""
import logging
from datetime import datetime, timedelta
from .queue import celery
from ..extensions import db
from ..models import Storm, ForecastPoint, Zone
from ..services.zones.gale_arrival import compute_tofi
from ..services.zones.polygon_builder import build_zone_polygons

logger = logging.getLogger(__name__)


@celery.task(name='tctfs_app.workers.tasks_zones.regenerate_storm_zones_task')
def regenerate_storm_zones_task(storm_id):
    """
    Regenerate watch/warning zones for a specific storm.
    
    Args:
        storm_id: Database ID of storm
    """
    logger.info(f"Regenerating zones for storm {storm_id}")
    
    try:
        storm = Storm.query.get(storm_id)
        if not storm:
            logger.error(f"Storm {storm_id} not found")
            return {'status': 'error', 'error': 'Storm not found'}
        
        # Get latest AP-mean forecast
        forecast_points = ForecastPoint.get_latest_forecast(storm_id)
        
        if not forecast_points:
            logger.info(f"No forecast available for {storm.storm_id}, skipping zone generation")
            return {'status': 'no_forecast'}
        
        logger.info(f"Using {len(forecast_points)} forecast points for {storm.storm_id}")
        
        # Delete old zones for this storm
        Zone.query.filter_by(storm_id=storm_id).delete()
        
        # Generate watch and warning zones
        watch_zones = generate_watch_zones(storm, forecast_points)
        warning_zones = generate_warning_zones(storm, forecast_points)
        
        # Save zones
        generated_at = datetime.utcnow()
        zones_created = 0
        
        for zone_data in watch_zones + warning_zones:
            zone = Zone(
                storm_id=storm_id,
                generated_at_utc=generated_at,
                zone_type=zone_data['type'],
                valid_from_utc=zone_data['valid_from'],
                valid_to_utc=zone_data['valid_to'],
                geom=zone_data['geometry'],
                method_version='v1.0',
                metadata_json=zone_data.get('metadata')
            )
            db.session.add(zone)
            zones_created += 1
        
        db.session.commit()
        
        logger.info(f"Generated {zones_created} zones for {storm.storm_id}")
        
        # Send WebSocket notification
        send_zone_update_notification(storm.storm_id)
        
        # Trigger alerts for zone changes
        from .tasks_alerts import send_zone_change_alerts_task
        send_zone_change_alerts_task.delay(storm_id)
        
        return {
            'status': 'success',
            'storm_id': storm.storm_id,
            'zones_created': zones_created,
            'watch_zones': len(watch_zones),
            'warning_zones': len(warning_zones)
        }
        
    except Exception as e:
        logger.error(f"Error regenerating zones for storm {storm_id}: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }


@celery.task(name='tctfs_app.workers.tasks_zones.regenerate_all_zones_task')
def regenerate_all_zones_task():
    """
    Regenerate zones for all active storms (scheduled task).
    """
    logger.info("Regenerating zones for all active storms")
    
    try:
        active_storms = Storm.query.filter_by(status='active').all()
        
        logger.info(f"Found {len(active_storms)} active storms")
        
        results = []
        for storm in active_storms:
            result = regenerate_storm_zones_task.delay(storm.id)
            results.append({
                'storm_id': storm.storm_id,
                'task_id': result.id
            })
        
        return {
            'status': 'success',
            'storms_processed': len(results),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error regenerating all zones: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }


def generate_watch_zones(storm, forecast_points):
    """
    Generate Cyclone Watch zones (24-48h gale arrival).
    
    Args:
        storm: Storm model instance
        forecast_points: List of ForecastPoint instances
    
    Returns:
        List of zone dictionaries
    """
    zones = []
    
    try:
        # Compute TOFI (Time of First Intersection) for each coastal segment
        # Watch: 24h < TOFI <= 48h
        watch_threshold_min = 24
        watch_threshold_max = 48
        
        # Get forecast points within watch window
        now = datetime.utcnow()
        watch_points = [
            fp for fp in forecast_points
            if watch_threshold_min <= (fp.valid_at_utc - now).total_seconds() / 3600 <= watch_threshold_max
        ]
        
        if not watch_points:
            return zones
        
        # Build watch polygons
        watch_polygons = build_zone_polygons(
            storm=storm,
            forecast_points=watch_points,
            buffer_km=50,
            zone_type='watch'
        )
        
        for polygon in watch_polygons:
            zones.append({
                'type': 'watch',
                'valid_from': now,
                'valid_to': now + timedelta(hours=48),
                'geometry': polygon,
                'metadata': {
                    'threshold_hours': '24-48',
                    'points_used': len(watch_points)
                }
            })
        
    except Exception as e:
        logger.error(f"Error generating watch zones: {e}", exc_info=True)
    
    return zones


def generate_warning_zones(storm, forecast_points):
    """
    Generate Cyclone Warning zones (≤24h gale arrival).
    
    Args:
        storm: Storm model instance
        forecast_points: List of ForecastPoint instances
    
    Returns:
        List of zone dictionaries
    """
    zones = []
    
    try:
        # Warning: TOFI <= 24h
        warning_threshold = 24
        
        # Get forecast points within warning window
        now = datetime.utcnow()
        warning_points = [
            fp for fp in forecast_points
            if (fp.valid_at_utc - now).total_seconds() / 3600 <= warning_threshold
        ]
        
        if not warning_points:
            return zones
        
        # Build warning polygons
        warning_polygons = build_zone_polygons(
            storm=storm,
            forecast_points=warning_points,
            buffer_km=75,  # Slightly larger buffer for warnings
            zone_type='warning'
        )
        
        for polygon in warning_polygons:
            zones.append({
                'type': 'warning',
                'valid_from': now,
                'valid_to': now + timedelta(hours=24),
                'geometry': polygon,
                'metadata': {
                    'threshold_hours': '≤24',
                    'points_used': len(warning_points)
                }
            })
        
    except Exception as e:
        logger.error(f"Error generating warning zones: {e}", exc_info=True)
    
    return zones


def send_zone_update_notification(storm_id):
    """
    Send WebSocket notification about zone update.
    
    Args:
        storm_id: Storm identifier string
    """
    try:
        from flask_socketio import emit
        from flask import current_app
        
        socketio = current_app.extensions.get('socketio')
        if socketio:
            socketio.emit('zones_updated', {
                'storm_id': storm_id,
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/ws/live')
            logger.info(f"Sent zone update notification for {storm_id}")
    except Exception as e:
        logger.warning(f"Failed to send WebSocket notification: {e}")
