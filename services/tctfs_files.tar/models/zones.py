"""
Zone model - Cyclone Watch/Warning polygons.
"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from ..extensions import db


class Zone(db.Model):
    """
    Represents a Cyclone Watch or Warning zone polygon.
    Generated algorithmically from AP-mean forecast.
    """
    __tablename__ = 'zones'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign key
    storm_id = db.Column(db.Integer, db.ForeignKey('storms.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Zone metadata
    zone_type = db.Column(db.String(20), nullable=False, index=True)  # 'watch' or 'warning'
    generated_at_utc = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Validity period
    valid_from_utc = db.Column(db.DateTime, nullable=False, index=True)
    valid_to_utc = db.Column(db.DateTime, nullable=False, index=True)
    
    # Geometry (PostGIS MultiPolygon in WGS84)
    geom = db.Column(Geometry('MULTIPOLYGON', srid=4326), nullable=False, index=True)
    
    # Method tracking (for algorithm versioning)
    method_version = db.Column(db.String(20), nullable=True)
    
    # Additional parameters used in generation
    parameters = db.Column(JSONB, nullable=True)  # Store coefficients, thresholds, etc.
    
    # Relationships
    storm = db.relationship('Storm', back_populates='zones')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint(zone_type.in_(['watch', 'warning']), name='check_zone_type_valid'),
        db.Index('idx_zone_storm_type_valid', 'storm_id', 'zone_type', 'valid_from_utc'),
    )
    
    def __repr__(self):
        return f"<Zone storm_id={self.storm_id} type={self.zone_type} valid={self.valid_from_utc}>"
    
    def to_dict(self, include_geometry=True):
        """Convert zone to dictionary for API responses."""
        result = {
            'id': self.id,
            'storm_id': self.storm_id,
            'zone_type': self.zone_type,
            'generated_at_utc': self.generated_at_utc.isoformat(),
            'valid_from_utc': self.valid_from_utc.isoformat(),
            'valid_to_utc': self.valid_to_utc.isoformat(),
            'method_version': self.method_version,
        }
        
        if include_geometry:
            from geoalchemy2.shape import to_shape
            from shapely import geometry
            import json
            
            # Convert PostGIS geometry to GeoJSON
            shape = to_shape(self.geom)
            result['geometry'] = json.loads(geometry.mapping(shape).__str__())
        
        return result
    
    def to_geojson_feature(self):
        """Convert zone to GeoJSON Feature for mapping."""
        from geoalchemy2.shape import to_shape
        from shapely import geometry
        
        shape = to_shape(self.geom)
        
        return {
            'type': 'Feature',
            'id': self.id,
            'geometry': geometry.mapping(shape),
            'properties': {
                'storm_id': self.storm_id,
                'zone_type': self.zone_type,
                'valid_from_utc': self.valid_from_utc.isoformat(),
                'valid_to_utc': self.valid_to_utc.isoformat(),
                'generated_at_utc': self.generated_at_utc.isoformat(),
            }
        }
    
    @classmethod
    def get_active_zones(cls, storm_id, at_time=None):
        """Get active zones for a storm at a specific time."""
        if at_time is None:
            at_time = datetime.utcnow()
        
        return (cls.query
                .filter_by(storm_id=storm_id)
                .filter(cls.valid_from_utc <= at_time)
                .filter(cls.valid_to_utc >= at_time)
                .all())
    
    @classmethod
    def get_latest_zones(cls, storm_id):
        """Get the most recently generated zones for a storm."""
        return (cls.query
                .filter_by(storm_id=storm_id)
                .order_by(cls.generated_at_utc.desc())
                .limit(2)  # Get both watch and warning
                .all())
