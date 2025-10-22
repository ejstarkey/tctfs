"""
Subscription schema - API serialization for Subscription model.
"""
from marshmallow import Schema, fields, validates, ValidationError


class SubscriptionSchema(Schema):
    """Schema for Subscription model serialization."""
    
    id = fields.Int(dump_only=True)
    user_id = fields.Int(required=True)
    storm_id = fields.Int(allow_none=True)
    basin = fields.Str(allow_none=True)
    mode = fields.Str(required=True)  # immediate or digest
    email_enabled = fields.Bool(dump_default=True)
    alert_on_new_advisory = fields.Bool(dump_default=True)
    alert_on_zone_change = fields.Bool(dump_default=True)
    alert_on_intensity_change = fields.Bool(dump_default=False)
    min_intensity_kt = fields.Float(allow_none=True)
    is_active = fields.Bool(dump_default=True)
    created_at = fields.DateTime(dump_only=True)
    
    @validates('mode')
    def validate_mode(self, value):
        """Validate mode is either immediate or digest."""
        if value not in ['immediate', 'digest']:
            raise ValidationError('Mode must be either immediate or digest')


class SubscriptionListSchema(Schema):
    """Schema for list of subscriptions."""
    
    subscriptions = fields.List(fields.Nested(SubscriptionSchema))
    count = fields.Int()
