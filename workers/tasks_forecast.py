"""
Forecast Tasks - Fetch A-Decks and compute AP1-AP30 mean forecast.
THIS IS THE ONLY FORECAST SHOWN TO USERS.
"""
import logging
from datetime import datetime
from .queue import celery
from ..extensions import db
from ..models import Storm, ForecastPoint
from ..services.forecast.adeck_fetch import get_adeck_fetch_service
from ..services.forecast.adeck_parse import get_adeck_parse_service
from ..services.forecast.ap_mean import get_ap_mean_service

logger = logging.getLogger(__name__)


@celery.task(name='tctfs_app.workers.tasks_forecast.update_storm_forecast_task')
def update_storm_forecast_task(storm_id):
    """
    Update AP-mean forecast for a specific storm.
    
    Args:
        storm_id: Database ID of storm
    """
    logger.info(f"Updating forecast for storm {storm_id}")
    
    try:
        storm = Storm.query.get(storm_id)
        if not storm:
            logger.error(f"Storm {storm_id} not found")
            return {'status': 'error', 'error': 'Storm not found'}
        
        # Extract storm number from storm_id (e.g., "28W" -> 28)
        storm_num = int(''.join(filter(str.isdigit, storm.storm_id)))
        current_year = datetime.utcnow().year
        
        # Fetch A-Deck file
        fetch_service = get_adeck_fetch_service()
        adeck_result = fetch_service.fetch_adeck(
            basin=storm.basin,
            storm_num=storm_num,
            year=current_year
        )
        
        if not adeck_result:
            logger.info(f"No A-Deck data available for {storm.storm_id}")
            return {'status': 'no_data'}
        
        # Parse A-Deck file
        parse_service = get_adeck_parse_service()
        all_forecasts = parse_service.parse_file(adeck_result['content'])
        
        # Filter to AP01-AP30 members only
        ap_forecasts = parse_service.filter_ap_members(all_forecasts, ap_range=(1, 30))
        
        if not ap_forecasts:
            logger.warning(f"No AP members found in A-Deck for {storm.storm_id}")
            return {'status': 'no_ap_members'}
        
        logger.info(f"Found {len(ap_forecasts)} AP member forecasts for {storm.storm_id}")
        
        # Compute AP1-AP30 mean
        ap_mean_service = get_ap_mean_service()
        mean_forecast = ap_mean_service.compute_mean_forecast(ap_forecasts)
        
        if not mean_forecast:
            logger.error(f"Failed to compute mean forecast for {storm.storm_id}")
            return {'status': 'error', 'error': 'Mean computation failed'}
        
        logger.info(f"Computed {len(mean_forecast)} mean forecast points for {storm.storm_id}")
        
        # Delete old forecast points for this storm
        ForecastPoint.query.filter_by(storm_id=storm_id, is_final=True).delete()
        
        # Insert new forecast points
        for fp_data in mean_forecast:
            forecast_point = ForecastPoint(
                storm_id=storm_id,
                issuance_time_utc=fp_data['issuance_time'],
                valid_at_utc=fp_data['valid_at'],
                lead_time_hours=fp_data['lead_time_hours'],
                center_lat=fp_data['latitude'],
                center_lon=fp_data['longitude'],
                vmax_kt=fp_data.get('vmax_kt'),
                mslp_hpa=fp_data.get('mslp_hpa'),
                radii_json=fp_data.get('radii'),
                member_count=fp_data.get('member_count', 0),
                source_tag='adecks_open',
                is_final=True
            )
            db.session.add(forecast_point)
        
        db.session.commit()
        
        logger.info(f"Saved {len(mean_forecast)} forecast points for {storm.storm_id}")
        
        # Trigger zone regeneration with new forecast
        from .tasks_zones import regenerate_storm_zones_task
        regenerate_storm_zones_task.delay(storm_id)
        
        # Send WebSocket notification
        send_forecast_update_notification(storm.storm_id)
        
        return {
            'status': 'success',
            'storm_id': storm.storm_id,
            'forecast_points': len(mean_forecast),
            'issuance_time': mean_forecast[0]['issuance_time'].isoformat() if mean_forecast else None
        }
        
    except Exception as e:
        logger.error(f"Error updating forecast for storm {storm_id}: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }


@celery.task(name='tctfs_app.workers.tasks_forecast.update_all_forecasts_task')
def update_all_forecasts_task():
    """
    Update forecasts for all active storms (scheduled task).
    """
    logger.info("Updating forecasts for all active storms")
    
    try:
        active_storms = Storm.query.filter_by(status='active').all()
        
        logger.info(f"Found {len(active_storms)} active storms")
        
        results = []
        for storm in active_storms:
            # Trigger individual storm forecast update
            result = update_storm_forecast_task.delay(storm.id)
            results.append({
                'storm_id': storm.storm_id,
                'task_id': result.id
            })
        
        return {
            'status': 'success',
            'storms_updated': len(results),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error updating all forecasts: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }


@celery.task(name='tctfs_app.workers.tasks_forecast.rebuild_forecast_task')
def rebuild_forecast_task(storm_id):
    """
    Rebuild forecast for a storm (admin action).
    Same as update but forces re-fetch.
    
    Args:
        storm_id: Database ID of storm
    """
    logger.info(f"Rebuilding forecast for storm {storm_id}")
    
    # Clear cache for this storm's A-Deck
    storm = Storm.query.get(storm_id)
    if storm:
        fetch_service = get_adeck_fetch_service()
        # Clear cache entry if exists
        storm_num = int(''.join(filter(str.isdigit, storm.storm_id)))
        current_year = datetime.utcnow().year
        basin_map = {'WP': 'w', 'EP': 'e', 'AL': 'l', 'CP': 'c', 'SH': 's', 'IO': 'i'}
        basin_code = basin_map.get(storm.basin, storm.basin.lower()[0])
        filename = f"a{basin_code}{storm_num:02d}{current_year}.dat"
        url = f"{fetch_service.base_url}{filename}"
        
        if url in fetch_service.cache:
            del fetch_service.cache[url]
            logger.info(f"Cleared cache for {url}")
    
    # Now update normally
    return update_storm_forecast_task(storm_id)


def send_forecast_update_notification(storm_id):
    """
    Send WebSocket notification about forecast update.
    
    Args:
        storm_id: Storm identifier string
    """
    try:
        from flask_socketio import emit
        from flask import current_app
        
        socketio = current_app.extensions.get('socketio')
        if socketio:
            socketio.emit('forecast_updated', {
                'storm_id': storm_id,
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/ws/live')
            logger.info(f"Sent forecast update notification for {storm_id}")
    except Exception as e:
        logger.warning(f"Failed to send WebSocket notification: {e}")
