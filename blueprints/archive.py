"""
Archive API Blueprint
REST endpoints for accessing archived storms
"""
from flask import Blueprint, jsonify, request, send_file, current_app
from sqlalchemy import and_, or_, extract, func
from datetime import datetime

from tctfs_app.extensions import db, cache
from tctfs_app.models import Storm, Advisory, ForecastPoint, Zone
from tctfs_app.schemas import StormSchema, AdvisorySchema, ForecastSchema, ZoneSchema
from tctfs_app.utils.http import etag_response, last_modified_response

archive_bp = Blueprint('archive', __name__, url_prefix='/api/archive')


@archive_bp.route('/storms', methods=['GET'])
@cache.cached(timeout=3600, query_string=True)  # Cache for 1 hour
def list_archived_storms():
    """
    GET /api/archive/storms
    
    Query params:
        - basin: WP|EP|IO|SH|AL|CP
        - season: 2024|2023|...
        - min_intensity: 64|100|...
        - max_intensity: ...
        - name: partial match
        - limit: 50 (default)
        - offset: 0
        - sort: archived_at|peak_intensity|name (default: archived_at)
        - order: desc|asc (default: desc)
    """
    # Parse query parameters
    basin = request.args.get('basin')
    season = request.args.get('season', type=int)
    min_intensity = request.args.get('min_intensity', type=int)
    max_intensity = request.args.get('max_intensity', type=int)
    name = request.args.get('name', '').strip()
    limit = min(request.args.get('limit', 50, type=int), 100)
    offset = request.args.get('offset', 0, type=int)
    sort_by = request.args.get('sort', 'archived_at')
    order = request.args.get('order', 'desc')
    
    # Build query
    query = Storm.query.filter(Storm.status == 'archived')
    
    if basin:
        query = query.filter(Storm.basin == basin.upper())
    
    if season:
        query = query.filter(extract('year', Storm.first_seen) == season)
    
    if name:
        query = query.filter(Storm.name.ilike(f'%{name}%'))
    
    # Intensity filtering requires joining advisories
    if min_intensity or max_intensity:
        subq = db.session.query(
            Advisory.storm_id,
            func.max(Advisory.vmax_kt).label('peak_vmax')
        ).group_by(Advisory.storm_id).subquery()
        
        query = query.join(subq, Storm.id == subq.c.storm_id)
        
        if min_intensity:
            query = query.filter(subq.c.peak_vmax >= min_intensity)
        if max_intensity:
            query = query.filter(subq.c.peak_vmax <= max_intensity)
    
    # Total count (before pagination)
    total = query.count()
    
    # Sorting
    if sort_by == 'archived_at':
        order_col = Storm.archived_at
    elif sort_by == 'peak_intensity':
        # This would require a subquery or materialized view
        # For now, default to archived_at
        order_col = Storm.archived_at
    elif sort_by == 'name':
        order_col = Storm.name
    else:
        order_col = Storm.archived_at
    
    if order == 'asc':
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())
    
    # Pagination
    query = query.limit(limit).offset(offset)
    
    storms = query.all()
    
    # Serialize with stats
    schema = StormSchema(many=True)
    results = []
    
    for storm in storms:
        storm_data = schema.dump(storm)
        
        # Add archive-specific metadata
        advisories = Advisory.query.filter_by(storm_id=storm.id).all()
        peak_intensity = max((a.vmax_kt for a in advisories if a.vmax_kt), default=0)
        min_pressure = min((a.mslp_hpa for a in advisories if a.mslp_hpa), default=None)
        
        # Calculate ACE
        ace = sum(
            (a.vmax_kt ** 2) / 10000.0
            for a in advisories
            if a.vmax_kt and a.vmax_kt >= 34
        )
        
        storm_data.update({
            'archived_at': storm.archived_at.isoformat() if storm.archived_at else None,
            'peak_intensity_kt': peak_intensity,
            'min_pressure_hpa': min_pressure,
            'ace': round(ace, 2),
            'advisories_count': len(advisories),
            'permalink': f'/archive/storms/{storm.id}'
        })
        
        results.append(storm_data)
    
    return jsonify({
        'total': total,
        'count': len(results),
        'limit': limit,
        'offset': offset,
        'storms': results
    })


