"""
Account Web Blueprint - User profile, authentication and subscription management.
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user, login_user, logout_user
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('account', __name__, url_prefix='/account')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        from ...models.user import User
        from ...extensions import db
        
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please provide email and password', 'error')
            return render_template('login.html.j2')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Account is disabled', 'error')
                return render_template('login.html.j2')
            
            login_user(user, remember=True)
            user.update_last_login(request.remote_addr)
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html.j2')


@bp.route('/logout')
@login_required
def logout():
    """Logout user."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('account.login'))


@bp.route('/')
@login_required
def index():
    """Account overview page."""
    return redirect(url_for('account.profile'))


@bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template(
        'account.html.j2',
        user=current_user,
        active_tab='profile'
    )


@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information."""
    from ...extensions import db
    
    full_name = request.form.get('full_name', '').strip()
    
    if full_name:
        current_user.full_name = full_name
        db.session.commit()
        flash('Profile updated successfully', 'success')
    
    return redirect(url_for('account.profile'))


@bp.route('/subscriptions')
@login_required
def subscriptions():
    """User subscriptions page."""
    from ...models.subscription import Subscription
    
    user_subs = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    return render_template(
        'account.html.j2',
        user=current_user,
        subscriptions=user_subs,
        active_tab='subscriptions'
    )
