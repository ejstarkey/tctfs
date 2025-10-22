"""
MediaThumb model - Store map thumbnails for storms.
"""
from datetime import datetime
from ..extensions import db


class MediaThumb(db.Model):
    """
    Thumbnail images of storm tracks for dashboard tiles and archive.
    """
    __tablename__ = 'media_thumbs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys
    storm_id = db.Column(db.Integer, db.ForeignKey('storms.id', ondelete='CASCADE'), nullable=False, index=True)
    advisory_id = db.Column(db.Integer, db.ForeignKey('advisories.id', ondelete='SET NULL'), nullable=True)  # Latest advisory when generated
    
    # Image storage (choose one approach)
    image_url = db.Column(db.String(512), nullable=True)  # URL if stored externally (S3, CDN)
    image_data = db.Column(db.LargeBinary, nullable=True)  # Binary data if stored in DB
    
    # Metadata
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(50), nullable=False, default='image/png')
    
    # Generation info
    derived_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    generator_version = db.Column(db.String(20), nullable=True)
    
    # Relationships
    storm = db.relationship('Storm', back_populates='media_thumbs')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MediaThumb storm_id={self.storm_id} derived_at={self.derived_at}>"
    
    def to_dict(self, include_data=False):
        """Convert media thumb to dictionary for API responses."""
        result = {
            'id': self.id,
            'storm_id': self.storm_id,
            'advisory_id': self.advisory_id,
            'image_url': self.image_url,
            'width': self.width,
            'height': self.height,
            'mime_type': self.mime_type,
            'derived_at': self.derived_at.isoformat(),
        }
        
        if include_data and self.image_data:
            import base64
            result['image_data_base64'] = base64.b64encode(self.image_data).decode('utf-8')
        
        return result
    
    @classmethod
    def get_latest_for_storm(cls, storm_id):
        """Get the most recent thumbnail for a storm."""
        return (cls.query
                .filter_by(storm_id=storm_id)
                .order_by(cls.derived_at.desc())
                .first())
    
    @classmethod
    def create_thumb(cls, storm_id, advisory_id=None, image_url=None, image_data=None, width=None, height=None):
        """Helper to create a new thumbnail."""
        return cls(
            storm_id=storm_id,
            advisory_id=advisory_id,
            image_url=image_url,
            image_data=image_data,
            width=width,
            height=height
        )