@archive_bp.route('/storms/<int:storm_id>', methods=['GET'])
@cache.cached(timeout=86400)  # Cache for 24 hours (immutable data)
def get_archived_storm(storm_id: int):
    """
    GET /api/archive/storms/{id}
    
    Full storm details including all advisories, forecasts, zones
    """
    storm = Storm.query.filter_by(id=storm_id, status='archived').first_or_404()
    
    # Get all related data
    advisories = Advisory.query.filter_by(storm_id=storm.id).order_by(Advisory.issued_at_utc).all()
    forecasts = ForecastPoint.query.filter_by(
        storm_id=storm.id,
        is_final=True
    ).order_by(ForecastPoint.valid_at_utc).all()
    zones = Zone.query.filter_by(storm_id=storm.id).all()
    
    # Calculate statistics
    peak_intensity = max((a.vmax_kt for a in advisories if a.vmax_kt), default=0)
    min_pressure = min((a.mslp_hpa for a in advisories if a.mslp_hpa), default=None)
    
    ace = sum(
        (a.vmax_kt ** 2) / 10000.0
        for a in advisories
        if a.vmax_kt and a.vmax_kt >= 34
    )
    
    # Track length
    from tctfs_app.services.geodesy.spheroid import calculate_distance
    track_length_km = 0.0
    for i in range(1, len(advisories)):
        prev = advisories[i-1]
        curr = advisories[i]
        if prev.center_geom and curr.center_geom:
            dist = calculate_distance(
                prev.center_geom.y, prev.center_geom.x,
                curr.center_geom.y, curr.center_geom.x
            )
            track_length_km += dist
    
    # Duration
    duration_hours = 0
    if advisories:
        first_time = advisories[0].issued_at_utc
        last_time = advisories[-1].issued_at_utc
        duration_hours = (last_time - first_time).total_seconds() / 3600
    
    # Serialize
    storm_schema = StormSchema()
    advisory_schema = AdvisorySchema(many=True)
    forecast_schema = ForecastSchema(many=True)
    zone_schema = ZoneSchema(many=True)
    
    return jsonify({
        'storm': storm_schema.dump(storm),
        'statistics': {
            'duration_hours': round(duration_hours, 1),
            'peak_intensity_kt': peak_intensity,
            'min_pressure_hpa': min_pressure,
            'ace': round(ace, 2),
            'track_length_km': round(track_length_km, 1),
            'advisories_count': len(advisories),
            'forecast_points_count': len(forecasts),
            'zones_count': len(zones)
        },
        'advisories': advisory_schema.dump(advisories),
        'forecasts': forecast_schema.dump(forecasts),
        'zones': zone_schema.dump(zones),
        'archived_at': storm.archived_at.isoformat() if storm.archived_at else None
    })


@archive_bp.route('/storms/<int:storm_id>/track', methods=['GET'])
@cache.cached(timeout=86400, query_string=True)
def get_archived_track(storm_id: int):
    """
    GET /api/archive/storms/{id}/track
    
    Query params:
        - full: true (include forecast history)
    """
    storm = Storm.query.filter_by(id=storm_id, status='archived').first_or_404()
    include_forecasts = request.args.get('full', 'false').lower() == 'true'
    
    advisories = Advisory.query.filter_by(storm_id=storm.id).order_by(Advisory.issued_at_utc).all()
    
    advisory_schema = AdvisorySchema(many=True)
    track_data = {
        'storm_id': storm.storm_id,
        'name': storm.name,
        'track': advisory_schema.dump(advisories)
    }
    
    if include_forecasts:
        # Get all historical forecast tracks
        forecasts = ForecastPoint.query.filter_by(
            storm_id=storm.id,
            is_final=True
        ).order_by(ForecastPoint.valid_at_utc).all()
        
        # Group by issuance time (would need to add issued_at field to ForecastPoint)
        # For now, return all forecast points
        forecast_schema = ForecastSchema(many=True)
        track_data['forecasts'] = forecast_schema.dump(forecasts)
    
    return jsonify(track_data)


