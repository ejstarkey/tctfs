"""
ADT List Parser - Parse *-list.txt files from CIMSS ADT.
"""
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


class ADTListParser:
    """Parser for ADT *-list.txt files."""
    
    def parse_file(self, content: str) -> List[Dict]:
        """Parse ADT list file."""
        advisories = []
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip header lines and empty lines
            if not line:
                continue
            if 'ADT' in line and 'LIST' in line:
                continue
            if '=====' in line:
                continue
            if 'Time' in line or 'Date' in line or 'UTC' in line:
                continue
            
            try:
                advisory = self.parse_line(line)
                if advisory:
                    advisories.append(advisory)
            except Exception as e:
                logger.debug(f"Line {line_num}: {e}")
        
        logger.info(f"Parsed {len(advisories)} records from ADT list")
        return advisories
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single ADT data line.
        
        Example line:
        2025OCT18 034000  2.0 1004.6  30.0  2.0 2.0 2.0  NO LIMIT  OFF  OFF  OFF  OFF  -5.96 -37.81  CRVBND   N/A    N/A   14.25 -126.75  ARCHER   HIM-8 23.2
        
        Columns we need:
        0: Date (2025OCT18)
        1: Time (034000)
        3: MSLP (1004.6)
        4: Vmax (30.0)
        -5: Lat (14.25)
        -4: Lon (-126.75)
        """
        parts = line.split()
        
        if len(parts) < 20:  # ADT lines have many columns
            return None
        
        try:
            # Parse date/time (columns 0 and 1)
            date_str = parts[0]  # 2025OCT18
            time_str = parts[1]  # 034000
            
            dt_str = f"{date_str} {time_str}"
            timestamp = datetime.strptime(dt_str, '%Y%b%d %H%M%S')
            timestamp = pytz.utc.localize(timestamp)
            
            # Parse pressure and winds (columns 3 and 4)
            pressure = float(parts[3])  # MSLP
            winds = float(parts[4])     # Vmax
            
            # Parse lat/lon from the END of the line
            # They are typically at positions -5 and -4
            lat = float(parts[-5])
            lon = float(parts[-4])
            
            # Validate coordinates
            if not (-90 <= lat <= 90):
                return None
            if not (-180 <= lon <= 180):
                return None
            
            return {
                'timestamp': timestamp,
                'latitude': lat,
                'longitude': lon,
                'mslp_hpa': pressure,
                'vmax_kt': winds
            }
            
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None


def get_adt_list_parser():
    return ADTListParser()
