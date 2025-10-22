"""
Subscriptions API Blueprint - Alert subscription management.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('api_subscriptions', __name__)


@bp.route('/subscriptions', methods=['GET'])
@login_required
def list_subscriptions():
    """
    Get current user's subscriptions.
    """
    from ...models import Subscription
    
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    subscriptions = Subscription.get_for_user(current_user.id, active_only=active_only)
    
    return jsonify({
        'subscriptions': [sub.to_dict() for sub in subscriptions],
        'count': len(subscriptions)
    })


@bp.route('/subscriptions', methods=['POST'])
@login_required
def create_subscription():
    """
    Create a new subscription.
    
    Body (JSON):
        storm_id: Storm identifier (for per-storm subscription)
        basin: Basin code (for basin-wide subscription)
        mode: immediate|digest
        alert_on_new_advisory: bool
        alert_on_zone_change: bool
        alert_on_intensity_change: bool
        min_intensity_kt: Optional minimum intensity threshold
    
    Note: Must provide either storm_id OR basin, not both.
    """
    from ...models import Subscription, Storm
    from ...extensions import db
    
    data = request.get_json()
    
    storm_id_str = data.get('storm_id')
    basin = data.get('basin')
    
    # Validate: must have either storm_id or basin, not both
    if not storm_id_str and not basin:
        return jsonify({'error': 'Must provide either storm_id or basin'}), 400
    
    if storm_id_str and basin:
        return jsonify({'error': 'Cannot provide both storm_id and basin'}), 400
    
    # If storm_id provided, verify storm exists and get DB ID
    storm_db_id = None
    if storm_id_str:
        storm = Storm.get_by_storm_id(storm_id_str)
        if not storm:
            return jsonify({'error': f'Storm {storm_id_str} not found'}), 404
        storm_db_id = storm.id
    
    # Check if subscription already exists
    existing = Subscription.query.filter_by(
        user_id=current_user.id,
        storm_id=storm_db_id,
        basin=basin
    ).first()
    
    if existing:
        if existing.is_active:
            return jsonify({'error': 'Subscription already exists', 'subscription': existing.to_dict()}), 409
        else:
            # Reactivate existing subscription
            existing.is_active = True
            db.session.commit()
            return jsonify({'subscription': existing.to_dict()}), 200
    
    # Create new subscription
    subscription = Subscription(
        user_id=current_user.id,
        storm_id=storm_db_id,
        basin=basin,
        mode=data.get('mode', 'immediate'),
        email_enabled=data.get('email_enabled', True),
        alert_on_new_advisory=data.get('alert_on_new_advisory', True),
        alert_on_zone_change=data.get('alert_on_zone_change', True),
        alert_on_intensity_change=data.get('alert_on_intensity_change', False),
        min_intensity_kt=data.get('min_intensity_kt'),
        is_active=True
    )
    
    db.session.add(subscription)
    db.session.commit()
    
    return jsonify({'subscription': subscription.to_dict()}), 201


@bp.route('/subscriptions/<int:subscription_id>', methods=['DELETE'])
@login_required
def delete_subscription(subscription_id):
    """
    Delete (deactivate) a subscription.
    """
    from ...models import Subscription
    from ...extensions import db
    
    subscription = Subscription.query.get_or_404(subscription_id)
    
    # Verify ownership
    if subscription.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    # Deactivate instead of hard delete
    subscription.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'Subscription deleted'}), 200


@bp.route('/subscriptions/<int:subscription_id>', methods=['PATCH'])
@login_required
def update_subscription(subscription_id):
    """
    Update subscription preferences.
    
    Body (JSON):
        mode: immediate|digest
        email_enabled: bool
        alert_on_new_advisory: bool
        alert_on_zone_change: bool
        alert_on_intensity_change: bool
        min_intensity_kt: float or null
    """
    from ...models import Subscription
    from ...extensions import db
    
    subscription = Subscription.query.get_or_404(subscription_id)
    
    # Verify ownership
    if subscription.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    # Update fields
    if 'mode' in data:
        subscription.mode = data['mode']
    if 'email_enabled' in data:
        subscription.email_enabled = data['email_enabled']
    if 'alert_on_new_advisory' in data:
        subscription.alert_on_new_advisory = data['alert_on_new_advisory']
    if 'alert_on_zone_change' in data:
        subscription.alert_on_zone_change = data['alert_on_zone_change']
    if 'alert_on_intensity_change' in data:
        subscription.alert_on_intensity_change = data['alert_on_intensity_change']
    if 'min_intensity_kt' in data:
        subscription.min_intensity_kt = data['min_intensity_kt']
    
    db.session.commit()
    
    return jsonify({'subscription': subscription.to_dict()}), 200