@archive_bp.route('/storms/<int:storm_id>/zones', methods=['GET'])
@cache.cached(timeout=86400)
def get_archived_zones(storm_id: int):
    """GET /api/archive/storms/{id}/zones"""
    storm = Storm.query.filter_by(id=storm_id, status='archived').first_or_404()
    
    zones = Zone.query.filter_by(storm_id=storm.id).order_by(Zone.valid_from_utc).all()
    
    zone_schema = ZoneSchema(many=True)
    return jsonify({
        'storm_id': storm.storm_id,
        'zones': zone_schema.dump(zones)
    })


@archive_bp.route('/storms/<int:storm_id>/export', methods=['GET'])
def export_archived_storm(storm_id: int):
    """
    GET /api/archive/storms/{id}/export?format=csv|geojson|kml
    
    Download complete storm data
    """
    storm = Storm.query.filter_by(id=storm_id, status='archived').first_or_404()
    export_format = request.args.get('format', 'csv').lower()
    
    if export_format not in ['csv', 'geojson', 'kml']:
        return jsonify({'error': 'Invalid format. Use csv, geojson, or kml'}), 400
    
    # Check if export already exists
    export_filename = f"{storm.storm_id}-{storm.first_seen.year if storm.first_seen else 'unknown'}-track.{export_format}"
    export_dir = current_app.config.get('EXPORT_DIR', '/tmp/tctfs_exports')
    export_path = f"{export_dir}/{export_filename}"
    
    import os
    if not os.path.exists(export_path):
        # Generate export on-demand
        from tctfs_app.workers.tasks_archival import _generate_export_packages
        _generate_export_packages(storm)
    
    if os.path.exists(export_path):
        return send_file(
            export_path,
            as_attachment=True,
            download_name=export_filename,
            mimetype='text/csv' if export_format == 'csv' else 'application/json'
        )
    
    return jsonify({'error': 'Export file not found'}), 404


@archive_bp.route('/statistics', methods=['GET'])
@cache.cached(timeout=3600, query_string=True)
def get_archive_statistics():
    """
    GET /api/archive/statistics?basin=WP&season=2024
    
    Season/basin summary statistics
    """
    basin = request.args.get('basin')
    season = request.args.get('season', type=int)
    
    query = Storm.query.filter(Storm.status == 'archived')
    
    if basin:
        query = query.filter(Storm.basin == basin.upper())
    
    if season:
        query = query.filter(extract('year', Storm.first_seen) == season)
    
    storms = query.all()
    
    if not storms:
        return jsonify({
            'basin': basin,
            'season': season,
            'total_systems': 0
        })
    
    # Calculate aggregate statistics
    total_systems = len(storms)
    named_storms = sum(1 for s in storms if s.name and s.name != 'INVEST')
    
    # Get all advisories for intensity classification
    all_advisories = Advisory.query.filter(
        Advisory.storm_id.in_([s.id for s in storms])
    ).all()
    
    # Peak intensities per storm
    storm_peaks = {}
    for adv in all_advisories:
        if adv.storm_id not in storm_peaks:
            storm_peaks[adv.storm_id] = 0
        if adv.vmax_kt:
            storm_peaks[adv.storm_id] = max(storm_peaks[adv.storm_id], adv.vmax_kt)
    
    # Count by category (basin-dependent thresholds)
    if basin == 'WP':
        # Typhoon >= 64kt, Major typhoon >= 100kt
        typhoons = sum(1 for v in storm_peaks.values() if v >= 64)
        major_typhoons = sum(1 for v in storm_peaks.values() if v >= 100)
    else:
        # Hurricane >= 64kt, Major hurricane >= 96kt
        typhoons = sum(1 for v in storm_peaks.values() if v >= 64)
        major_typhoons = sum(1 for v in storm_peaks.values() if v >= 96)
    
    # Total ACE
    ace_total = 0.0
    for adv in all_advisories:
        if adv.vmax_kt and adv.vmax_kt >= 34:
            ace_total += (adv.vmax_kt ** 2) / 10000.0
    
    # Peak system
    peak_storm = max(storms, key=lambda s: storm_peaks.get(s.id, 0))
    
    # Landfall count (placeholder - needs implementation)
    landfall_count = 0
    
    # Average duration
    durations = []
    for storm in storms:
        advisories = [a for a in all_advisories if a.storm_id == storm.id]
        if advisories:
            sorted_adv = sorted(advisories, key=lambda a: a.issued_at_utc)
            duration = (sorted_adv[-1].issued_at_utc - sorted_adv[0].issued_at_utc).total_seconds() / 3600
            durations.append(duration)
    
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    return jsonify({
        'basin': basin or 'ALL',
        'season': season,
        'total_systems': total_systems,
        'named_storms': named_storms,
        'typhoons': typhoons,
        'major_typhoons': major_typhoons,
        'ace_total': round(ace_total, 2),
        'peak_system': {
            'storm_id': peak_storm.storm_id,
            'name': peak_storm.name,
            'peak_intensity_kt': storm_peaks.get(peak_storm.id, 0)
        },
        'landfall_count': landfall_count,
        'avg_duration_hours': round(avg_duration, 1)
    })


