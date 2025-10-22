"""
Thumbnail Tasks - Generate map thumbnails for storm tracks.
"""
import logging
from datetime import datetime
from .queue import celery
from ..extensions import db
from ..models import Storm, Advisory, MediaThumb
from ..services.thumbnails.builder import get_thumbnail_builder_service

logger = logging.getLogger(__name__)


@celery.task(name='tctfs_app.workers.tasks_thumbs.update_storm_thumbnail_task')
def update_storm_thumbnail_task(storm_id):
    """
    Update thumbnail for a specific storm.
    
    Args:
        storm_id: Database ID of storm
    """
    logger.info(f"Updating thumbnail for storm {storm_id}")
    
    try:
        storm = Storm.query.get(storm_id)
        if not storm:
            logger.error(f"Storm {storm_id} not found")
            return {'status': 'error', 'error': 'Storm not found'}
        
        # Get track points (last 72 hours of advisories)
        advisories = Advisory.query.filter_by(storm_id=storm_id).order_by(Advisory.issued_at_utc.asc()).all()
        
        if not advisories:
            logger.info(f"No advisories for storm {storm.storm_id}, skipping thumbnail")
            return {'status': 'no_data'}
        
        # Extract track points
        track_points = [(adv.center_lat, adv.center_lon) for adv in advisories if adv.center_lat and adv.center_lon]
        
        if not track_points:
            logger.warning(f"No valid track points for storm {storm.storm_id}")
            return {'status': 'no_valid_points'}
        
        # Get latest advisory for metadata
        latest_advisory = advisories[-1]
        
        # Build storm data dict
        storm_data = {
            'storm_id': storm.storm_id,
            'name': storm.name,
            'basin': storm.basin,
            'vmax_kt': latest_advisory.vmax_kt
        }
        
        # Generate thumbnail
        thumbnail_service = get_thumbnail_builder_service()
        image_data = thumbnail_service.generate_thumbnail(
            storm_data=storm_data,
            track_points=track_points,
            width=400,
            height=300
        )
        
        if not image_data:
            logger.error(f"Failed to generate thumbnail for storm {storm.storm_id}")
            return {'status': 'error', 'error': 'Thumbnail generation failed'}
        
        # Save thumbnail
        thumb = MediaThumb.create_thumb(
            storm_id=storm_id,
            advisory_id=latest_advisory.id,
            image_data=image_data,
            width=400,
            height=300
        )
        
        db.session.add(thumb)
        
        # Update storm's last_thumb_url (if storing externally, upload to S3/CDN here)
        # For now, we'll store in DB
        storm.last_thumb_url = f"/api/storms/{storm.storm_id}/media/latest"
        
        db.session.commit()
        
        logger.info(f"Updated thumbnail for storm {storm.storm_id}")
        
        return {
            'status': 'success',
            'storm_id': storm.storm_id,
            'thumb_id': thumb.id,
            'size_bytes': len(image_data)
        }
        
    except Exception as e:
        logger.error(f"Error updating thumbnail for storm {storm_id}: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }


@celery.task(name='tctfs_app.workers.tasks_thumbs.update_all_thumbs_task')
def update_all_thumbs_task():
    """
    Update thumbnails for all active storms (scheduled task).
    """
    logger.info("Updating thumbnails for all active storms")
    
    try:
        active_storms = Storm.query.filter_by(status='active').all()
        
        logger.info(f"Found {len(active_storms)} active storms")
        
        results = []
        for storm in active_storms:
            result = update_storm_thumbnail_task.delay(storm.id)
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
        logger.error(f"Error updating all thumbnails: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }


@celery.task(name='tctfs_app.workers.tasks_thumbs.generate_archive_thumbs_task')
def generate_archive_thumbs_task(storm_id):
    """
    Generate high-quality thumbnails for archived storm.
    
    Args:
        storm_id: Database ID of storm
    """
    logger.info(f"Generating archive thumbnails for storm {storm_id}")
    
    try:
        storm = Storm.query.get(storm_id)
        if not storm:
            return {'status': 'error', 'error': 'Storm not found'}
        
        # Generate at multiple sizes for archive
        sizes = [
            (200, 150),   # Small tile
            (400, 300),   # Medium
            (800, 600),   # Large
        ]
        
        advisories = Advisory.query.filter_by(storm_id=storm_id).order_by(Advisory.issued_at_utc.asc()).all()
        track_points = [(adv.center_lat, adv.center_lon) for adv in advisories if adv.center_lat and adv.center_lon]
        
        if not track_points:
            return {'status': 'no_data'}
        
        latest_advisory = advisories[-1] if advisories else None
        storm_data = {
            'storm_id': storm.storm_id,
            'name': storm.name,
            'basin': storm.basin,
            'vmax_kt': latest_advisory.vmax_kt if latest_advisory else None
        }
        
        thumbnail_service = get_thumbnail_builder_service()
        thumbs_created = 0
        
        for width, height in sizes:
            image_data = thumbnail_service.generate_thumbnail(
                storm_data=storm_data,
                track_points=track_points,
                width=width,
                height=height
            )
            
            if image_data:
                thumb = MediaThumb.create_thumb(
                    storm_id=storm_id,
                    advisory_id=latest_advisory.id if latest_advisory else None,
                    image_data=image_data,
                    width=width,
                    height=height
                )
                db.session.add(thumb)
                thumbs_created += 1
        
        db.session.commit()
        
        logger.info(f"Generated {thumbs_created} archive thumbnails for {storm.storm_id}")
        
        return {
            'status': 'success',
            'storm_id': storm.storm_id,
            'thumbs_created': thumbs_created
        }
        
    except Exception as e:
        logger.error(f"Error generating archive thumbnails: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }
