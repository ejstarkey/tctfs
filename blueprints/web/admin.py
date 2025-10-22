"""
Admin Web Blueprint - Admin dashboard and management.
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from functools import wraps
import logging

from ...models.storm import Storm
from ...models.user import User
from ...models.subscription import Subscription

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            from flask import abort
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/')
@admin_required
def index():
    """Admin dashboard."""
    # Get statistics
    active_storms = Storm.query.filter_by(status='active').count()
    total_users = User.query.count()
    total_subscriptions = Subscription.query.filter_by(is_active=True).count()
    
    stats = {
        'active_storms': active_storms,
        'total_users': total_users,
        'subscriptions': total_subscriptions
    }
    
    logger.info(f"Admin dashboard stats: {stats}")
    
    return render_template('admin/index.html.j2',
                         stats=stats,
                         system_status='Healthy')


@bp.route('/storms')
@admin_required
def storms():
    """Storm browser."""
    all_storms = Storm.query.order_by(Storm.last_seen.desc()).all()
    
    return render_template('admin/storm_browser.html.j2',
                         storms=all_storms)


@bp.route('/users')
@admin_required
def users():
    """User management."""
    all_users = User.query.order_by(User.created_at.desc()).all()
    
    return render_template('admin/users.html.j2',
                         users=all_users)
