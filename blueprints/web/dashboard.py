"""
Dashboard Web Blueprint - Main landing page with active storms.
"""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('dashboard', __name__, url_prefix='/')


@bp.route('/')
@login_required
def index():
    """
    Main dashboard page showing all active tropical cyclones.
    """
    # Get filter parameters from query string
    basin_filter = request.args.get('basin', None)
    status_filter = request.args.get('status', 'active')
    search_query = request.args.get('q', '')
    
    # Import models here to avoid circular imports
    from ...models import Storm
    
    # Build query
    query = Storm.query
    
    # Apply filters
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if basin_filter:
        query = query.filter_by(basin=basin_filter)
    
    if search_query:
        query = query.filter(
            (Storm.name.ilike(f'%{search_query}%')) |
            (Storm.storm_id.ilike(f'%{search_query}%'))
        )
    
    # Order by most recent
    storms = query.order_by(Storm.last_seen.desc()).all()
    
    # Get user's favorites (if implemented)
    favorite_storm_ids = []
    if current_user.is_authenticated:
        # TODO: Implement favorites in user metadata
        pass
    
    return render_template(
        'dashboard.html.j2',
        storms=storms,
        basin_filter=basin_filter,
        status_filter=status_filter,
        search_query=search_query,
        favorite_storm_ids=favorite_storm_ids
    )


@bp.route('/storms')
@login_required
def storms_list():
    """
    Alternative storms list view (redirect to dashboard).
    """
    from flask import redirect, url_for
    return redirect(url_for('dashboard.index'))
