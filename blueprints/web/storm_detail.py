"""
Storm Detail Web Blueprint - Individual storm page with interactive map.
"""
from flask import Blueprint, render_template, abort
from flask_login import login_required
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('storm_detail', __name__, url_prefix='/storms')


@bp.route('/<storm_id>')
@login_required
def detail(storm_id):
    """
    Storm detail page with interactive map, track, and forecast.
    
    Args:
        storm_id: Storm identifier (e.g., "28W", "03S")
    """
    from ...models import Storm, Advisory, ForecastPoint
    
    # Get storm
    storm = Storm.get_by_storm_id(storm_id)
    if not storm:
        abort(404, description=f"Storm {storm_id} not found")
    
    # Get latest advisory
    latest_advisory = Advisory.get_latest_for_storm(storm.id)
    
    # Get advisory count
    advisory_count = Advisory.query.filter_by(storm_id=storm.id).count()
    
    # Get latest forecast
    latest_forecast = ForecastPoint.get_latest_forecast(storm.id)
    
    # Check if user is subscribed
    is_subscribed = False
    if current_user.is_authenticated:
        from ...models import Subscription
        subscription = Subscription.query.filter_by(
            user_id=current_user.id,
            storm_id=storm.id,
            is_active=True
        ).first()
        is_subscribed = subscription is not None
    
    return render_template(
        'storm_detail.html.j2',
        storm=storm,
        latest_advisory=latest_advisory,
        advisory_count=advisory_count,
        has_forecast=len(latest_forecast) > 0 if latest_forecast else False,
        is_subscribed=is_subscribed
    )


@bp.route('/<storm_id>/track')
@login_required
def track(storm_id):
    """
    Full-screen track view for a storm.
    """
    from ...models import Storm
    
    storm = Storm.get_by_storm_id(storm_id)
    if not storm:
        abort(404, description=f"Storm {storm_id} not found")
    
    return render_template(
        'storm_track.html.j2',
        storm=storm
    )

def get_category(vmax_kt):
    """Get Saffir-Simpson category from wind speed."""
    if not vmax_kt:
        return 0
    if vmax_kt < 34:
        return 0  # TD
    elif vmax_kt < 64:
        return 0  # TS
    elif vmax_kt < 83:
        return 1
    elif vmax_kt < 96:
        return 2
    elif vmax_kt < 113:
        return 3
    elif vmax_kt < 137:
        return 4
    else:
        return 5

def get_category_name(vmax_kt):
    """Get category name from wind speed."""
    if not vmax_kt:
        return 'UNKNOWN'
    if vmax_kt < 34:
        return 'TD'
    elif vmax_kt < 64:
        return 'TS'
    elif vmax_kt < 83:
        return 'CAT 1'
    elif vmax_kt < 96:
        return 'CAT 2'
    elif vmax_kt < 113:
        return 'CAT 3'
    elif vmax_kt < 137:
        return 'CAT 4'
    else:
        return 'CAT 5'

# Add to template context
bp.context_processor(lambda: {
    'get_category': get_category,
    'get_category_name': get_category_name
})
