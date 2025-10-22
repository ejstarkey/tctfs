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
            a.id as advisory_id,
            a.issued_at_utc,
            ST_Y(a.center_geom) as latitude,
            ST_X(a.center_geom) as longitude,
            a.vmax_kt,
            a.mslp_hpa,
            a.motion_bearing_deg,
            a.motion_speed_kt
        FROM advisories a
        WHERE a.storm_id = :storm_id
        AND a.center_geom IS NOT NULL
        ORDER BY a.issued_at_utc ASC
    """)
    
    result = db.session.execute(sql, {'storm_id': storm.id})
    rows = result.fetchall()
    
    logger.info(f"📊 Found {len(rows)} advisories using RAW SQL")
    
    # Get radii data
    radii_sql = text("""
        SELECT 
            r.advisory_id,
            r.quadrant,
            r.r34_nm,
            r.r50_nm,
            r.r64_nm
        FROM radii r
        JOIN advisories a ON r.advisory_id = a.id
        WHERE a.storm_id = :storm_id
    """)
    
    radii_result = db.session.execute(radii_sql, {'storm_id': storm.id})
    radii_rows = radii_result.fetchall()
    
    # Organize radii by advisory_id
    radii_by_advisory = {}
    for r in radii_rows:
        if r.advisory_id not in radii_by_advisory:
            radii_by_advisory[r.advisory_id] = {}
        radii_by_advisory[r.advisory_id][r.quadrant] = {
            'r34_nm': float(r.r34_nm) if r.r34_nm else None,
            'r50_nm': float(r.r50_nm) if r.r50_nm else None,
            'r64_nm': float(r.r64_nm) if r.r64_nm else None
        }
    
    logger.info(f"📊 Found radii for {len(radii_by_advisory)} advisories")
    
    track = []
    for row in rows:
        track_point = {
            'time': row.issued_at_utc.isoformat() if row.issued_at_utc else None,
            'latitude': float(row.latitude) if row.latitude else None,
            'longitude': float(row.longitude) if row.longitude else None,
            'vmax_kt': float(row.vmax_kt) if row.vmax_kt else None,
            'mslp_hpa': float(row.mslp_hpa) if row.mslp_hpa else None,
            'motion_bearing': float(row.motion_bearing_deg) if row.motion_bearing_deg else None,
            'motion_speed': float(row.motion_speed_kt) if row.motion_speed_kt else None
        }
        
        # Add radii if available
        if row.advisory_id in radii_by_advisory:
            track_point['radii'] = radii_by_advisory[row.advisory_id]
        
        track.append(track_point)
    
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