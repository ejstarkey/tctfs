"""
Zones API Blueprint - Watch/Warning zone endpoints.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('api_zones', __name__)


@bp.route('/storms/<storm_id>/zones', methods=['GET'])
@login_required
def get_zones(storm_id):
    """
    Get watch/warning zones for a storm.
    
    Args:
        storm_id: Storm identifier
    
    Query params:
        at: Optional time to get zones valid at (ISO format, default: now)
    """
    from ...models import Storm, Zone
    
    storm = Storm.get_by_storm_id(storm_id)
    if not storm:
        return jsonify({'error': 'Storm not found'}), 404
    
    # Parse time parameter
    at_time_str = request.args.get('at')
    if at_time_str:
        try:
            at_time = datetime.fromisoformat(at_time_str.replace('Z', '+00:00'))
        except:
            return jsonify({'error': 'Invalid time format'}), 400
    else:
        at_time = datetime.utcnow()
    
    # Get zones active at specified time
    zones = Zone.get_active_zones(storm.id, at_time)
    
    if not zones:
        return jsonify({
            'storm_id': storm_id,
            'zones': [],
            'message': 'No zones active at specified time'
        })
    
    # Convert to GeoJSON FeatureCollection
    features = [zone.to_geojson_feature() for zone in zones]
    
    return jsonify({
        'storm_id': storm_id,
        'query_time_utc': at_time.isoformat(),
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'watch_color': '#FEC5BB',  # Pale pink
            'warning_color': '#EF4444',  # Darker pink/red
            'zone_count': len(features)
        }
    })


@bp.route('/storms/<storm_id>/zones/latest', methods=['GET'])
@login_required
def get_latest_zones(storm_id):
    """
    Get most recently generated zones (regardless of validity time).
    """
    from ...models import Storm, Zone
    
    storm = Storm.get_by_storm_id(storm_id)
    if not storm:
        return jsonify({'error': 'Storm not found'}), 404
    
    zones = Zone.get_latest_zones(storm.id)
    
    if not zones:
        return jsonify({
            'storm_id': storm_id,
            'zones': [],
            'message': 'No zones generated yet'
        })
    
    features = [zone.to_geojson_feature() for zone in zones]
    
    return jsonify({
        'storm_id': storm_id,
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'zone_count': len(features),
            'generated_at_utc': zones[0].generated_at_utc.isoformat() if zones else None
        }
    })
