"""
AuditLog model - Track admin and system actions for security.
"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from ..extensions import db


class AuditLog(db.Model):
    """
    Audit trail for important system and admin actions.
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Actor (NULL for system actions)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    actor_email = db.Column(db.String(255), nullable=True)  # Denormalized for deleted users
    actor_ip = db.Column(db.String(45), nullable=True)
    
    # Action details
    action = db.Column(db.String(100), nullable=False, index=True)  # e.g., 'user.created', 'storm.reingested', 'zone.regenerated'
    entity_type = db.Column(db.String(50), nullable=True, index=True)  # user, storm, advisory, zone, etc.
    entity_id = db.Column(db.Integer, nullable=True, index=True)
    
    # Additional context
    details = db.Column(JSONB, nullable=True)  # Store any relevant data
    
    # Result
    success = db.Column(db.Boolean, nullable=False, default=True)
    error_message = db.Column(db.Text, nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_audit_action_time', 'action', 'created_at'),
        db.Index('idx_audit_entity', 'entity_type', 'entity_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog action={self.action} actor={self.actor_email} time={self.created_at}>"
    
    def to_dict(self):
        """Convert audit log to dictionary."""
        return {
            'id': self.id,
            'actor_user_id': self.actor_user_id,
            'actor_email': self.actor_email,
            'actor_ip': self.actor_ip,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'success': self.success,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
        }
    
    @classmethod
    def log_action(cls, action, actor_user=None, actor_ip=None, entity_type=None, entity_id=None, details=None, success=True, error_message=None):
        """Helper to create an audit log entry."""
        log = cls(
            actor_user_id=actor_user.id if actor_user else None,
            actor_email=actor_user.email if actor_user else 'system',
            actor_ip=actor_ip,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            success=success,
            error_message=error_message
        )
        db.session.add(log)
        return log
    
    @classmethod
    def get_recent_logs(cls, limit=100, action=None, entity_type=None):
        """Get recent audit logs with optional filters."""
        query = cls.query
        
        if action:
            query = query.filter_by(action=action)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        
        return query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_logs_for_entity(cls, entity_type, entity_id):
        """Get all logs for a specific entity."""
        return (cls.query
                .filter_by(entity_type=entity_type, entity_id=entity_id)
                .order_by(cls.created_at.desc())
                .all())
