"""
AlertEvent model - Track sent alerts/notifications.
"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from ..extensions import db


class AlertEvent(db.Model):
    """
    Records alerts sent to users for audit and debugging.
    """
    __tablename__ = 'alert_events'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    storm_id = db.Column(db.Integer, db.ForeignKey('storms.id', ondelete='CASCADE'), nullable=True, index=True)
    
    # Event metadata
    event_type = db.Column(db.String(50), nullable=False, index=True)  # new_advisory, zone_change, intensity_change, digest
    
    # Delivery details
    delivery_channel = db.Column(db.String(20), nullable=False, default='email')  # email, sms (future), push (future)
    delivery_status = db.Column(db.String(20), nullable=False, default='pending', index=True)  # pending, sent, failed, bounced
    delivery_error = db.Column(db.Text, nullable=True)
    
    # Content
    subject = db.Column(db.String(255), nullable=True)
    payload = db.Column(JSONB, nullable=True)  # Store alert details for debugging
    
    # Timestamps
    sent_at_utc = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='alert_events')
    storm = db.relationship('Storm')
    
    # Indexes
    __table_args__ = (
        db.Index('idx_alert_user_time', 'user_id', 'created_at'),
        db.Index('idx_alert_storm_type', 'storm_id', 'event_type', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AlertEvent user_id={self.user_id} type={self.event_type} status={self.delivery_status}>"
    
    def to_dict(self):
        """Convert alert event to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'storm_id': self.storm_id,
            'event_type': self.event_type,
            'delivery_channel': self.delivery_channel,
            'delivery_status': self.delivery_status,
            'subject': self.subject,
            'sent_at_utc': self.sent_at_utc.isoformat() if self.sent_at_utc else None,
            'created_at': self.created_at.isoformat(),
        }
    
    def mark_sent(self):
        """Mark alert as successfully sent."""
        self.delivery_status = 'sent'
        self.sent_at_utc = datetime.utcnow()
    
    def mark_failed(self, error_message):
        """Mark alert as failed with error message."""
        self.delivery_status = 'failed'
        self.delivery_error = error_message
        self.sent_at_utc = datetime.utcnow()
    
    @classmethod
    def create_event(cls, user_id, event_type, storm_id=None, subject=None, payload=None):
        """Helper to create a new alert event."""
        return cls(
            user_id=user_id,
            storm_id=storm_id,
            event_type=event_type,
            subject=subject,
            payload=payload,
            delivery_status='pending'
        )
    
    @classmethod
    def get_recent_for_user(cls, user_id, limit=50):
        """Get recent alerts for a user."""
        return (cls.query
                .filter_by(user_id=user_id)
                .order_by(cls.created_at.desc())
                .limit(limit)
                .all())
    
    @classmethod
    def get_failed_alerts(cls, since=None):
        """Get failed alerts for retry."""
        query = cls.query.filter_by(delivery_status='failed')
        if since:
            query = query.filter(cls.created_at >= since)
        return query.all()
