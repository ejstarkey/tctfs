"""
Advisory schema - API serialization for Advisory model.
"""
from marshmallow import Schema, fields, EXCLUDE


class RadiiSchema(Schema):
    """Schema for wind radii by quadrant."""
    
    quadrant = fields.Str(required=True)  # NE, SE, SW, NW
    r34_nm = fields.Float(allow_none=True)
    r50_nm = fields.Float(allow_none=True)
    r64_nm = fields.Float(allow_none=True)


class AdvisorySchema(Schema):
    """Schema for Advisory model serialization."""
    
    class Meta:
        unknown = EXCLUDE
    
    id = fields.Int(dump_only=True)
    storm_id = fields.Int(required=True)
    advisory_no = fields.Int(allow_none=True)
    issued_at_utc = fields.DateTime(required=True)
    
    # Position
    latitude = fields.Float(required=True)
    longitude = fields.Float(required=True)
    
    # Intensity
    vmax_kt = fields.Float(allow_none=True)
    mslp_hpa = fields.Float(allow_none=True)
    
    # Motion
    motion_bearing_deg = fields.Float(allow_none=True)
    motion_speed_kt = fields.Float(allow_none=True)
    
    # Wind radii
    radii = fields.List(fields.Nested(RadiiSchema), allow_none=True)
    
    # Source
    source_url = fields.Str(allow_none=True)
    parse_version = fields.Str(allow_none=True)
    
    # Timestamps
    created_at = fields.DateTime(dump_only=True)
    
    # Computed fields
    intensity_category = fields.Method('get_intensity_category')
    motion_direction = fields.Method('get_motion_direction')
    
    def get_intensity_category(self, obj):
        """Get intensity category from wind speed."""
        if not obj.vmax_kt:
            return None
        
        vmax = obj.vmax_kt
        if vmax < 34:
            return 'TD'
        elif vmax < 64:
            return 'TS'
        elif vmax < 83:
            return 'CAT1'
        elif vmax < 96:
            return 'CAT2'
        elif vmax < 113:
            return 'CAT3'
        elif vmax < 137:
            return 'CAT4'
        else:
            return 'CAT5'
    
    def get_motion_direction(self, obj):
        """Convert bearing to cardinal direction."""
        if obj.motion_bearing_deg is None:
            return None
        
        bearing = obj.motion_bearing_deg
        
        directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                     'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        
        index = round(bearing / 22.5) % 16
        return directions[index]


class AdvisoryListSchema(Schema):
    """Schema for list of advisories."""
    
    advisories = fields.List(fields.Nested(AdvisorySchema))
    count = fields.Int()
    storm_id = fields.Int()


class AdvisoryTrackSchema(Schema):
    """Schema for track (series of advisories as GeoJSON)."""
    
    type = fields.Str(dump_default='FeatureCollection')
    features = fields.List(fields.Dict())
    metadata = fields.Dict()
    
    # Track statistics
    start_time = fields.DateTime(allow_none=True)
    end_time = fields.DateTime(allow_none=True)
    max_intensity_kt = fields.Float(allow_none=True)
    min_pressure_hpa = fields.Float(allow_none=True)
    track_length_nm = fields.Float(allow_none=True)
