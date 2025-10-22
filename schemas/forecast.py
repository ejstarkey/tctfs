"""
Forecast schema - API serialization for Forecast model (AP1-AP30 mean).
"""
from marshmallow import Schema, fields, EXCLUDE


class ForecastRadiiSchema(Schema):
    """Schema for forecast wind radii."""
    
    NE = fields.Dict(allow_none=True)  # {r34, r50, r64}
    SE = fields.Dict(allow_none=True)
    SW = fields.Dict(allow_none=True)
    NW = fields.Dict(allow_none=True)


class ForecastPointSchema(Schema):
    """Schema for a single forecast point (one lead time)."""
    
    class Meta:
        unknown = EXCLUDE
    
    id = fields.Int(dump_only=True)
    storm_id = fields.Int(required=True)
    
    # Timing
    issuance_time = fields.DateTime(required=True)
    valid_at = fields.DateTime(required=True)
    lead_time_hours = fields.Int(required=True)
    
    # Position
    latitude = fields.Float(required=True)
    longitude = fields.Float(required=True)
    
    # Intensity
    vmax_kt = fields.Float(allow_none=True)
    mslp_hpa = fields.Float(allow_none=True)
    
    # Wind radii
    radii = fields.Nested(ForecastRadiiSchema, allow_none=True)
    
    # Metadata
    member_count = fields.Int(allow_none=True)
    source_tag = fields.Str(dump_default='adecks_open')
    is_final = fields.Bool(dump_default=True)
    
    # Timestamps
    created_at = fields.DateTime(dump_only=True)
    
    # Computed fields
    intensity_category = fields.Method('get_intensity_category')
    
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


class ForecastSchema(Schema):
    """Schema for complete forecast (all lead times)."""
    
    storm_id = fields.Int(required=True)
    issuance_time = fields.DateTime(required=True)
    forecast_points = fields.List(fields.Nested(ForecastPointSchema))
    
    # Metadata
    lead_times = fields.List(fields.Int())
    max_lead_time_hours = fields.Int()
    member_count = fields.Int()
    source = fields.Str(dump_default='adecks_open')
    is_final = fields.Bool(dump_default=True)
    
    # Track as GeoJSON
    track_geojson = fields.Dict(allow_none=True)


class ForecastGeoJSONSchema(Schema):
    """Schema for forecast as GeoJSON FeatureCollection."""
    
    type = fields.Str(dump_default='FeatureCollection')
    features = fields.List(fields.Dict())
    
    metadata = fields.Dict()
    
    # Forecast info
    storm_id = fields.Int()
    issuance_time = fields.DateTime()
    forecast_type = fields.Str(dump_default='AP_MEAN')
    opacity = fields.Float(dump_default=0.5)  # Future path at 50% opacity


class ForecastConeSchema(Schema):
    """Schema for forecast uncertainty cone."""
    
    storm_id = fields.Int()
    issuance_time = fields.DateTime()
    
    # Cone geometry
    cone_geometry = fields.Dict()  # GeoJSON polygon
    
    # Cone parameters
    initial_radius_nm = fields.Float()
    growth_rate_nm_per_hour = fields.Float()
    max_lead_time_hours = fields.Int()
