"""
Celery tasks for storm data ingestion.
"""
import logging
from .queue import celery_app
from ..services.ingest.cimss_discovery import get_discovery_service
from ..services.ingest.history_fetch import get_history_fetch_service
from ..services.ingest.adt_list_parser import get_adt_list_parser
from ..extensions import db
from ..models.storm import Storm
from ..models.advisory import Advisory
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from ..services.ingest.cimss_2dwind_fetch import get_cimss_2dwind_service
from ..models.radii import Radii

logger = logging.getLogger(__name__)


@celery_app.task(name='tctfs_app.workers.tasks_ingest.discover_and_ingest_storms')
def discover_and_ingest_storms():
    """Discover all active storms and ingest their track data."""
    from .. import create_app
    app = create_app()
    
    with app.app_context():
        logger.info("🔍 Discovering storms from CIMSS...")
        
        discovery = get_discovery_service()
        discovered_storms = discovery.discover_storms(use_conditional_get=True)
        
        logger.info(f"Found {len(discovered_storms)} active storms")
        
        for storm_data in discovered_storms:
            try:
                storm_id = storm_data['storm_id']
                
                # Get or create storm
                storm = Storm.query.filter_by(storm_id=storm_id).first()
                if not storm:
                    adt_url = f"https://tropic.ssec.wisc.edu/real-time/adt/{storm_id}-list.txt"
                    
                    storm = Storm(
                        storm_id=storm_id,
                        basin=storm_data['basin'],
                        name=storm_data.get('name'),
                        status='active',
                        history_file_url=adt_url,
                        first_seen=db.func.now()
                    )
                    db.session.add(storm)
                    db.session.commit()
                    logger.info(f"✅ Created storm: {storm_id}")
                
                # Update storm status
                storm.status = 'active'
                storm.last_seen = db.func.now()
                
                # Fetch track data
                adt_url = f"https://tropic.ssec.wisc.edu/real-time/adt/{storm_id}-list.txt"
                storm.history_file_url = adt_url
                
                history_fetch = get_history_fetch_service()
                result = history_fetch.fetch_history_file(adt_url, use_cache=True)
                
                if result:
                    # Parse ADT format
                    parser = get_adt_list_parser()
                    advisories_data = parser.parse_file(result['content'])
                    
                    logger.info(f"📊 Parsed {len(advisories_data)} advisories for {storm_id}")
                    
                    # Clear old advisories
                    Advisory.query.filter_by(storm_id=storm.id).delete()
                    
                    # Add new advisories
                    for i, adv_data in enumerate(advisories_data):
                        point = Point(adv_data['longitude'], adv_data['latitude'])
                        geom = from_shape(point, srid=4326)
                        
                        advisory = Advisory(
                            storm_id=storm.id,
                            advisory_no=i + 1,
                            issued_at_utc=adv_data['timestamp'],
                            center_geom=geom,
                            vmax_kt=adv_data['vmax_kt'],
                            mslp_hpa=adv_data['mslp_hpa']
                        )
                        db.session.add(advisory)
                    
                    storm.last_advisory_no = len(advisories_data)
                    db.session.commit()
                    
                    logger.info(f"✅ Updated {storm_id} with {len(advisories_data)} advisories")
                
            except Exception as e:
                logger.error(f"❌ Error ingesting {storm_data['storm_id']}: {e}", exc_info=True)
                db.session.rollback()


@celery_app.task(name='tctfs_app.workers.tasks_ingest.health_check')
def health_check():
    """Health check task."""
    logger.info("Health check: OK")
    return "OK"

@celery_app.task(name='tctfs_app.workers.tasks_ingest.ingest_radii_for_storm')
def ingest_radii_for_storm(storm_id: str):
    """Fetch and ingest wind radii from CIMSS 2dwind files."""
    from .. import create_app
    app = create_app()
    
    with app.app_context():
        logger.info(f"🌬️ Ingesting radii for storm {storm_id}")
        
        storm = Storm.query.filter_by(storm_id=storm_id).first()
        if not storm:
            logger.error(f"Storm {storm_id} not found")
            return
        
        service = get_cimss_2dwind_service()
        radii_records = service.fetch_and_parse(storm_id)
        
        if not radii_records:
            logger.warning(f"No radii data for {storm_id}")
            return
        
        logger.info(f"Found {len(radii_records)} radii records")
        
        advisories = Advisory.query.filter_by(storm_id=storm.id).all()
        advisory_by_time = {adv.issued_at_utc: adv for adv in advisories}
        
        radii_inserted = 0
        
        for record in radii_records:
            timestamp = record['timestamp']
            advisory = advisory_by_time.get(timestamp)
            
            if not advisory:
                closest = None
                min_diff = None
                
                for adv_time, adv in advisory_by_time.items():
                    diff = abs((adv_time - timestamp).total_seconds())
                    if diff <= 10800:
                        if min_diff is None or diff < min_diff:
                            min_diff = diff
                            closest = adv
                
                advisory = closest
            
            if not advisory:
                continue
            
            for quadrant, quad_radii in record['radii'].items():
                existing = Radii.query.filter_by(
                    advisory_id=advisory.id,
                    quadrant=quadrant
                ).first()
                
                if existing:
                    existing.r34_nm = quad_radii['r34_nm']
                    existing.r50_nm = quad_radii['r50_nm']
                    existing.r64_nm = quad_radii['r64_nm']
                else:
                    radii = Radii(
                        advisory_id=advisory.id,
                        quadrant=quadrant,
                        r34_nm=quad_radii['r34_nm'],
                        r50_nm=quad_radii['r50_nm'],
                        r64_nm=quad_radii['r64_nm']
                    )
                    db.session.add(radii)
                
                radii_inserted += 1
        
        db.session.commit()
        logger.info(f"✅ Inserted {radii_inserted} radii records")


@celery_app.task(name='tctfs_app.workers.tasks_ingest.ingest_radii_for_all_storms')
def ingest_radii_for_all_storms():
    """Ingest radii for all active storms."""
    from .. import create_app
    app = create_app()
    
    with app.app_context():
        active_storms = Storm.query.filter_by(status='active').all()
        
        for storm in active_storms:
            try:
                ingest_radii_for_storm(storm.storm_id)
            except Exception as e:
                logger.error(f"Error ingesting radii for {storm.storm_id}: {e}")
