from datetime import datetime
from ..extensions import db

class Storm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    basin = db.Column(db.String(10))
    advisory_time = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    intensity = db.Column(db.String(20))

    def __repr__(self):
        return f"<Storm {self.name} {self.intensity}>"

