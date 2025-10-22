"""
Storm Archival Worker Tasks
Handles automatic archival of inactive/dormant storms
"""
from datetime import datetime, timedelta
from sqlalchemy import and_
from celery import Task
from flask import current_app

from tctfs_app.extensions import db, cache
from tctfs_app.models import Storm, Advisory, ForecastPoint, Zone, MediaThumb, Subscription
from tctfs_app.workers.queue import celery
from tctfs_app.services.alerts.emailer import send_archival_notification
from tctfs_app.services.thumbnails.builder import generate_summary_thumbnail
from tctfs_app.utils.geojson import storm_to_geojson, forecasts_to_geojson, zones_to_geojson


# Configuration thresholds (hours)
DORMANT_THRESHOLD = 24  # No advisories for 24h → dormant
ARCHIVE_THRESHOLD = 168  # No advisories for 7 days → archive


@celery.task(name='archival.check_dormant_storms', bind=True)
def check_dormant_storms(self: Task):
    """
    Scan active storms and mark as dormant if no recent advisories
    Runs every hour
    """
    threshold_time = datetime.utcnow() - timedelta(hours=DORMANT_THRESHOLD)
    
    # Find active storms with no recent advisories
    dormant_candidates = db.session.query(Storm).join(Advisory).filter(
        Storm.status == 'active',
        Advisory.issued_at_utc < threshold_time
    ).group_by(Storm.id).having(
        db.func.max(Advisory.issued_at_utc) < threshold_time
    ).all()
    
    dormant_count = 0
    for storm in dormant_candidates:
        current_app.logger.info(f"Marking storm {storm.storm_id} ({storm.name}) as dormant")
        
        storm.status = 'dormant'
        storm.last_status_change_at = datetime.utcnow()
        
        # Log the state change
        from tctfs_app.models.audit_log import AuditLog
        AuditLog.create(
            actor='system',
            action='storm_status_change',
            entity=f'storm:{storm.id}',
            details={
                'storm_id': storm.storm_id,
                'name': storm.name,
                'old_status': 'active',
                'new_status': 'dormant',
                'reason': f'No advisories for {DORMANT_THRESHOLD}h',
                'last_advisory': storm.last_advisory_no,
                'last_advisory_time': storm.last_seen.isoformat() if storm.last_seen else None
            }
        )
        
        # Notify subscribers
        _notify_storm_status_change(storm, 'dormant')
        
        dormant_count += 1
    
    db.session.commit()
    
    # Clear relevant caches
    if dormant_count > 0:
        cache.delete('active_storms_list')
        cache.delete('dashboard_summary')
    
    return {
        'dormant_count': dormant_count,
        'checked_at': datetime.utcnow().isoformat()
    }


@celery.task(name='archival.check_archive_storms', bind=True)
def check_archive_storms(self: Task):
    """
    Scan dormant storms and archive if criteria met
    Runs every 6 hours
    """
    threshold_time = datetime.utcnow() - timedelta(hours=ARCHIVE_THRESHOLD)
    
    # Find dormant storms ready for archival
    archive_candidates = db.session.query(Storm).join(Advisory).filter(
        Storm.status == 'dormant',
        Advisory.issued_at_utc < threshold_time
    ).group_by(Storm.id).having(
        db.func.max(Advisory.issued_at_utc) < threshold_time
    ).all()
    
    archived_count = 0
    for storm in archive_candidates:
        current_app.logger.info(f"Archiving storm {storm.storm_id} ({storm.name})")
        
        # Execute archival workflow
        try:
            archive_storm(storm.id)
            archived_count += 1
        except Exception as e:
            current_app.logger.error(f"Failed to archive storm {storm.id}: {str(e)}")
            # Don't fail the whole batch, continue with others
    
    return {
        'archived_count': archived_count,
        'checked_at': datetime.utcnow().isoformat()
    }


