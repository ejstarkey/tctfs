"""
User model - Authentication and authorization.
"""
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSONB
from ..extensions import db
import bcrypt


class User(UserMixin, db.Model):
    """
    User account with role-based access control and 2FA support.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Authentication
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile
    full_name = db.Column(db.String(100), nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    
    # Role-based access control
    role = db.Column(db.String(20), nullable=False, default='viewer', index=True)  # admin, forecaster, viewer
    
    # Two-factor authentication
    totp_secret = db.Column(db.String(32), nullable=True)  # Base32 encoded secret
    totp_enabled = db.Column(db.Boolean, nullable=False, default=False)
    
    # Session tracking
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)  # IPv6 compatible
    
    # Additional metadata
    metadata_json = db.Column(JSONB, nullable=True)
    
    # Relationships
    subscriptions = db.relationship('Subscription', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    alert_events = db.relationship('AlertEvent', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint(role.in_(['admin', 'forecaster', 'viewer']), name='check_role_valid'),
    )
    
    def __repr__(self):
        return f"<User {self.email} role={self.role}>"
    
    def set_password(self, password):
        """Hash and set user password."""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        """Verify password against stored hash."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary for API responses."""
        result = {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'created_at': self.created_at.isoformat(),
        }
        
        if include_sensitive:
            result['totp_enabled'] = self.totp_enabled
        
        return result
    
    def has_role(self, *roles):
        """Check if user has any of the specified roles."""
        return self.role in roles
    
    def is_admin(self):
        """Check if user is an admin."""
        return self.role == 'admin'
    
    def update_last_login(self, ip_address=None):
        """Update last login timestamp and IP."""
        self.last_login_at = datetime.utcnow()
        if ip_address:
            self.last_login_ip = ip_address
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def create_user(cls, email, password, role='viewer', full_name=None):
        """Helper to create a new user with hashed password."""
        user = cls(
            email=email,
            role=role,
            full_name=full_name,
            is_active=True,
            is_verified=False
        )
        user.set_password(password)
        return user
