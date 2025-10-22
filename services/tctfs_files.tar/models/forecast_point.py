"""
ForecastPoint model - AP1-AP30 mean forecast positions.
"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from ..extensions import db


class ForecastPoint(db.Model):
    """
    Represents a single forecast point in the AP1-AP30 mean track.
    The ONLY forecast displayed to users.
    """
    __tablename__ = 'forecast_points'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign key
    storm_id = db.Column(db.Integer, db.ForeignKey('storms.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Forecast metadata
    issuance_time_utc = db.Column(db.DateTime, nullable=False, index=True)  # When forecast was issued
    valid_at_utc = db.Column(db.DateTime, nullable=False, index=True)  # Valid time for this point
    lead_time_hours = db.Column(db.Integer, nullable=False)  # Hours from issuance (0, 6, 12, ...)
    
    # Position (PostGIS Point in WGS84)
    center_geom = db.Column(Geometry('POINT', srid=4326), nullable=False, index=True)
    
    # Intensity (mean across AP members)
    vmax_kt = db.Column(db.Float, nullable=True)  # Mean max sustained winds
    mslp_hpa = db.Column(db.Float, nullable=True)  # Mean MSLP (if available)
    
    # Radii (stored as JSON for quadrant-wise means)
    radii_json = db.Column(JSONB, nullable=True)  # {"NE": {"r34": 120, "r50": 60, "r64": 30}, ...}
    
    # Source tracking
    source_tag = db.Column(db.String(50), nullable=False, default='adecks_open')  # Always 'adecks_open'
    is_final = db.Column(db.Boolean, nullable=False, default=True, index=True)  # Always True for AP-mean
    
    # Member metadata
    member_count = db.Column(db.Integer, nullable=True)  # How many AP members contributed
    
    # Additional metadata
    metadata = db.Column(JSONB, nullable=True)
    
    # Relationships
    storm = db.relationship('Storm', back_populates='forecast_points')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_forecast_storm_issuance', 'storm_id', 'issuance_time_utc', 'lead_time_hours'),
        db.Index('idx_forecast_final', 'storm_id', 'is_final', 'issuance_time_utc'),
    )
    
    def __repr__(self):
        return f"<ForecastPoint storm_id={self.storm_id} lead={self.lead_time_hours}h valid={self.valid_at_utc}>"
    
    def to_dict(self):
        """Convert forecast point to dictionary for API responses."""
        from geoalchemy2.shape import to_shape
        
        # Extract lat/lon from PostGIS geometry
        point = to_shape(self.center_geom)
        
        return {
            'id': self.id,
            'storm_id': self.storm_id,
            'issuance_time_utc': self.issuance_time_utc.isoformat(),
            'valid_at_utc': self.valid_at_utc.isoformat(),
            'lead_time_hours': self.lead_time_hours,
            'latitude': point.y,
            'longitude': point.x,
            'vmax_kt': self.vmax_kt,
            'mslp_hpa': self.mslp_hpa,
            'radii': self.radii_json,
            'member_count': self.member_count,
            'source_tag': self.source_tag,
            'is_final': self.is_final,
        }
    
    @classmethod
    def get_latest_forecast(cls, storm_id):
        """Get the most recent AP-mean final forecast for a storm."""
        return (cls.query
                .filter_by(storm_id=storm_id, is_final=True)
                .order_by(cls.issuance_time_utc.desc(), cls.lead_time_hours.asc())
                .all())
    
    @classmethod
    def get_forecast_for_issuance(cls, storm_id, issuance_time):
        """Get all forecast points for a specific issuance."""
        return (cls.query
                .filter_by(storm_id=storm_id, is_final=True, issuance_time_utc=issuance_time)
                .order_by(cls.lead_time_hours.asc())
                .all())