@celery.task(name='archival.archive_storm', bind=True)
def archive_storm(self: Task, storm_id: int, reason: str = 'automatic', admin_id: int = None):
    """
    Execute full archival workflow for a storm
    
    Args:
        storm_id: Storm database ID
        reason: Reason for archival ('automatic', 'manual_admin', 'dissipated', 'landfall')
        admin_id: Admin user ID if manually triggered
    """
    storm = Storm.query.get_or_404(storm_id)
    
    if storm.status == 'archived':
        current_app.logger.warning(f"Storm {storm_id} already archived")
        return {'status': 'already_archived', 'storm_id': storm.storm_id}
    
    current_app.logger.info(f"Starting archival workflow for storm {storm.storm_id}")
    
    # Step 1: Pre-archival validation
    validation = _pre_archive_validation(storm)
    if not validation['valid']:
        current_app.logger.error(f"Pre-archival validation failed: {validation['errors']}")
        raise ValueError(f"Cannot archive storm: {', '.join(validation['errors'])}")
    
    # Step 2: Freeze data (mark as archived)
    storm.status = 'archived'
    storm.archived_at = datetime.utcnow()
    storm.archival_reason = reason
    storm.last_status_change_at = datetime.utcnow()
    
    # Step 3: Generate archive artifacts
    artifacts = _generate_archive_artifacts(storm)
    
    # Step 4: Update archive index
    _update_archive_index(storm, artifacts)
    
    # Step 5: Create audit log
    from tctfs_app.models.audit_log import AuditLog
    AuditLog.create(
        actor=f'admin:{admin_id}' if admin_id else 'system',
        action='storm_archived',
        entity=f'storm:{storm.id}',
        details={
            'storm_id': storm.storm_id,
            'name': storm.name,
            'basin': storm.basin,
            'reason': reason,
            'first_seen': storm.first_seen.isoformat() if storm.first_seen else None,
            'last_seen': storm.last_seen.isoformat() if storm.last_seen else None,
            'peak_intensity_kt': artifacts['stats']['peak_intensity_kt'],
            'advisories_count': artifacts['stats']['advisories_count'],
            'archived_at': storm.archived_at.isoformat()
        }
    )
    
    # Step 6: Notify subscribers
    _notify_storm_archived(storm, artifacts)
    
    # Step 7: Cleanup
    _cleanup_after_archival(storm)
    
    db.session.commit()
    
    current_app.logger.info(f"Storm {storm.storm_id} archived successfully")
    
    return {
        'status': 'archived',
        'storm_id': storm.storm_id,
        'name': storm.name,
        'archived_at': storm.archived_at.isoformat(),
        'artifacts': artifacts
    }


def _pre_archive_validation(storm: Storm) -> dict:
    """Validate storm is ready for archival"""
    errors = []
    
    # Check has advisories
    advisory_count = Advisory.query.filter_by(storm_id=storm.id).count()
    if advisory_count == 0:
        errors.append('No advisories found')
    
    # Check has thumbnail
    if not storm.last_thumb_url:
        current_app.logger.warning(f"Storm {storm.id} missing thumbnail, will generate")
    
    # Check no pending alerts
    from tctfs_app.models.alert_event import AlertEvent
    pending_alerts = AlertEvent.query.filter(
        AlertEvent.storm_id == storm.id,
        AlertEvent.delivery_status.in_(['pending', 'sending'])
    ).count()
    
    if pending_alerts > 0:
        errors.append(f'{pending_alerts} pending alerts')
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'advisory_count': advisory_count
    }


