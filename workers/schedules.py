"""
Celery Beat Schedules - Periodic tasks for polling and updates.
"""
from celery.schedules import crontab
from tctfs_app.workers.tasks_archival import (
    check_dormant_storms,
    check_archive_storms,
    refresh_archive_index,
    validate_archive_integrity
)

# Periodic task schedules
CELERY_BEAT_SCHEDULE = {
    # Discover new storms from CIMSS every 10 minutes
    'discover-storms': {
        'task': 'tctfs_app.workers.tasks_ingest.discover_and_ingest_storms',
        'schedule': 600.0,  # 10 minutes in seconds
    },
    
    # Update existing storm data every 15 minutes
    'update-storm-data': {
        'task': 'tctfs_app.workers.tasks_ingest.update_all_storms',
        'schedule': 900.0,  # 15 minutes
    },
    
    # Fetch and build AP-mean forecasts every 15 minutes
    'update-forecasts': {
        'task': 'tctfs_app.workers.tasks_forecast.update_all_forecasts',
        'schedule': 900.0,  # 15 minutes
    },
    
    # Generate watch/warning zones every 30 minutes
    'generate-zones': {
        'task': 'tctfs_app.workers.tasks_zones.generate_all_zones',
        'schedule': 1800.0,  # 30 minutes
    },
    
    # Health check every 5 minutes
    'health-check': {
        'task': 'tctfs_app.workers.tasks_ingest.health_check',
        'schedule': 300.0,  # 5 minutes
    },
    
    # Archival schedules
    'check-dormant-storms': {
        'task': 'archival.check_dormant_storms',
        'schedule': timedelta(hours=1),
        'options': {'expires': 3600}
    },
    'check-archive-storms': {
        'task': 'archival.check_archive_storms',
        'schedule': timedelta(hours=6),
        'options': {'expires': 21600}
    },
    'refresh-archive-index': {
        'task': 'archival.refresh_archive_index',
        'schedule': crontab(hour=3, minute=0),
        'options': {'expires': 7200}
    },
    'validate-archive-integrity': {
        'task': 'archival.validate_archive_integrity',
        'schedule': crontab(day_of_week=0, hour=2, minute=0),
        'options': {'expires': 14400}
    },    
}
