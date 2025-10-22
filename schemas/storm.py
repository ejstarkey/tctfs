"""
Storm schema - API serialization for Storm model.
"""
from marshmallow import Schema, fields, EXCLUDE


class StormSchema(Schema):
    """Schema for Storm model serialization."""
    
    class Meta:
        unknown = EXCLUDE
    
    id = fields.Int(dump_only=True)
    basin = fields.Str(required=True)
    name = fields.Str(allow_none=True)
    storm_id = fields.Str(required=True)
    status = fields.Str(dump_default='active')  # active, dormant, archived
    
    # Timestamps
    first_seen = fields.DateTime(dump_only=True)
    last_seen = fields.DateTime(dump_only=True)
    last_update = fields.DateTime(dump_only=True)
    
    # Latest data
    last_advisory_no = fields.Int(allow_none=True)
    last_position = fields.Dict(allow_none=True)  # {lat, lon}
    last_intensity_kt = fields.Float(allow_none=True)
    last_mslp_hpa = fields.Float(allow_none=True)
    
    # Metadata
    last_thumb_url = fields.Str(allow_none=True)
    source_url = fields.Str(allow_none=True)
    
    # Timestamps
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Computed fields
    intensity_category = fields.Method('get_intensity_category')
    time_since_update = fields.Method('get_time_since_update')
    is_active = fields.Method('get_is_active')
    
    def get_intensity_category(self, obj):
        """Get intensity category from wind speed."""
        if not obj.last_intensity_kt:
            return None
        
        vmax = obj.last_intensity_kt
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
    
    def get_time_since_update(self, obj):
        """Get time since last update in seconds."""
        if not obj.last_update:
            return None
        
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        delta = now - obj.last_update
        return int(delta.total_seconds())
    
    def get_is_active(self, obj):
        """Check if storm is currently active."""
        return obj.status == 'active'


class StormListSchema(Schema):
    """Schema for list of storms."""
    
    storms = fields.List(fields.Nested(StormSchema))
    count = fields.Int()
    filters = fields.Dict(allow_none=True)
    
    # Pagination
    page = fields.Int(dump_default=1)
    per_page = fields.Int(dump_default=20)
    total_pages = fields.Int(allow_none=True)


class StormDetailSchema(StormSchema):
    """Extended storm schema with additional details."""
    
    # Advisory count
    advisory_count = fields.Int(allow_none=True)
    
    # Latest forecast info
    has_forecast = fields.Bool(dump_default=False)
    forecast_issuance = fields.DateTime(allow_none=True)
    forecast_lead_times = fields.List(fields.Int(), allow_none=True)
    
    # Zone info
    has_zones = fields.Bool(dump_default=False)
    active_watches = fields.Int(dump_default=0)
    active_warnings = fields.Int(dump_default=0)
