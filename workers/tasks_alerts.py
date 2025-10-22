"""
Alert Tasks - Send email notifications for storm updates.
"""
import logging
from datetime import datetime, timedelta
from .queue import celery
from ..extensions import db
from ..models import Storm, Advisory, Zone, Subscription, AlertEvent, User
from ..services.alerts.emailer import send_email
from ..services.alerts.rules import should_send_alert

logger = logging.getLogger(__name__)


@celery.task(name='tctfs_app.workers.tasks_alerts.send_new_advisory_alerts_task')
def send_new_advisory_alerts_task(advisory_id):
    """
    Send alerts for a newly ingested advisory.
    
    Args:
        advisory_id: Database ID of advisory
    """
    logger.info(f"Sending alerts for advisory {advisory_id}")
    
    try:
        advisory = Advisory.query.get(advisory_id)
        if not advisory:
            logger.error(f"Advisory {advisory_id} not found")
            return {'status': 'error', 'error': 'Advisory not found'}
        
        storm = advisory.storm
        
        # Get subscriptions for this storm
        subscriptions = Subscription.query.filter_by(
            storm_id=storm.id,
            is_active=True,
            mode='immediate',
            alert_on_new_advisory=True
        ).all()
        
        logger.info(f"Found {len(subscriptions)} subscriptions for storm {storm.storm_id}")
        
        sent_count = 0
        for subscription in subscriptions:
            if should_send_alert(subscription, 'new_advisory', advisory):
                result = send_advisory_email(subscription.user, storm, advisory)
                
                if result:
                    # Log alert event
                    alert_event = AlertEvent(
                        user_id=subscription.user_id,
                        storm_id=storm.id,
                        event_type='new_advisory',
                        payload={
                            'advisory_id': advisory_id,
                            'issued_at': advisory.issued_at_utc.isoformat(),
                            'vmax_kt': advisory.vmax_kt
                        },
                        sent_at_utc=datetime.utcnow(),
                        delivery_status='sent'
                    )
                    db.session.add(alert_event)
                    sent_count += 1
        
        db.session.commit()
        
        logger.info(f"Sent {sent_count} new advisory alerts for {storm.storm_id}")
        
        return {
            'status': 'success',
            'storm_id': storm.storm_id,
            'alerts_sent': sent_count
        }
        
    except Exception as e:
        logger.error(f"Error sending advisory alerts: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }


@celery.task(name='tctfs_app.workers.tasks_alerts.send_zone_change_alerts_task')
def send_zone_change_alerts_task(storm_id):
    """
    Send alerts for zone changes (watch/warning issued or updated).
    
    Args:
        storm_id: Database ID of storm
    """
    logger.info(f"Sending zone change alerts for storm {storm_id}")
    
    try:
        storm = Storm.query.get(storm_id)
        if not storm:
            logger.error(f"Storm {storm_id} not found")
            return {'status': 'error', 'error': 'Storm not found'}
        
        # Get latest zones
        zones = Zone.get_latest_zones(storm_id)
        
        if not zones:
            logger.info(f"No zones for storm {storm.storm_id}")
            return {'status': 'no_zones'}
        
        # Get subscriptions for this storm
        subscriptions = Subscription.query.filter_by(
            storm_id=storm_id,
            is_active=True,
            mode='immediate',
            alert_on_zone_change=True
        ).all()
        
        logger.info(f"Found {len(subscriptions)} subscriptions for storm {storm.storm_id}")
        
        sent_count = 0
        for subscription in subscriptions:
            if should_send_alert(subscription, 'zone_change', zones):
                result = send_zone_change_email(subscription.user, storm, zones)
                
                if result:
                    # Log alert event
                    alert_event = AlertEvent(
                        user_id=subscription.user_id,
                        storm_id=storm_id,
                        event_type='zone_change',
                        payload={
                            'zones': [{'type': z.zone_type, 'generated_at': z.generated_at_utc.isoformat()} for z in zones]
                        },
                        sent_at_utc=datetime.utcnow(),
                        delivery_status='sent'
                    )
                    db.session.add(alert_event)
                    sent_count += 1
        
        db.session.commit()
        
        logger.info(f"Sent {sent_count} zone change alerts for {storm.storm_id}")
        
        return {
            'status': 'success',
            'storm_id': storm.storm_id,
            'alerts_sent': sent_count
        }
        
    except Exception as e:
        logger.error(f"Error sending zone change alerts: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }


@celery.task(name='tctfs_app.workers.tasks_alerts.send_digest_alerts_task')
def send_digest_alerts_task():
    """
    Send digest emails (scheduled task, e.g., every 6 hours).
    """
    logger.info("Sending digest emails")
    
    try:
        # Get digest subscriptions
        subscriptions = Subscription.query.filter_by(
            is_active=True,
            mode='digest',
            email_enabled=True
        ).all()
        
        logger.info(f"Found {len(subscriptions)} digest subscriptions")
        
        sent_count = 0
        for subscription in subscriptions:
            # Build digest for user
            digest_data = build_digest_for_subscription(subscription)
            
            if digest_data and digest_data.get('has_updates'):
                result = send_digest_email(subscription.user, digest_data)
                
                if result:
                    # Log alert event
                    alert_event = AlertEvent(
                        user_id=subscription.user_id,
                        storm_id=subscription.storm_id,
                        event_type='digest',
                        payload=digest_data,
                        sent_at_utc=datetime.utcnow(),
                        delivery_status='sent'
                    )
                    db.session.add(alert_event)
                    sent_count += 1
        
        db.session.commit()
        
        logger.info(f"Sent {sent_count} digest emails")
        
        return {
            'status': 'success',
            'digests_sent': sent_count
        }
        
    except Exception as e:
        logger.error(f"Error sending digest emails: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }


def send_advisory_email(user, storm, advisory):
    """
    Send email about new advisory.
    
    Args:
        user: User model instance
        storm: Storm model instance
        advisory: Advisory model instance
    
    Returns:
        True if sent successfully
    """
    try:
        subject = f"New Advisory: {storm.name or 'UNNAMED'} ({storm.storm_id})"
        
        template_data = {
            'user': user,
            'storm': storm,
            'advisory': advisory
        }
        
        return send_email(
            to_email=user.email,
            subject=subject,
            template='advisory_ingested.html.j2',
            template_data=template_data
        )
        
    except Exception as e:
        logger.error(f"Failed to send advisory email to {user.email}: {e}")
        return False


def send_zone_change_email(user, storm, zones):
    """
    Send email about zone changes.
    
    Args:
        user: User model instance
        storm: Storm model instance
        zones: List of Zone model instances
    
    Returns:
        True if sent successfully
    """
    try:
        # Determine if watch or warning
        has_warning = any(z.zone_type == 'warning' for z in zones)
        zone_type = 'Warning' if has_warning else 'Watch'
        
        subject = f"Cyclone {zone_type} Issued: {storm.name or 'UNNAMED'} ({storm.storm_id})"
        
        template_data = {
            'user': user,
            'storm': storm,
            'zones': zones,
            'zone_type': zone_type
        }
        
        return send_email(
            to_email=user.email,
            subject=subject,
            template='zone_change.html.j2',
            template_data=template_data
        )
        
    except Exception as e:
        logger.error(f"Failed to send zone change email to {user.email}: {e}")
        return False


def send_digest_email(user, digest_data):
    """
    Send digest email with multiple updates.
    
    Args:
        user: User model instance
        digest_data: Dictionary with digest information
    
    Returns:
        True if sent successfully
    """
    try:
        subject = "TCTFS Digest - Storm Updates"
        
        template_data = {
            'user': user,
            'digest': digest_data
        }
        
        return send_email(
            to_email=user.email,
            subject=subject,
            template='digest.html.j2',
            template_data=template_data
        )
        
    except Exception as e:
        logger.error(f"Failed to send digest email to {user.email}: {e}")
        return False


def build_digest_for_subscription(subscription):
    """
    Build digest data for a subscription.
    
    Args:
        subscription: Subscription model instance
    
    Returns:
        Dictionary with digest data
    """
    # Get updates since last digest
    cutoff_time = datetime.utcnow() - timedelta(hours=6)
    
    updates = {
        'storms': [],
        'has_updates': False
    }
    
    if subscription.storm_id:
        # Per-storm subscription
        storm = subscription.storm
        
        # Get recent advisories
        recent_advisories = Advisory.query.filter(
            Advisory.storm_id == subscription.storm_id,
            Advisory.created_at >= cutoff_time
        ).order_by(Advisory.issued_at_utc.desc()).all()
        
        if recent_advisories:
            updates['storms'].append({
                'storm': storm,
                'advisories': recent_advisories
            })
            updates['has_updates'] = True
    
    elif subscription.basin:
        # Basin-wide subscription
        storms = Storm.query.filter_by(
            basin=subscription.basin,
            status='active'
        ).all()
        
        for storm in storms:
            recent_advisories = Advisory.query.filter(
                Advisory.storm_id == storm.id,
                Advisory.created_at >= cutoff_time
            ).order_by(Advisory.issued_at_utc.desc()).all()
            
            if recent_advisories:
                updates['storms'].append({
                    'storm': storm,
                    'advisories': recent_advisories
                })
                updates['has_updates'] = True
    
    return updates
