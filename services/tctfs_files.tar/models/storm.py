"""
Storm model - Core entity tracking tropical cyclone systems.
"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from ..extensions import db


class Storm(db.Model):
    """
    Represents a tropical cyclone system tracked by TCTFS.
    """
    __tablename__ = 'storms'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Identification
    basin = db.Column(db.String(10), nullable=False, index=True)  # WP, SH, EP, IO, etc.
    name = db.Column(db.String(50), nullable=True)  # May be unnamed initially
    storm_id = db.Column(db.String(20), nullable=False, unique=True, index=True)  # e.g., "28W", "03SH"
    
    # Status tracking
    status = db.Column(
        db.String(20),
        nullable=False,
        default='active',
        index=True
    )  # active, dormant, archived
    
    # Temporal tracking
    first_seen = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Latest advisory metadata
    last_advisory_no = db.Column(db.Integer, nullable=True)
    last_thumb_url = db.Column(db.String(512), nullable=True)
    
    # Source tracking
    history_file_url = db.Column(db.String(512), nullable=True)  # *-list.txt URL
    raw_metadata = db.Column(JSONB, nullable=True)  # Store any extra metadata
    
    # Relationships
    advisories = db.relationship('Advisory', back_populates='storm', lazy='dynamic', cascade='all, delete-orphan')
    forecast_points = db.relationship('ForecastPoint', back_populates='storm', lazy='dynamic', cascade='all, delete-orphan')
    zones = db.relationship('Zone', back_populates='storm', lazy='dynamic', cascade='all, delete-orphan')
    media_thumbs = db.relationship('MediaThumb', back_populates='storm', lazy='dynamic', cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', back_populates='storm', lazy='dynamic', cascade='all, delete-orphan')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Storm {self.storm_id} '{self.name}' status={self.status}>"
    
    def to_dict(self):
        """Convert storm to dictionary for API responses."""
        return {
            'id': self.id,
            'basin': self.basin,
            'name': self.name,
            'storm_id': self.storm_id,
            'status': self.status,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'last_advisory_no': self.last_advisory_no,
            'last_thumb_url': self.last_thumb_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def get_active_storms(cls):
        """Get all active storms."""
        return cls.query.filter_by(status='active').order_by(cls.last_seen.desc()).all()
    
    @classmethod
    def get_by_storm_id(cls, storm_id):
        """Get storm by its identifier."""
        return cls.query.filter_by(storm_id=storm_id).first()
    
    def mark_dormant(self):
        """Mark storm as dormant (no recent updates)."""
        self.status = 'dormant'
        self.updated_at = datetime.utcnow()
    
    def mark_archived(self):
        """Mark storm as archived (system has ended)."""
        self.status = 'archived'
        self.updated_at = datetime.utcnow()
    
    def update_last_seen(self):
        """Update last seen timestamp."""
        self.last_seen = datetime.utcnow()
        self.updated_at = datetime.utcnow()
