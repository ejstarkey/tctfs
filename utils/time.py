"""
Time utilities - UTC helpers and datetime formatting.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import pytz


def utc_now() -> datetime:
    """
    Get current UTC datetime.
    
    Returns:
        Current datetime in UTC with timezone info
    """
    return datetime.now(timezone.utc)


def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    """
    Parse ISO 8601 datetime string to datetime object.
    
    Args:
        dt_str: ISO datetime string
    
    Returns:
        datetime object with timezone, or None if parsing fails
    """
    if not dt_str:
        return None
    
    try:
        # Try parsing with fromisoformat (Python 3.7+)
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        pass
    
    # Try common formats
    formats = [
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y%m%d%H%M',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(dt_str, fmt)
            # Add UTC timezone if naive
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            return dt
        except ValueError:
            continue
    
    return None


def format_datetime(dt: datetime, fmt: str = 'iso') -> str:
    """
    Format datetime to string.
    
    Args:
        dt: datetime object
        fmt: Format type ('iso', 'human', 'compact')
    
    Returns:
        Formatted datetime string
    """
    if not dt:
        return ''
    
    # Ensure UTC
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    elif dt.tzinfo != pytz.utc:
        dt = dt.astimezone(pytz.utc)
    
    if fmt == 'iso':
        return dt.isoformat()
    elif fmt == 'human':
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    elif fmt == 'compact':
        return dt.strftime('%Y%m%d%H%M')
    elif fmt == 'date':
        return dt.strftime('%Y-%m-%d')
    elif fmt == 'time':
        return dt.strftime('%H:%M:%S')
    else:
        return dt.strftime(fmt)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp.
    
    Args:
        dt: datetime object
    
    Returns:
        Unix timestamp (seconds since epoch)
    """
    return int(dt.timestamp())


def timestamp_to_datetime(ts: Union[int, float]) -> datetime:
    """
    Convert Unix timestamp to datetime.
    
    Args:
        ts: Unix timestamp
    
    Returns:
        datetime object in UTC
    """
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string.
    
    Args:
        dt: datetime object
    
    Returns:
        String like "5 minutes ago", "2 hours ago"
    """
    if not dt:
        return 'unknown'
    
    now = utc_now()
    
    # Ensure both have timezone info
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    if now.tzinfo is None:
        now = pytz.utc.localize(now)
    
    delta = now - dt
    
    seconds = delta.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"


def add_hours(dt: datetime, hours: int) -> datetime:
    """
    Add hours to datetime.
    
    Args:
        dt: datetime object
        hours: Number of hours to add
    
    Returns:
        New datetime object
    """
    return dt + timedelta(hours=hours)


def round_to_nearest_hour(dt: datetime) -> datetime:
    """
    Round datetime to nearest hour.
    
    Args:
        dt: datetime object
    
    Returns:
        Rounded datetime
    """
    if dt.minute >= 30:
        return dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        return dt.replace(minute=0, second=0, microsecond=0)


def get_forecast_lead_times(max_hours: int = 120, interval: int = 6) -> list:
    """
    Generate standard forecast lead times.
    
    Args:
        max_hours: Maximum forecast lead time
        interval: Interval between lead times in hours
    
    Returns:
        List of lead times [0, 6, 12, 18, ...]
    """
    return list(range(0, max_hours + 1, interval))


def is_recent(dt: datetime, hours: int = 24) -> bool:
    """
    Check if datetime is within the last N hours.
    
    Args:
        dt: datetime to check
        hours: Number of hours to consider recent
    
    Returns:
        True if datetime is recent
    """
    if not dt:
        return False
    
    now = utc_now()
    
    # Ensure timezone info
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    delta = now - dt
    return delta.total_seconds() <= (hours * 3600)
