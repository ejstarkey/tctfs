"""
Parsing utilities - Robust regex helpers and text parsing functions.
"""
import re
import logging
from typing import List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


def safe_split(text: str, delimiter: str = None, max_split: int = -1) -> List[str]:
    """
    Safely split text, handling None and empty strings.
    
    Args:
        text: Text to split
        delimiter: Split delimiter (None for whitespace)
        max_split: Maximum number of splits
    
    Returns:
        List of strings
    """
    if not text:
        return []
    
    if delimiter is None:
        return text.split(maxsplit=max_split)
    
    return text.split(delimiter, maxsplit=max_split)


def extract_numbers(text: str, as_float: bool = True) -> List[Union[int, float]]:
    """
    Extract all numbers from text.
    
    Args:
        text: Text to parse
        as_float: Return floats instead of strings
    
    Returns:
        List of numbers
    """
    if not text:
        return []
    
    # Match integers and decimals (including negative)
    pattern = r'[-+]?\d*\.?\d+'
    matches = re.findall(pattern, text)
    
    if as_float:
        return [float(m) for m in matches if m]
    
    return [int(float(m)) for m in matches if m and '.' not in m]


def extract_first_number(text: str, default: Optional[float] = None) -> Optional[float]:
    """
    Extract first number from text.
    
    Args:
        text: Text to parse
        default: Default value if no number found
    
    Returns:
        First number or default
    """
    numbers = extract_numbers(text)
    return numbers[0] if numbers else default


def parse_cardinal_direction(direction: str) -> Optional[float]:
    """
    Parse cardinal direction (N, NE, E, etc.) to degrees.
    
    Args:
        direction: Cardinal direction string
    
    Returns:
        Bearing in degrees (0-360), or None if invalid
    """
    if not direction:
        return None
    
    direction = direction.upper().strip()
    
    cardinal_map = {
        'N': 0, 'NNE': 22.5, 'NE': 45, 'ENE': 67.5,
        'E': 90, 'ESE': 112.5, 'SE': 135, 'SSE': 157.5,
        'S': 180, 'SSW': 202.5, 'SW': 225, 'WSW': 247.5,
        'W': 270, 'WNW': 292.5, 'NW': 315, 'NNW': 337.5
    }
    
    return cardinal_map.get(direction)


def parse_latlon_string(lat_str: str, lon_str: str) -> Optional[Tuple[float, float]]:
    """
    Parse latitude/longitude strings in various formats.
    
    Supported formats:
    - "12.5N", "125.3E"
    - "12.5", "-125.3"
    - "12°30'N", "125°18'E"
    
    Args:
        lat_str: Latitude string
        lon_str: Longitude string
    
    Returns:
        Tuple of (lat, lon) or None if parsing fails
    """
    try:
        # Try simple decimal format first
        lat_match = re.search(r'([+-]?\d+\.?\d*)', lat_str)
        lon_match = re.search(r'([+-]?\d+\.?\d*)', lon_str)
        
        if not lat_match or not lon_match:
            return None
        
        lat = float(lat_match.group(1))
        lon = float(lon_match.group(1))
        
        # Handle hemisphere indicators
        if 'S' in lat_str.upper():
            lat = -abs(lat)
        elif 'N' in lat_str.upper():
            lat = abs(lat)
        
        if 'W' in lon_str.upper():
            lon = -abs(lon)
        elif 'E' in lon_str.upper():
            lon = abs(lon)
        
        # Validate ranges
        if not (-90 <= lat <= 90):
            logger.warning(f"Invalid latitude: {lat}")
            return None
        
        if not (-180 <= lon <= 180):
            logger.warning(f"Invalid longitude: {lon}")
            return None
        
        return (lat, lon)
        
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse lat/lon '{lat_str}'/'{lon_str}': {e}")
        return None


def clean_whitespace(text: str) -> str:
    """
    Clean and normalize whitespace in text.
    
    Args:
        text: Text to clean
    
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    return text.strip()


def extract_storm_id(text: str) -> Optional[str]:
    """
    Extract storm ID from text (e.g., "28W", "03S", "15E").
    
    Args:
        text: Text containing storm ID
    
    Returns:
        Storm ID or None
    """
    match = re.search(r'\b(\d{2}[A-Z])\b', text)
    return match.group(1) if match else None


def parse_intensity_category(vmax_kt: float) -> str:
    """
    Determine intensity category from maximum wind speed.
    
    Args:
        vmax_kt: Maximum wind speed in knots
    
    Returns:
        Category string (TD, TS, CAT1-5)
    """
    if vmax_kt < 34:
        return 'TD'  # Tropical Depression
    elif vmax_kt < 64:
        return 'TS'  # Tropical Storm
    elif vmax_kt < 83:
        return 'CAT1'  # Category 1
    elif vmax_kt < 96:
        return 'CAT2'
    elif vmax_kt < 113:
        return 'CAT3'
    elif vmax_kt < 137:
        return 'CAT4'
    else:
        return 'CAT5'


def normalize_basin_code(basin: str) -> str:
    """
    Normalize basin code to standard format.
    
    Args:
        basin: Basin code (various formats)
    
    Returns:
        Standardized basin code (WP, EP, AL, CP, SH, IO)
    """
    basin = basin.upper().strip()
    
    basin_map = {
        'W': 'WP',
        'WEST': 'WP',
        'WPAC': 'WP',
        'E': 'EP',
        'EAST': 'EP',
        'EPAC': 'EP',
        'L': 'AL',
        'ATL': 'AL',
        'ATLANTIC': 'AL',
        'C': 'CP',
        'CPAC': 'CP',
        'S': 'SH',
        'SOUTH': 'SH',
        'I': 'IO',
        'INDIAN': 'IO',
        'A': 'IO',
        'B': 'IO',
    }
    
    return basin_map.get(basin, basin)


def parse_boolean(value: Union[str, bool, int, None]) -> bool:
    """
    Parse various representations of boolean values.
    
    Args:
        value: Value to parse
    
    Returns:
        Boolean value
    """
    if value is None:
        return False
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, int):
        return value != 0
    
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on', 'y', 't')
    
    return bool(value)
