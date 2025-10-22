"""
Base History Parser - Tolerant line parsing with basin-specific adapters.
"""
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


class BaseHistoryParser:
    """
    Base class for parsing *-list.txt history files.
    Provides common parsing utilities and error handling.
    """
    
    def __init__(self):
        self.parse_errors = []
    
    def parse_file(self, content: str) -> List[Dict]:
        """
        Parse history file content into normalized advisory records.
        
        Args:
            content: Raw text content of *-list.txt file
        
        Returns:
            List of advisory dictionaries
        """
        self.parse_errors = []
        advisories = []
        
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            try:
                advisory = self.parse_line(line)
                if advisory:
                    advisory['line_num'] = line_num
                    advisory['raw_line'] = line
                    advisories.append(advisory)
            except Exception as e:
                self.parse_errors.append({
                    'line_num': line_num,
                    'line': line,
                    'error': str(e)
                })
                logger.warning(f"Failed to parse line {line_num}: {e}")
        
        if self.parse_errors:
            logger.warning(f"Encountered {len(self.parse_errors)} parse errors")
        
        return advisories
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single line from history file.
        Must be implemented by basin-specific subclasses.
        
        Returns:
            Dictionary with keys: timestamp, lat, lon, vmax_kt, mslp_hpa, 
            motion_bearing, motion_speed, radii (optional)
        """
        raise NotImplementedError("Subclasses must implement parse_line()")
    
    def parse_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """
        Parse date and time strings into UTC datetime.
        
        Args:
            date_str: Date in various formats (YYYYMMDD, YYYY-MM-DD, etc.)
            time_str: Time in HHMM or HH:MM format
        
        Returns:
            datetime object in UTC, or None if parsing fails
        """
        try:
            # Remove separators
            date_str = date_str.replace('-', '').replace('/', '')
            time_str = time_str.replace(':', '')
            
            # Parse YYYYMMDDHHMM
            dt_str = f"{date_str}{time_str}"
            dt = datetime.strptime(dt_str, '%Y%m%d%H%M')
            
            # Assume UTC
            return pytz.utc.localize(dt)
            
        except ValueError as e:
            logger.warning(f"Failed to parse datetime {date_str} {time_str}: {e}")
            return None
    
    def parse_latlon(self, lat_str: str, lon_str: str) -> Optional[tuple]:
        """
        Parse latitude and longitude strings.
        
        Args:
            lat_str: Latitude (e.g., "12.5N", "12.5", "-12.5")
            lon_str: Longitude (e.g., "125.3E", "125.3", "-125.3")
        
        Returns:
            Tuple of (lat, lon) as floats, or None if parsing fails
        """
        try:
            # Extract numeric value
            lat_match = re.search(r'([+-]?\d+\.?\d*)', lat_str)
            lon_match = re.search(r'([+-]?\d+\.?\d*)', lon_str)
            
            if not lat_match or not lon_match:
                return None
            
            lat = float(lat_match.group(1))
            lon = float(lon_match.group(1))
            
            # Handle N/S/E/W suffixes
            if 'S' in lat_str.upper():
                lat = -abs(lat)
            if 'W' in lon_str.upper():
                lon = -abs(lon)
            
            # Validate ranges
            if not (-90 <= lat <= 90):
                logger.warning(f"Invalid latitude: {lat}")
                return None
            if not (-180 <= lon <= 180):
                logger.warning(f"Invalid longitude: {lon}")
                return None
            
            return (lat, lon)
            
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse lat/lon {lat_str}/{lon_str}: {e}")
            return None
    
    def parse_intensity(self, vmax_str: str) -> Optional[float]:
        """
        Parse maximum wind speed.
        
        Args:
            vmax_str: Wind speed string (e.g., "65", "65kt", "N/A")
        
        Returns:
            Wind speed in knots, or None if not available
        """
        try:
            # Extract numeric value
            match = re.search(r'(\d+\.?\d*)', vmax_str)
            if match:
                return float(match.group(1))
            return None
        except (ValueError, AttributeError):
            return None
    
    def parse_pressure(self, mslp_str: str) -> Optional[float]:
        """
        Parse minimum sea level pressure.
        
        Args:
            mslp_str: Pressure string (e.g., "980", "980hPa", "N/A")
        
        Returns:
            Pressure in hPa, or None if not available
        """
        try:
            # Extract numeric value
            match = re.search(r'(\d+\.?\d*)', mslp_str)
            if match:
                return float(match.group(1))
            return None
        except (ValueError, AttributeError):
            return None
    
    def parse_motion(self, bearing_str: str, speed_str: str) -> Optional[tuple]:
        """
        Parse motion bearing and speed.
        
        Args:
            bearing_str: Direction (e.g., "270", "W", "WSW")
            speed_str: Speed (e.g., "12", "12kt")
        
        Returns:
            Tuple of (bearing_deg, speed_kt), or None if parsing fails
        """
        try:
            # Parse bearing
            bearing = None
            
            # Try numeric bearing
            match = re.search(r'(\d+\.?\d*)', bearing_str)
            if match:
                bearing = float(match.group(1))
            else:
                # Try cardinal direction
                cardinal_map = {
                    'N': 0, 'NNE': 22.5, 'NE': 45, 'ENE': 67.5,
                    'E': 90, 'ESE': 112.5, 'SE': 135, 'SSE': 157.5,
                    'S': 180, 'SSW': 202.5, 'SW': 225, 'WSW': 247.5,
                    'W': 270, 'WNW': 292.5, 'NW': 315, 'NNW': 337.5
                }
                bearing = cardinal_map.get(bearing_str.upper())
            
            # Parse speed
            speed_match = re.search(r'(\d+\.?\d*)', speed_str)
            if not speed_match:
                return None
            
            speed = float(speed_match.group(1))
            
            if bearing is not None and 0 <= bearing <= 360:
                return (bearing, speed)
            
            return None
            
        except (ValueError, AttributeError):
            return None
