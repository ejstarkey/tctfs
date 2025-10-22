"""
Alert Rules Service - Determine when to send alerts and apply suppressions.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AlertRulesService:
    """
    Business logic for determining when and how to send alerts.
    """
    
    # Minimum time between alerts for same event type (hours)
    ALERT_COOLDOWN = {
        'new_advisory': 6,      # Max 1 advisory alert per 6 hours
        'zone_change': 12,       # Max 1 zone change alert per 12 hours
        'intensity_change': 6,   # Max 1 intensity alert per 6 hours
    }
    
    def should_send_advisory_alert(
        self,
        subscription: Dict,
        advisory: Dict,
        last_alert_time: Optional[datetime] = None
    ) -> bool:
        """
        Determine if advisory alert should be sent.
        
        Args:
            subscription: User subscription dict
            advisory: Advisory data dict
            last_alert_time: Time of last alert sent for this event type
        
        Returns:
            True if alert should be sent
        """
        # Check if user wants advisory alerts
        if not subscription.get('alert_on_new_advisory', True):
            return False
        
        # Check intensity threshold if set
        min_intensity = subscription.get('min_intensity_kt')
        if min_intensity:
            vmax = advisory.get('vmax_kt', 0)
            if vmax < min_intensity:
                logger.debug(f"Advisory intensity {vmax}kt below threshold {min_intensity}kt")
                return False
        
        # Check cooldown period
        if last_alert_time:
            cooldown_hours = self.ALERT_COOLDOWN['new_advisory']
            time_since = (datetime.utcnow() - last_alert_time).total_seconds() / 3600
            
            if time_since < cooldown_hours:
                logger.debug(f"Advisory alert in cooldown ({time_since:.1f}h < {cooldown_hours}h)")
                return False
        
        return True
    
    def should_send_zone_alert(
        self,
        subscription: Dict,
        zone: Dict,
        previous_zone: Optional[Dict] = None,
        last_alert_time: Optional[datetime] = None
    ) -> bool:
        """
        Determine if zone change alert should be sent.
        
        Args:
            subscription: User subscription dict
            zone: New/updated zone data
            previous_zone: Previous zone data (if any)
            last_alert_time: Time of last zone alert
        
        Returns:
            True if alert should be sent
        """
        # Check if user wants zone alerts
        if not subscription.get('alert_on_zone_change', True):
            return False
        
        # Check if this is a new zone or significant change
        if previous_zone is None:
            # New zone issued
            logger.info("New zone issued, sending alert")
            return True
        
        # Check if zone type upgraded (watch -> warning)
        if previous_zone.get('zone_type') == 'watch' and zone.get('zone_type') == 'warning':
            logger.info("Zone upgraded from watch to warning")
            return True
        
        # Check cooldown for non-urgent changes
        if last_alert_time:
            cooldown_hours = self.ALERT_COOLDOWN['zone_change']
            time_since = (datetime.utcnow() - last_alert_time).total_seconds() / 3600
            
            if time_since < cooldown_hours:
                logger.debug(f"Zone alert in cooldown ({time_since:.1f}h < {cooldown_hours}h)")
                return False
        
        return True
    
    def should_send_intensity_alert(
        self,
        subscription: Dict,
        current_intensity_kt: float,
        previous_intensity_kt: float,
        threshold_change_kt: float = 15,
        last_alert_time: Optional[datetime] = None
    ) -> bool:
        """
        Determine if intensity change alert should be sent.
        
        Args:
            subscription: User subscription dict
            current_intensity_kt: Current max winds
            previous_intensity_kt: Previous max winds
            threshold_change_kt: Minimum change to trigger alert
            last_alert_time: Time of last intensity alert
        
        Returns:
            True if alert should be sent
        """
        # Check if user wants intensity alerts
        if not subscription.get('alert_on_intensity_change', False):
            return False
        
        # Check if change is significant
        intensity_change = abs(current_intensity_kt - previous_intensity_kt)
        if intensity_change < threshold_change_kt:
            logger.debug(f"Intensity change {intensity_change}kt below threshold {threshold_change_kt}kt")
            return False
        
        # Check minimum intensity threshold
        min_intensity = subscription.get('min_intensity_kt')
        if min_intensity and current_intensity_kt < min_intensity:
            return False
        
        # Check cooldown
        if last_alert_time:
            cooldown_hours = self.ALERT_COOLDOWN['intensity_change']
            time_since = (datetime.utcnow() - last_alert_time).total_seconds() / 3600
            
            if time_since < cooldown_hours:
                logger.debug(f"Intensity alert in cooldown ({time_since:.1f}h < {cooldown_hours}h)")
                return False
        
        return True
    
    def should_send_digest(
        self,
        subscription: Dict,
        last_digest_time: Optional[datetime] = None
    ) -> bool:
        """
        Determine if digest should be sent.
        
        Args:
            subscription: User subscription dict
            last_digest_time: Time of last digest sent
        
        Returns:
            True if digest should be sent
        """
        # Only for users with digest mode
        if subscription.get('mode') != 'digest':
            return False
        
        # Default digest frequency: every 6 hours
        digest_interval_hours = 6
        
        if last_digest_time is None:
            # Never sent digest, send now
            return True
        
        time_since = (datetime.utcnow() - last_digest_time).total_seconds() / 3600
        
        return time_since >= digest_interval_hours
    
    def get_digest_storms(
        self,
        user_subscriptions: List[Dict],
        since: datetime
    ) -> List[Dict]:
        """
        Get storms with updates for digest email.
        
        Args:
            user_subscriptions: List of user's active subscriptions
            since: Get updates since this time
        
        Returns:
            List of storm data dictionaries with updates
        """
        # This would query the database for storms with updates
        # Placeholder implementation
        return []
    
    def apply_suppressions(
        self,
        subscription: Dict,
        alert_type: str
    ) -> bool:
        """
        Check if alert should be suppressed due to user preferences.
        
        Args:
            subscription: User subscription
            alert_type: Type of alert
        
        Returns:
            True if alert should be suppressed (not sent)
        """
        # Check if subscription is active
        if not subscription.get('is_active', True):
            return True
        
        # Check if email is enabled
        if not subscription.get('email_enabled', True):
            return True
        
        # Digest mode users don't get immediate alerts
        if subscription.get('mode') == 'digest' and alert_type != 'digest':
            return True
        
        return False


# Singleton instance
_alert_rules_service = None

def get_alert_rules_service() -> AlertRulesService:
    """Get or create the singleton alert rules service."""
    global _alert_rules_service
    if _alert_rules_service is None:
        _alert_rules_service = AlertRulesService()
    return _alert_rules_service
