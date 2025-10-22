"""
Feature flags - Toggle features on/off.
"""
import os
from flask import current_app


def is_enabled(flag_name, default=False):
    """
    Check if a feature flag is enabled.
    
    Args:
        flag_name: Name of feature flag
        default: Default value if not set
    
    Returns:
        True if enabled
    """
    try:
        # Check environment variable first
        env_var = f"FEATURE_{flag_name.upper()}"
        env_value = os.getenv(env_var)
        
        if env_value is not None:
            return env_value.lower() in ('true', '1', 'yes', 'on')
        
        # Check app config
        if current_app:
            config_key = f"FEATURE_{flag_name.upper()}"
            return current_app.config.get(config_key, default)
        
        return default
        
    except:
        return default


# Predefined feature flags
def forecast_enabled():
    """Check if forecast feature is enabled."""
    return is_enabled('FORECAST', default=True)


def zones_enabled():
    """Check if zone generation is enabled."""
    return is_enabled('ZONES', default=True)


def alerts_enabled():
    """Check if email alerts are enabled."""
    return is_enabled('ALERTS', default=True)


def websockets_enabled():
    """Check if WebSocket real-time updates are enabled."""
    return is_enabled('WEBSOCKETS', default=True)