def _generate_archive_artifacts(storm: Storm) -> dict:
    """Generate all archive artifacts for the storm"""
    
    # Calculate statistics
    advisories = Advisory.query.filter_by(storm_id=storm.id).order_by(Advisory.issued_at_utc).all()
    
    peak_intensity = max((a.vmax_kt for a in advisories if a.vmax_kt), default=0)
    min_pressure = min((a.mslp_hpa for a in advisories if a.mslp_hpa), default=None)
    
    # Calculate ACE (Accumulated Cyclone Energy)
    # ACE = sum of (Vmax^2 / 10000) for every 6-hour period where Vmax >= 34kt
    ace = 0.0
    for advisory in advisories:
        if advisory.vmax_kt and advisory.vmax_kt >= 34:
            ace += (advisory.vmax_kt ** 2) / 10000.0
    
    # Calculate track length
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
    
    # Get forecast count
    forecast_count = ForecastPoint.query.filter_by(
        storm_id=storm.id,
        is_final=True
    ).count()
    
    # Get zone stats
    zones = Zone.query.filter_by(storm_id=storm.id).all()
    watch_hours = sum(
        (z.valid_to_utc - z.valid_from_utc).total_seconds() / 3600
        for z in zones if z.type == 'watch'
    )
    warning_hours = sum(
        (z.valid_to_utc - z.valid_from_utc).total_seconds() / 3600
        for z in zones if z.type == 'warning'
    )
    
    stats = {
        'storm_id': storm.storm_id,
        'basin': storm.basin,
        'name': storm.name,
        'season': storm.first_seen.year if storm.first_seen else None,
        'duration_hours': round(duration_hours, 1),
        'peak_intensity_kt': peak_intensity,
        'peak_intensity_time': max(
            ((a.issued_at_utc, a.vmax_kt) for a in advisories if a.vmax_kt),
            key=lambda x: x[1],
            default=(None, None)
        )[0].isoformat() if advisories else None,
        'min_pressure_hpa': min_pressure,
        'ace': round(ace, 2),
        'track_length_km': round(track_length_km, 1),
        'advisories_count': len(advisories),
        'forecast_points_count': forecast_count,
        'landfall_count': 0,  # TODO: Implement landfall detection
        'watch_hours': round(watch_hours, 1),
        'warning_hours': round(warning_hours, 1),
        'archived_at': datetime.utcnow().isoformat()
    }
    
    # Generate summary thumbnail if missing
    if not storm.last_thumb_url:
        thumb_url = generate_summary_thumbnail(storm)
        storm.last_thumb_url = thumb_url
    
    # Generate export packages
    export_urls = _generate_export_packages(storm)
    
    return {
        'stats': stats,
        'thumbnail_url': storm.last_thumb_url,
        'export_urls': export_urls
    }


def _generate_export_packages(storm: Storm) -> dict:
    """Generate CSV/GeoJSON/KML export files"""
    import csv
    import json
    from io import StringIO
    
    # Get all data
    advisories = Advisory.query.filter_by(storm_id=storm.id).order_by(Advisory.issued_at_utc).all()
    forecasts = ForecastPoint.query.filter_by(
        storm_id=storm.id,
        is_final=True
    ).order_by(ForecastPoint.valid_at_utc).all()
    zones = Zone.query.filter_by(storm_id=storm.id).all()
    
    # Generate CSV
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow([
        'advisory_no', 'time_utc', 'latitude', 'longitude', 
        'vmax_kt', 'mslp_hpa', 'motion_deg', 'motion_kt'
    ])
    for adv in advisories:
        writer.writerow([
            adv.advisory_no,
            adv.issued_at_utc.isoformat(),
            adv.center_geom.y if adv.center_geom else None,
            adv.center_geom.x if adv.center_geom else None,
            adv.vmax_kt,
            adv.mslp_hpa,
            adv.motion_bearing_deg,
            adv.motion_speed_kt
        ])
    
    # Save to storage (S3/MinIO or local filesystem)
    csv_filename = f"{storm.storm_id}-{storm.first_seen.year}-track.csv"
    csv_url = _save_export_file(csv_filename, csv_buffer.getvalue())
    
    # Generate GeoJSON
    geojson_data = {
        'type': 'FeatureCollection',
        'properties': {
            'storm_id': storm.storm_id,
            'name': storm.name,
            'basin': storm.basin
        },
        'features': []
    }
    
    # Add track
    geojson_data['features'].append(storm_to_geojson(storm, advisories))
    
    # Add forecasts
    if forecasts:
        geojson_data['features'].append(forecasts_to_geojson(forecasts))
    
    # Add zones
    for zone in zones:
        geojson_data['features'].append(zones_to_geojson(zone))
    
    geojson_filename = f"{storm.storm_id}-{storm.first_seen.year}-complete.geojson"
    geojson_url = _save_export_file(geojson_filename, json.dumps(geojson_data, indent=2))
    
    # TODO: Generate KML
    kml_url = None
    
    return {
        'csv': csv_url,
        'geojson': geojson_url,
        'kml': kml_url
    }


