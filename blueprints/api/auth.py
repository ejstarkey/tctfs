"""
Auth API Blueprint - Authentication endpoints.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_user, logout_user, login_required, current_user
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('api_auth', __name__)


@bp.route('/login', methods=['POST'])
def login():
    """
    Login endpoint.
    
    Body (JSON):
        email: User email
        password: Password
        remember: Optional remember me flag (default false)
    """
    from ...models import User
    from ...extensions import db
    
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember = data.get('remember', False)
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    # Find user
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        logger.warning(f"Failed login attempt for {email} from {request.remote_addr}")
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is disabled'}), 403
    
    # Check if TOTP is enabled
    if user.totp_enabled:
        # Store user ID in session for TOTP verification step
        from flask import session
        session['totp_user_id'] = user.id
        session['totp_remember'] = remember
        
        return jsonify({
            'totp_required': True,
            'message': 'TOTP verification required'
        }), 200
    
    # Login user
    login_user(user, remember=remember)
    
    # Update last login
    user.update_last_login(request.remote_addr)
    db.session.commit()
    
    logger.info(f"User {email} logged in from {request.remote_addr}")
    
    return jsonify({
        'user': user.to_dict(),
        'message': 'Login successful'
    }), 200


@bp.route('/totp/verify', methods=['POST'])
def verify_totp():
    """
    Verify TOTP token for 2FA login.
    
    Body (JSON):
        token: 6-digit TOTP token
    """
    from flask import session
    from ...models import User
    from ..services.authn.totp import get_totp_service
    from ...extensions import db
    
    data = request.get_json()
    token = data.get('token', '').strip()
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    # Get user ID from session
    user_id = session.get('totp_user_id')
    if not user_id:
        return jsonify({'error': 'No TOTP session found'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Verify token
    totp_service = get_totp_service()
    if not totp_service.verify_token(user.totp_secret, token):
        logger.warning(f"Failed TOTP verification for {user.email}")
        return jsonify({'error': 'Invalid token'}), 401
    
    # Login user
    remember = session.get('totp_remember', False)
    login_user(user, remember=remember)
    
    # Update last login
    user.update_last_login(request.remote_addr)
    db.session.commit()
    
    # Clear TOTP session
    session.pop('totp_user_id', None)
    session.pop('totp_remember', None)
    
    logger.info(f"User {user.email} completed 2FA login")
    
    return jsonify({
        'user': user.to_dict(),
        'message': 'Login successful'
    }), 200


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    Logout current user.
    """
    email = current_user.email
    logout_user()
    
    logger.info(f"User {email} logged out")
    
    return jsonify({'message': 'Logout successful'}), 200


@bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """
    Get current authenticated user info.
    """
    return jsonify({
        'user': current_user.to_dict(include_sensitive=True)
    }), 200


@bp.route('/check', methods=['GET'])
def check_auth():
    """
    Check if user is authenticated.
    """
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict()
        }), 200
    else:
        return jsonify({
            'authenticated': False
        }), 200
