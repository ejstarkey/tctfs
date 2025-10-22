"""
Health API Blueprint - Health check and metrics endpoints.
"""
from flask import Blueprint, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('api_health', __name__)


@bp.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint.
    """
    from ...extensions import db
    
    # Check database connection
    db_healthy = True
    try:
        db.session.execute('SELECT 1')
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_healthy = False
    
    status = 'healthy' if db_healthy else 'unhealthy'
    status_code = 200 if db_healthy else 503
    
    return jsonify({
        'status': status,
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {
            'database': 'ok' if db_healthy else 'failed'
        }
    }), status_code


@bp.route('/health/deep', methods=['GET'])
def deep_health_check():
    """
    Comprehensive health check with all components.
    """
    from ...extensions import db
    from ...models import Storm
    import redis
    
    checks = {}
    
    # Database check
    try:
        db.session.execute('SELECT 1')
        checks['database'] = 'ok'
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        checks['database'] = 'failed'
    
    # Redis check
    try:
        from flask import current_app
        redis_url = current_app.config.get('REDIS_URL')
        if redis_url:
            r = redis.from_url(redis_url)
            r.ping()
            checks['redis'] = 'ok'
        else:
            checks['redis'] = 'not_configured'
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        checks['redis'] = 'failed'
    
    # Check active storms count
    try:
        active_count = Storm.query.filter_by(status='active').count()
        checks['active_storms'] = active_count
    except:
        checks['active_storms'] = 'unknown'
    
    # Overall status
    all_ok = all(
        v == 'ok' or (isinstance(v, int) and v >= 0) or v == 'not_configured'
        for v in checks.values()
    )
    
    status = 'healthy' if all_ok else 'degraded'
    status_code = 200 if all_ok else 503
    
    return jsonify({
        'status': status,
        'timestamp': datetime.utcnow().isoformat(),
        'checks': checks
    }), status_code


@bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Prometheus-compatible metrics endpoint.
    """
    from ...models import Storm, User, Subscription, Advisory
    from datetime import datetime, timedelta
    
    try:
        # Gather metrics
        active_storms = Storm.query.filter_by(status='active').count()
        dormant_storms = Storm.query.filter_by(status='dormant').count()
        archived_storms = Storm.query.filter_by(status='archived').count()
        
        total_users = User.query.filter_by(is_active=True).count()
        total_subscriptions = Subscription.query.filter_by(is_active=True).count()
        
        # Recent advisory count (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_advisories = Advisory.query.filter(Advisory.created_at >= one_hour_ago).count()
        
        # Format as Prometheus metrics
        metrics_output = f"""# HELP tctfs_storms_active Number of active storms
# TYPE tctfs_storms_active gauge
tctfs_storms_active {active_storms}

# HELP tctfs_storms_dormant Number of dormant storms
# TYPE tctfs_storms_dormant gauge
tctfs_storms_dormant {dormant_storms}

# HELP tctfs_storms_archived Number of archived storms
# TYPE tctfs_storms_archived gauge
tctfs_storms_archived {archived_storms}

# HELP tctfs_users_active Number of active users
# TYPE tctfs_users_active gauge
tctfs_users_active {total_users}

# HELP tctfs_subscriptions_active Number of active subscriptions
# TYPE tctfs_subscriptions_active gauge
tctfs_subscriptions_active {total_subscriptions}

# HELP tctfs_advisories_recent Advisories ingested in last hour
# TYPE tctfs_advisories_recent counter
tctfs_advisories_recent {recent_advisories}
"""
        
        return metrics_output, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"Metrics generation failed: {e}")
        return "# Metrics unavailable\n", 500, {'Content-Type': 'text/plain; charset=utf-8'}


@bp.route('/version', methods=['GET'])
def version():
    """
    Get application version information.
    """
    return jsonify({
        'application': 'TCTFS',
        'version': '1.0.0',  # TODO: Get from package
        'python_version': '3.12',
        'build_date': '2025-01-01'  # TODO: Get from build info
    })