def _save_export_file(filename: str, content: str) -> str:
    """Save export file to storage and return URL"""
    # TODO: Implement S3/MinIO upload
    # For now, save locally
    import os
    export_dir = current_app.config.get('EXPORT_DIR', '/tmp/tctfs_exports')
    os.makedirs(export_dir, exist_ok=True)
    
    filepath = os.path.join(export_dir, filename)
    with open(filepath, 'w') as f:
        f.write(content)
    
    return f"/exports/{filename}"


def _update_archive_index(storm: Storm, artifacts: dict):
    """Update the archive index table for fast searching"""
    # This would insert/update a denormalized table for search optimization
    # See the archival doc for full SQL schema
    pass


def _notify_storm_status_change(storm: Storm, new_status: str):
    """Notify subscribers of storm status change"""
    from tctfs_app.models.subscription import Subscription
    
    subscriptions = Subscription.query.filter(
        db.or_(
            Subscription.storm_id == storm.id,
            Subscription.basin == storm.basin
        ),
        Subscription.email_enabled == True
    ).all()
    
    for sub in subscriptions:
        send_archival_notification(
            user=sub.user,
            storm=storm,
            event_type=f'storm_{new_status}',
            details={'status': new_status}
        )


def _notify_storm_archived(storm: Storm, artifacts: dict):
    """Send final archival notification to subscribers"""
    from tctfs_app.models.subscription import Subscription
    
    subscriptions = Subscription.query.filter(
        db.or_(
            Subscription.storm_id == storm.id,
            Subscription.basin == storm.basin
        ),
        Subscription.email_enabled == True
    ).all()
    
    for sub in subscriptions:
        send_archival_notification(
            user=sub.user,
            storm=storm,
            event_type='storm_archived',
            details={
                'stats': artifacts['stats'],
                'exports': artifacts['export_urls'],
                'permalink': f"{current_app.config['BASE_URL']}/archive/storms/{storm.id}"
            }
        )


def _cleanup_after_archival(storm: Storm):
    """Cleanup tasks after archival"""
    # Remove from active polling queue
    cache.delete(f'storm:{storm.id}:polling_active')
    
    # Clear cached forecast data
    cache.delete(f'storm:{storm.id}:forecast')
    cache.delete(f'storm:{storm.id}:zones')
    
    # Update dashboard caches
    cache.delete('active_storms_list')
    cache.delete('dashboard_summary')
    cache.delete(f'basin:{storm.basin}:storms')


@celery.task(name='archival.reactivate_storm', bind=True)
def reactivate_storm(self: Task, storm_id: int):
    """
    Reactivate a dormant storm (e.g., if new advisory arrives)
    Should be called by the ingest worker when new data detected
    """
    storm = Storm.query.get_or_404(storm_id)
    
    if storm.status != 'dormant':
        return {'status': 'not_dormant', 'current_status': storm.status}
    
    current_app.logger.info(f"Reactivating storm {storm.storm_id}")
    
    storm.status = 'active'
    storm.last_status_change_at = datetime.utcnow()
    
    # Log reactivation
    from tctfs_app.models.audit_log import AuditLog
    AuditLog.create(
        actor='system',
        action='storm_reactivated',
        entity=f'storm:{storm.id}',
        details={
            'storm_id': storm.storm_id,
            'name': storm.name,
            'reactivated_at': datetime.utcnow().isoformat()
        }
    )
    
    # Notify subscribers
    _notify_storm_status_change(storm, 'active')
    
    db.session.commit()
    
    return {
        'status': 'reactivated',
        'storm_id': storm.storm_id,
        'name': storm.name
    }
