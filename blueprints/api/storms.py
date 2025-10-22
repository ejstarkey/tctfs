"""
Storms API - REST endpoints for storm data.
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import func, text
import logging

from ...models.storm import Storm
from ...models.advisory import Advisory
from ...extensions import db

logger = logging.getLogger(__name__)

bp = Blueprint('api_storms', __name__, url_prefix='/api/storms')


@bp.route('', methods=['GET'])
def list_storms():
    """List all storms with optional filters."""
    status = request.args.get('status', 'active')
    
    query = Storm.query
    if status:
        query = query.filter_by(status=status)
    
    storms = query.all()
    
    return jsonify({
        'storms': [s.to_dict() for s in storms],
        'count': len(storms)
    })


@bp.route('/<storm_id>', methods=['GET'])
def get_storm(storm_id):
    """Get single storm details."""
    storm = Storm.query.filter_by(storm_id=storm_id).first_or_404()
    return jsonify(storm.to_dict())


@bp.route('/<storm_id>/track', methods=['GET'])
def get_track(storm_id):
    """Get storm track (all advisory positions)."""
    logger.info(f"🔍 API called for storm: {storm_id}")
    
    # Find storm
    storm = Storm.query.filter_by(storm_id=storm_id).first()
    if not storm:
        try:
            storm = Storm.query.get(int(storm_id))
        except:
            return jsonify({'error': 'Storm not found'}), 404
    
    if not storm:
        return jsonify({'error': 'Storm not found'}), 404
    
    logger.info(f"✓ Found storm: {storm.storm_id} (DB ID: {storm.id})")
    
    # Use RAW SQL to bypass any ORM caching issues
    sql = text("""
        SELECT 
            issued_at_utc,
            ST_Y(center_geom) as latitude,
            ST_X(center_geom) as longitude,
            vmax_kt,
            mslp_hpa,
            motion_bearing_deg,
            motion_speed_kt
        FROM advisories
        WHERE storm_id = :storm_id
        AND center_geom IS NOT NULL
        ORDER BY issued_at_utc ASC
    """)
    
    result = db.session.execute(sql, {'storm_id': storm.id})
    rows = result.fetchall()
    
    logger.info(f"📊 Found {len(rows)} advisories using RAW SQL")
    
    track = []
    for row in rows:
        track.append({
            'time': row.issued_at_utc.isoformat() if row.issued_at_utc else None,
            'latitude': float(row.latitude) if row.latitude else None,
            'longitude': float(row.longitude) if row.longitude else None,
            'vmax_kt': float(row.vmax_kt) if row.vmax_kt else None,
            'mslp_hpa': float(row.mslp_hpa) if row.mslp_hpa else None,
            'motion_bearing': float(row.motion_bearing_deg) if row.motion_bearing_deg else None,
            'motion_speed': float(row.motion_speed_kt) if row.motion_speed_kt else None
        })
    
    logger.info(f"✅ Returning {len(track)} track points")
    
    return jsonify({
        'storm_id': storm.storm_id,
        'name': storm.name,
        'basin': storm.basin,
        'track': track
    })


@bp.route('/<storm_id>/forecast', methods=['GET'])
def get_forecast(storm_id):
    """Get forecast track (AP-mean only)."""
    storm = Storm.query.filter_by(storm_id=storm_id).first_or_404()
    return jsonify({
        'storm_id': storm.storm_id,
        'forecast': []
    })


@bp.route('/<storm_id>/zones', methods=['GET'])
def get_zones(storm_id):
    """Get watch/warning zones."""
    storm = Storm.query.filter_by(storm_id=storm_id).first_or_404()
    return jsonify({
        'storm_id': storm.storm_id,
        'zones': []
    })
