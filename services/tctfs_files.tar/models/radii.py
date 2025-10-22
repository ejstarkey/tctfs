"""
Radii model - Wind radii by quadrant for each advisory.
"""
from datetime import datetime
from ..extensions import db


class Radii(db.Model):
    """
    Wind radii (34/50/64 kt) by quadrant (NE/SE/SW/NW) for an advisory.
    """
    __tablename__ = 'radii'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign key
    advisory_id = db.Column(db.Integer, db.ForeignKey('advisories.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Quadrant (NE, SE, SW, NW)
    quadrant = db.Column(db.String(2), nullable=False)
    
    # Radii in nautical miles (nm)
    r34_nm = db.Column(db.Float, nullable=True)  # 34-knot wind radius
    r50_nm = db.Column(db.Float, nullable=True)  # 50-knot wind radius
    r64_nm = db.Column(db.Float, nullable=True)  # 64-knot wind radius (hurricane force)
    
    # Relationships
    advisory = db.relationship('Advisory', back_populates='radii')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint(quadrant.in_(['NE', 'SE', 'SW', 'NW']), name='check_quadrant_valid'),
        db.UniqueConstraint('advisory_id', 'quadrant', name='uq_advisory_quadrant'),
    )
    
    def __repr__(self):
        return f"<Radii advisory_id={self.advisory_id} quadrant={self.quadrant}>"
    
    def to_dict(self):
        """Convert radii to dictionary for API responses."""
        return {
            'quadrant': self.quadrant,
            'r34_nm': self.r34_nm,
            'r50_nm': self.r50_nm,
            'r64_nm': self.r64_nm,
        }
    
    @classmethod
    def create_for_advisory(cls, advisory_id, quadrant, r34=None, r50=None, r64=None):
        """Helper to create radii record for an advisory."""
        radii = cls(
            advisory_id=advisory_id,
            quadrant=quadrant,
            r34_nm=r34,
            r50_nm=r50,
            r64_nm=r64
        )
        return radii
