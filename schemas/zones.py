"""
Zones schema - API serialization for Zone model.
"""
from marshmallow import Schema, fields


class ZoneSchema(Schema):
    """Schema for Zone model serialization."""
    
    id = fields.Int(dump_only=True)
    storm_id = fields.Int(required=True)
    generated_at_utc = fields.DateTime(required=True)
    zone_type = fields.Str(required=True)  # watch or warning
    valid_from_utc = fields.DateTime(required=True)
    valid_to_utc = fields.DateTime(required=True)
    geometry = fields.Dict(dump_only=True)  # GeoJSON geometry
    method_version = fields.Str(allow_none=True)
    metadata_json = fields.Dict(allow_none=True)


class ZonesGeoJSONSchema(Schema):
    """Schema for zones in GeoJSON FeatureCollection format."""
    
    storm_id = fields.Str(required=True)
    query_time_utc = fields.DateTime(allow_none=True)
    type = fields.Str(dump_default='FeatureCollection')
    features = fields.List(fields.Dict())
    metadata = fields.Dict()
