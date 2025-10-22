"""
A-Deck Parse Service - Parse A-Deck forecast files.
"""
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


class AdeckParseService:
    """
    Parser for A-Deck forecast files.
    
    Line format (comma-separated):
    basin, storm_num, yyyymmddhh, reserved, model_code, forecast_hour, 
    lat, lon, vmax_kt, mslp_hpa, [additional fields...]
    """
    
    def __init__(self):
        self.parse_errors = []
    
    def parse_file(self, content: str, filter_models: Optional[List[str]] = None) -> List[Dict]:
        """
        Parse A-Deck file content.
        
        Args:
            content: Raw text content of A-Deck file
            filter_models: List of model codes to filter (e.g., ['AP01', 'AP02', ...])
                          If None, parse all models
        
        Returns:
            List of forecast point dictionaries
        """
        self.parse_errors = []
        forecasts = []
        
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            try:
                forecast = self.parse_line(line)
                if forecast:
                    # Filter by model if specified
                    if filter_models is None or forecast['model_code'] in filter_models:
                        forecast['line_num'] = line_num
                        forecast['raw_line'] = line
                        forecasts.append(forecast)
            except Exception as e:
                self.parse_errors.append({
                    'line_num': line_num,
                    'line': line,
                    'error': str(e)
                })
                logger.warning(f"Failed to parse A-Deck line {line_num}: {e}")
        
        if self.parse_errors:
            logger.warning(f"Encountered {len(self.parse_errors)} A-Deck parse errors")
        
        return forecasts
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single A-Deck line.
        
        Returns:
            Dictionary with forecast point data
        """
        parts = [p.strip() for p in line.split(',')]
        
        if len(parts) < 10:
            return None
        
        basin = parts[0]
        storm_num = parts[1]
        datetime_str = parts[2]  # YYYYMMDDHH
        model_code = parts[4]
        forecast_hour = parts[5]
        lat_str = parts[6]
        lon_str = parts[7]
        vmax_str = parts[8]
        mslp_str = parts[9]
        
        # Parse issuance time
        try:
            issuance_time = datetime.strptime(datetime_str, '%Y%m%d%H')
            issuance_time = pytz.utc.localize(issuance_time)
        except ValueError:
            logger.warning(f"Invalid datetime in A-Deck: {datetime_str}")
            return None
        
        # Parse forecast hour
        try:
            fhour = int(forecast_hour)
        except ValueError:
            return None
        
        # Parse lat/lon
        latlon = self._parse_latlon(lat_str, lon_str)
        if not latlon:
            return None
        
        lat, lon = latlon
        
        # Parse intensity
        vmax = self._parse_number(vmax_str)
        mslp = self._parse_number(mslp_str)
        
        # Parse radii if present (optional, starting around index 11)
        radii = None
        if len(parts) > 11:
            radii = self._parse_radii(parts[11:])
        
        return {
            'basin': basin,
            'storm_num': storm_num,
            'issuance_time': issuance_time,
            'model_code': model_code,
            'forecast_hour': fhour,
            'latitude': lat,
            'longitude': lon,
            'vmax_kt': vmax,
            'mslp_hpa': mslp,
            'radii': radii
        }
    
    def _parse_latlon(self, lat_str: str, lon_str: str) -> Optional[tuple]:
        """Parse lat/lon from A-Deck format (e.g., 125N, 1453E)."""
        try:
            # Extract numeric and hemisphere
            lat_match = re.match(r'(\d+)([NS])', lat_str)
            lon_match = re.match(r'(\d+)([EW])', lon_str)
            
            if not lat_match or not lon_match:
                return None
            
            # Lat is in tenths of degrees (e.g., 125 = 12.5°)
            lat = float(lat_match.group(1)) / 10.0
            lon = float(lon_match.group(1)) / 10.0
            
            # Apply hemisphere
            if lat_match.group(2) == 'S':
                lat = -lat
            if lon_match.group(2) == 'W':
                lon = -lon
            
            return (lat, lon)
            
        except (ValueError, AttributeError):
            return None
    
    def _parse_number(self, num_str: str) -> Optional[float]:
        """Parse numeric value, handling missing/invalid data."""
        try:
            num_str = num_str.strip()
            if not num_str or num_str in ['-', 'N/A', 'XXX']:
                return None
            return float(num_str)
        except ValueError:
            return None
    
    def _parse_radii(self, radii_parts: List[str]) -> Optional[Dict]:
        """
        Parse wind radii from A-Deck (optional fields).
        Format varies, typically: RAD, R34_NE, R34_SE, R34_SW, R34_NW, ...
        """
        # Simplified: just return None for now, can expand later
        # Full implementation would parse quadrant radii if present
        return None
    
    def filter_ap_members(self, forecasts: List[Dict], ap_range: tuple = (1, 30)) -> List[Dict]:
        """
        Filter forecasts to only AP ensemble members.
        
        Args:
            forecasts: List of parsed forecast dictionaries
            ap_range: Tuple of (min, max) AP member numbers (default: 1-30)
        
        Returns:
            Filtered list containing only AP01-AP30 members
        """
        ap_min, ap_max = ap_range
        ap_models = [f"AP{i:02d}" for i in range(ap_min, ap_max + 1)]
        
        return [f for f in forecasts if f['model_code'] in ap_models]


# Singleton instance
_adeck_parse_service = None

def get_adeck_parse_service() -> AdeckParseService:
    """Get or create the singleton A-Deck parse service."""
    global _adeck_parse_service
    if _adeck_parse_service is None:
        _adeck_parse_service = AdeckParseService()
    return _adeck_parse_service
