"""
Emailer Service - Send email alerts to users.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from flask import current_app
from flask_mail import Mail, Message
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

logger = logging.getLogger(__name__)


class EmailerService:
    """
    Send email notifications to users for storm alerts.
    """
    
    def __init__(self, mail: Mail = None, template_dir: Optional[str] = None):
        """
        Initialize emailer service.
        
        Args:
            mail: Flask-Mail instance
            template_dir: Path to email templates directory
        """
        self.mail = mail
        
        # Setup Jinja2 for email templates
        if template_dir is None:
            template_dir = os.path.join(
                os.path.dirname(__file__),
                'templates'
            )
        
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml', 'j2'])
        )
    
    def send_advisory_alert(
        self,
        user_email: str,
        storm_name: str,
        storm_id: str,
        advisory_data: Dict
    ) -> bool:
        """
        Send new advisory notification.
        
        Args:
            user_email: Recipient email address
            storm_name: Storm name
            storm_id: Storm identifier
            advisory_data: Advisory details dictionary
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            template = self.jinja_env.get_template('advisory_ingested.html.j2')
            
            html_body = template.render(
                storm_name=storm_name,
                storm_id=storm_id,
                advisory=advisory_data,
                current_year=datetime.utcnow().year
            )
            
            subject = f"New Advisory: {storm_name} ({storm_id})"
            
            return self._send_email(user_email, subject, html_body)
            
        except Exception as e:
            logger.error(f"Failed to send advisory alert to {user_email}: {e}")
            return False
    
    def send_zone_change_alert(
        self,
        user_email: str,
        storm_name: str,
        storm_id: str,
        zone_type: str,
        zone_details: Dict
    ) -> bool:
        """
        Send zone change notification (watch/warning issued or changed).
        
        Args:
            user_email: Recipient email
            storm_name: Storm name
            storm_id: Storm ID
            zone_type: 'watch' or 'warning'
            zone_details: Zone information
        
        Returns:
            True if sent successfully
        """
        try:
            template = self.jinja_env.get_template('zone_change.html.j2')
            
            html_body = template.render(
                storm_name=storm_name,
                storm_id=storm_id,
                zone_type=zone_type,
                zone=zone_details,
                current_year=datetime.utcnow().year
            )
            
            subject = f"{zone_type.capitalize()} Issued: {storm_name} ({storm_id})"
            
            return self._send_email(user_email, subject, html_body)
            
        except Exception as e:
            logger.error(f"Failed to send zone change alert to {user_email}: {e}")
            return False
    
    def send_digest(
        self,
        user_email: str,
        storms: List[Dict],
        time_period: str = "24 hours"
    ) -> bool:
        """
        Send digest email with multiple storm updates.
        
        Args:
            user_email: Recipient email
            storms: List of storm update dictionaries
            time_period: Time period covered by digest
        
        Returns:
            True if sent successfully
        """
        try:
            template = self.jinja_env.get_template('digest.html.j2')
            
            html_body = template.render(
                storms=storms,
                time_period=time_period,
                current_year=datetime.utcnow().year
            )
            
            subject = f"TCTFS Digest: {len(storms)} Storm Updates"
            
            return self._send_email(user_email, subject, html_body)
            
        except Exception as e:
            logger.error(f"Failed to send digest to {user_email}: {e}")
            return False
    
    def _send_email(self, to: str, subject: str, html_body: str) -> bool:
        """
        Send an email using Flask-Mail.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
        
        Returns:
            True if sent successfully
        """
        try:
            if self.mail is None:
                logger.error("Mail instance not configured")
                return False
            
            msg = Message(
                subject=subject,
                recipients=[to],
                html=html_body,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            
            self.mail.send(msg)
            logger.info(f"Email sent to {to}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False


# Singleton instance
_emailer_service = None

def get_emailer_service(mail: Mail = None) -> EmailerService:
    """Get or create the singleton emailer service."""
    global _emailer_service
    if _emailer_service is None:
        _emailer_service = EmailerService(mail=mail)
    return _emailer_service