@archive_bp.route('/seasons/<basin>', methods=['GET'])
@cache.cached(timeout=86400)
def list_seasons(basin: str):
    """
    GET /api/archive/seasons/{basin}
    
    List all available seasons for a basin
    """
    basin = basin.upper()
    
    seasons = db.session.query(
        extract('year', Storm.first_seen).label('season')
    ).filter(
        Storm.basin == basin,
        Storm.status == 'archived'
    ).distinct().order_by('season').all()
    
    season_list = [int(s[0]) for s in seasons if s[0]]
    
    return jsonify({
        'basin': basin,
        'seasons': season_list,
        'count': len(season_list)
    })


@archive_bp.route('/search', methods=['POST'])
def search_archived_storms():
    """
    POST /api/archive/search
    
    Advanced search with multiple criteria
    Body: {
        "basin": "WP",
        "season_start": 2020,
        "season_end": 2024,
        "min_intensity": 100,
        "name_contains": "yagi",
        "bbox": [120, 10, 130, 25]  // [west, south, east, north]
    }
    """
    data = request.get_json()
    
    query = Storm.query.filter(Storm.status == 'archived')
    
    # Basin filter
    if 'basin' in data:
        query = query.filter(Storm.basin == data['basin'].upper())
    
    # Season range
    if 'season_start' in data:
        query = query.filter(extract('year', Storm.first_seen) >= data['season_start'])
    if 'season_end' in data:
        query = query.filter(extract('year', Storm.first_seen) <= data['season_end'])
    
    # Name search
    if 'name_contains' in data:
        query = query.filter(Storm.name.ilike(f"%{data['name_contains']}%"))
    
    # Intensity filtering
    if 'min_intensity' in data:
        subq = db.session.query(
            Advisory.storm_id,
            func.max(Advisory.vmax_kt).label('peak_vmax')
        ).group_by(Advisory.storm_id).subquery()
        
        query = query.join(subq, Storm.id == subq.c.storm_id)
        query = query.filter(subq.c.peak_vmax >= data['min_intensity'])
    
    # Spatial filtering (bounding box)
    if 'bbox' in data:
        west, south, east, north = data['bbox']
        # This requires a spatial join with advisories
        # Would be better implemented with a simplified track geometry on storm table
        pass
    
    storms = query.limit(100).all()
    
    schema = StormSchema(many=True)
    return jsonify({
        'count': len(storms),
        'storms': schema.dump(storms)
    })
