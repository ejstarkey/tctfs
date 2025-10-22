"""
Archive Web Blueprint - Browse historical storms.
"""
from flask import Blueprint, render_template, request
from flask_login import login_required
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('archive', __name__, url_prefix='/archive')


@bp.route('/')
@login_required
def index():
    """
    Archive browser with filters for year, basin, intensity.
    """
    from ...models import Storm
    from datetime import datetime
    
    # Get filter parameters
    year = request.args.get('year', type=int)
    basin = request.args.get('basin')
    min_intensity = request.args.get('min_intensity', type=int)
    
    # Build query for archived storms
    query = Storm.query.filter_by(status='archived')
    
    # Apply filters
    if year:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)
        query = query.filter(
            Storm.first_seen >= start_date,
            Storm.first_seen <= end_date
        )
    
    if basin:
        query = query.filter_by(basin=basin)
    
    # Order by most recent first
    storms = query.order_by(Storm.last_seen.desc()).all()
    
    # Filter by intensity if needed (requires join with advisories)
    if min_intensity:
        from ...models import Advisory
        filtered_storms = []
        for storm in storms:
            max_advisory = Advisory.query.filter_by(storm_id=storm.id).order_by(Advisory.vmax_kt.desc()).first()
            if max_advisory and max_advisory.vmax_kt and max_advisory.vmax_kt >= min_intensity:
                filtered_storms.append(storm)
        storms = filtered_storms
    
    # Get available years for filter
    all_storms = Storm.query.filter_by(status='archived').all()
    years = sorted(set(s.first_seen.year for s in all_storms if s.first_seen), reverse=True)
    
    # Get available basins
    basins = ['WP', 'EP', 'AL', 'SH', 'IO', 'CP']
    
    return render_template(
        'archive.html.j2',
        storms=storms,
        selected_year=year,
        selected_basin=basin,
        selected_min_intensity=min_intensity,
        years=years,
        basins=basins
    )


@bp.route('/storm/<storm_id>')
@login_required
def archived_storm(storm_id):
    """
    View archived storm with replay capability.
    """
    from ...models import Storm, Advisory
    
    storm = Storm.get_by_storm_id(storm_id)
    if not storm or storm.status != 'archived':
        from flask import abort
        abort(404, description=f"Archived storm {storm_id} not found")
    
    # Get all advisories for timeline
    advisories = Advisory.query.filter_by(storm_id=storm.id).order_by(Advisory.issued_at_utc.asc()).all()
    
    return render_template(
        'archive_storm.html.j2',
        storm=storm,
        advisories=advisories
    )

"""
Archive Web Blueprint - Browse historical storms.
"""
from flask import Blueprint, render_template, request
from flask_login import login_required
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('archive', __name__, url_prefix='/archive')


@bp.route('/')
@login_required
def index():
    """
    Archive browser with filters for year, basin, intensity.
    """
    from ...models import Storm
    
    # Get filter parameters
    year = request.args.get('year', type=int)
    basin = request.args.get('basin')
    min_intensity = request.args.get('min_intensity', type=int)
    
    # Build query for archived storms
    query = Storm.query.filter_by(status='archived')
    
    # Apply filters
    if year:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)
        query = query.filter(
            Storm.first_seen >= start_date,
            Storm.first_seen <= end_date
        )
    
    if basin:
        query = query.filter_by(basin=basin)
    
    # Order by most recent first
    storms = query.order_by(Storm.last_seen.desc()).all()
    
    # Filter by intensity if needed (requires join with advisories)
    if min_intensity:
        from ...models import Advisory
        filtered_storms = []
        for storm in storms:
            max_advisory = Advisory.query.filter_by(storm_id=storm.id).order_by(Advisory.vmax_kt.desc()).first()
            if max_advisory and max_advisory.vmax_kt and max_advisory.vmax_kt >= min_intensity:
                filtered_storms.append(storm)
        storms = filtered_storms
    
    # Get available years for filter
    all_storms = Storm.query.filter_by(status='archived').all()
    years = sorted(set(s.first_seen.year for s in all_storms if s.first_seen), reverse=True)
    
    # Get available basins
    basins = ['WP', 'EP', 'AL', 'SH', 'IO', 'CP']
    
    return render_template(
        'archive.html.j2',
        storms=storms,
        selected_year=year,
        selected_basin=basin,
        selected_min_intensity=min_intensity,
        years=years,
        basins=basins,
        current_year=datetime.now().year  # ADD THIS LINE FOR THE TEMPLATE
    )


@bp.route('/storm/<storm_id>')
@login_required
def archived_storm(storm_id):
    """
    View archived storm with replay capability.
    """
    from ...models import Storm, Advisory
    
    storm = Storm.get_by_storm_id(storm_id)
    if not storm or storm.status != 'archived':
        from flask import abort
        abort(404, description=f"Archived storm {storm_id} not found")
    
    # Get all advisories for timeline
    advisories = Advisory.query.filter_by(storm_id=storm.id).order_by(Advisory.issued_at_utc.asc()).all()
    
    return render_template(
        'archive_storm.html.j2',
        storm=storm,
        advisories=advisories
    )


# ADD THIS NEW ROUTE - for the storm detail redirect mentioned earlier
@bp.route('/storms/<int:storm_id>')
@login_required
def storm_detail_redirect(storm_id):
    """Redirect to archived storm detail by database ID."""
    from ...models import Storm
    from flask import redirect, url_for
    
    storm = Storm.query.get_or_404(storm_id)
    return redirect(url_for('archive.archived_storm', storm_id=storm.storm_id))
