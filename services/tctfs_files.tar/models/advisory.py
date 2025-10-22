"""
Advisory model - Historical observations and advisories for storms.
"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from ..extensions import db


class Advisory(db.Model):
    """
    Represents a single advisory/observation for a tropical cyclone.
    Parsed from *-list.txt history files.
    """
    __tablename__ = 'advisories'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign key
    storm_id = db.Column(db.Integer, db.ForeignKey('storms.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Advisory metadata
    advisory_no = db.Column(db.Integer, nullable=True)  # May not always be present
    issued_at_utc = db.Column(db.DateTime, nullable=False, index=True)
    
    # Position (PostGIS Point in WGS84)
    center_geom = db.Column(Geometry('POINT', srid=4326), nullable=False, index=True)
    
    # Intensity
    vmax_kt = db.Column(db.Float, nullable=True)  # Maximum sustained winds in knots
    mslp_hpa = db.Column(db.Float, nullable=True)  # Minimum sea level pressure in hPa
    
    # Motion
    motion_bearing_deg = db.Column(db.Float, nullable=True)  # 0-360 degrees
    motion_speed_kt = db.Column(db.Float, nullable=True)  # Speed in knots
    
    # Source tracking
    source_url = db.Column(db.String(512), nullable=True)
    parse_version = db.Column(db.String(20), nullable=True)  # Parser version for reprocessing
    raw_blob = db.Column(db.Text, nullable=True)  # Original line/block for reprocessing
    
    # Additional data (flexible storage)
    metadata = db.Column(JSONB, nullable=True)
    
    # Relationships
    storm = db.relationship('Storm', back_populates='advisories')
    radii = db.relationship('Radii', back_populates='advisory', lazy='joined', cascade='all, delete-orphan')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_advisory_storm_time', 'storm_id', 'issued_at_utc'),
    )
    
    def __repr__(self):
        return f"<Advisory storm_id={self.storm_id} no={self.advisory_no} time={self.issued_at_utc}>"
    
    def to_dict(self, include_radii=False):
        """Convert advisory to dictionary for API responses."""
        from geoalchemy2.shape import to_shape
        
        # Extract lat/lon from PostGIS geometry
        point = to_shape(self.center_geom)
        
        result = {
            'id': self.id,
            'storm_id': self.storm_id,
            'advisory_no': self.advisory_no,
            'issued_at_utc': self.issued_at_utc.isoformat(),
            'latitude': point.y,
            'longitude': point.x,
            'vmax_kt': self.vmax_kt,
            'mslp_hpa': self.mslp_hpa,
            'motion_bearing_deg': self.motion_bearing_deg,
            'motion_speed_kt': self.motion_speed_kt,
            'created_at': self.created_at.isoformat(),
        }
        
        if include_radii and self.radii:
            result['radii'] = [r.to_dict() for r in self.radii]
        
        return result
    
    @classmethod
    def get_latest_for_storm(cls, storm_id):
        """Get the most recent advisory for a storm."""
        return cls.query.filter_by(storm_id=storm_id).order_by(cls.issued_at_utc.desc()).first()
    
    @classmethod
    def get_track_for_storm(cls, storm_id, from_time=None, to_time=None):
        """Get advisories for a storm within a time range."""
        query = cls.query.filter_by(storm_id=storm_id)
        
        if from_time:
            query = query.filter(cls.issued_at_utc >= from_time)
        if to_time:
            query = query.filter(cls.issued_at_utc <= to_time)
        
        return query.order_by(cls.issued_at_utc.asc()).all()
