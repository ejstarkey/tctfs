"""
Indian Ocean Basin Parser - Parse IO history files.
"""
import re
from typing import Optional, Dict
from .base import BaseHistoryParser


class IndianOceanParser(BaseHistoryParser):
    """
    Parser for Indian Ocean basin *-list.txt files.
    """
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """
        Parse a line from IO basin history file.
        """
        parts = line.split()
        
        if len(parts) < 6:
            return None
        
        # Parse timestamp
        date_str = parts[0]
        time_str = parts[1]
        timestamp = self.parse_datetime(date_str, time_str)
        
        if not timestamp:
            return None
        
        # Parse position
        lat_str = parts[2]
        lon_str = parts[3]
        latlon = self.parse_latlon(lat_str, lon_str)
        
        if not latlon:
            return None
        
        lat, lon = latlon
        
        # Parse intensity
        vmax = self.parse_intensity(parts[4])
        mslp = self.parse_pressure(parts[5]) if len(parts) > 5 else None
        
        # Try to parse motion if available
        motion_bearing = None
        motion_speed = None
        
        if len(parts) >= 8:
            motion = self.parse_motion(parts[6], parts[7])
            if motion:
                motion_bearing, motion_speed = motion
        
        return {
            'timestamp': timestamp,
            'latitude': lat,
            'longitude': lon,
            'vmax_kt': vmax,
            'mslp_hpa': mslp,
            'motion_bearing_deg': motion_bearing,
            'motion_speed_kt': motion_speed,
            'basin': 'IO'
        }
