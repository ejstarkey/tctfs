"""
Forecast API Blueprint - AP-mean forecast endpoints.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('api_forecast', __name__)


@bp.route('/storms/<storm_id>/forecast', methods=['GET'])
@login_required
def get_forecast(storm_id):
    """
    Get AP1-AP30 mean forecast for a storm.
    This is the ONLY forecast shown to users.
    
    Args:
        storm_id: Storm identifier
    
    Query params:
        issuance: Optional specific issuance time (ISO format)
    """
    from ...models import Storm, ForecastPoint
    from datetime import datetime
    
    storm = Storm.get_by_storm_id(storm_id)
    if not storm:
        return jsonify({'error': 'Storm not found'}), 404
    
    # Check for specific issuance time
    issuance_str = request.args.get('issuance')
    
    if issuance_str:
        try:
            issuance_time = datetime.fromisoformat(issuance_str.replace('Z', '+00:00'))
            forecast_points = ForecastPoint.get_forecast_for_issuance(storm.id, issuance_time)
        except:
            return jsonify({'error': 'Invalid issuance time format'}), 400
    else:
        # Get latest forecast
        forecast_points = ForecastPoint.get_latest_forecast(storm.id)
    
    if not forecast_points:
        return jsonify({
            'storm_id': storm_id,
            'forecast': [],
            'message': 'No forecast available'
        })
    
    # Convert to GeoJSON format for easy map rendering
    features = []
    for fp in forecast_points:
        fp_dict = fp.to_dict()
        
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [fp_dict['longitude'], fp_dict['latitude']]
            },
            'properties': {
                'valid_at_utc': fp_dict['valid_at_utc'],
                'lead_time_hours': fp_dict['lead_time_hours'],
                'vmax_kt': fp_dict['vmax_kt'],
                'mslp_hpa': fp_dict['mslp_hpa'],
                'radii': fp_dict['radii'],
                'member_count': fp_dict['member_count']
            }
        })
    
    # Get issuance time from first point
    issuance_time = forecast_points[0].issuance_time_utc.isoformat() if forecast_points else None
    
    return jsonify({
        'storm_id': storm_id,
        'issuance_time_utc': issuance_time,
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'source': 'UCAR A-Decks (AP1-AP30 ensemble mean)',
            'is_final': True,
            'display_opacity': 0.5,  # Always render future path at 50% opacity
            'point_count': len(features)
        }
    })
