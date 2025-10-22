"""
Subscription model - User subscriptions to storms/basins for alerts.
"""
from datetime import datetime
from ..extensions import db


class Subscription(db.Model):
    """
    User subscription to receive alerts for specific storms or basins.
    """
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    storm_id = db.Column(db.Integer, db.ForeignKey('storms.id', ondelete='CASCADE'), nullable=True, index=True)  # NULL = basin-wide
    
    # Subscription scope
    basin = db.Column(db.String(10), nullable=True, index=True)  # For basin-wide subscriptions
    
    # Delivery preferences
    mode = db.Column(db.String(20), nullable=False, default='immediate')  # immediate, digest
    email_enabled = db.Column(db.Boolean, nullable=False, default=True)
    
    # Filter preferences (what triggers alerts)
    alert_on_new_advisory = db.Column(db.Boolean, nullable=False, default=True)
    alert_on_zone_change = db.Column(db.Boolean, nullable=False, default=True)
    alert_on_intensity_change = db.Column(db.Boolean, nullable=False, default=False)
    
    # Intensity threshold (only alert if storm exceeds this)
    min_intensity_kt = db.Column(db.Float, nullable=True)  # e.g., only alert for hurricanes (64+ kt)
    
    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    
    # Relationships
    user = db.relationship('User', back_populates='subscriptions')
    storm = db.relationship('Storm', back_populates='subscriptions')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint(mode.in_(['immediate', 'digest']), name='check_mode_valid'),
        db.CheckConstraint(
            '(storm_id IS NOT NULL AND basin IS NULL) OR (storm_id IS NULL AND basin IS NOT NULL)',
            name='check_subscription_scope'
        ),
        db.UniqueConstraint('user_id', 'storm_id', name='uq_user_storm'),
        db.UniqueConstraint('user_id', 'basin', name='uq_user_basin'),
    )
    
    def __repr__(self):
        scope = f"storm={self.storm_id}" if self.storm_id else f"basin={self.basin}"
        return f"<Subscription user_id={self.user_id} {scope} mode={self.mode}>"
    
    def to_dict(self):
        """Convert subscription to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'storm_id': self.storm_id,
            'basin': self.basin,
            'mode': self.mode,
            'email_enabled': self.email_enabled,
            'alert_on_new_advisory': self.alert_on_new_advisory,
            'alert_on_zone_change': self.alert_on_zone_change,
            'alert_on_intensity_change': self.alert_on_intensity_change,
            'min_intensity_kt': self.min_intensity_kt,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
        }
    
    @classmethod
    def get_for_user(cls, user_id, active_only=True):
        """Get all subscriptions for a user."""
        query = cls.query.filter_by(user_id=user_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()
    
    @classmethod
    def get_for_storm(cls, storm_id, active_only=True):
        """Get all subscriptions for a specific storm."""
        query = cls.query.filter_by(storm_id=storm_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()
    
    @classmethod
    def get_for_basin(cls, basin, active_only=True):
        """Get all subscriptions for a basin."""
        query = cls.query.filter_by(basin=basin)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()
    
    def should_alert_for_intensity(self, current_intensity_kt):
        """Check if current intensity meets threshold."""
        if self.min_intensity_kt is None:
            return True
        return current_intensity_kt >= self.min_intensity_kt
