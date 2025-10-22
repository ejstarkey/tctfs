"""
CIMSS 2dwind Parser - Fetch and parse wind radii from CIMSS ADT 2dwind files
Add this to: services/ingest/cimss_2dwind_fetch.py
"""
import logging
import re
import requests
from typing import Dict, Optional, List
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


class CIMSS2dWindService:
    """
    Fetch and parse wind radii from CIMSS ADT 2dwind.txt files.
    Example: https://tropic.ssec.wisc.edu/real-time/adt/04S.2dwind.txt
    """
    
    BASE_URL = "https://tropic.ssec.wisc.edu/real-time/adt"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TCTFS/1.0'
        })
    
    def fetch_2dwind(self, storm_id: str) -> Optional[str]:
        """
        Fetch 2dwind.txt file for a storm.
        
        Args:
            storm_id: Storm ID (e.g., "04S", "28W")
        
        Returns:
            Raw text content or None if not found
        """
        url = f"{self.BASE_URL}/{storm_id}.2dwind.txt"
        
        try:
            logger.info(f"Fetching 2dwind data: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"No 2dwind file for {storm_id}")
            else:
                logger.error(f"HTTP error fetching 2dwind: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching 2dwind for {storm_id}: {e}")
            return None
    
    def parse_2dwind(self, content: str) -> List[Dict]:
        """
        Parse 2dwind.txt content.
        
        Format is typically:
        YYYYMMDDHHMM  LAT  LON  VMAX  R34_NE  R34_SE  R34_SW  R34_NW  R50_NE  R50_SE  R50_SW  R50_NW  R64_NE  R64_SE  R64_SW  R64_NW
        
        Returns:
            List of dictionaries with timestamp and radii by quadrant
        """
        records = []
        
        for line in content.splitlines():
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#') or line.startswith('Date'):
                continue
            
            parts = line.split()
            
            if len(parts) < 15:
                continue
            
            try:
                # Parse timestamp - format is like "2025OCT22 130000"
                date_str = parts[0]  # "2025OCT22"
                time_str = parts[1]  # "130000"
                
                # Convert month abbreviation to number
                month_map = {
                    'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
                    'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
                    'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
                }
                
                # Extract year, month abbr, day
                year = date_str[:4]
                month_abbr = date_str[4:7].upper()
                day = date_str[7:9]
                
                month = month_map.get(month_abbr)
                if not month:
                    logger.warning(f"Unknown month: {month_abbr}")
                    continue
                
                # Build datetime string
                datetime_str = f"{year}{month}{day}{time_str}"
                timestamp = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                timestamp = pytz.utc.localize(timestamp)
                
                # Parse radii - skip the pipe separators
                # Format: date time lat lon vmax temp | R34x4 R50x4 R64x4 | motion
                parts_cleaned = [p for p in parts if p != '|']
                
                if len(parts_cleaned) < 18:
                    continue
                
                # Radii start at index 6 after removing pipes
                r34_ne = self._parse_radius(parts_cleaned[6])
                r34_se = self._parse_radius(parts_cleaned[7])
                r34_sw = self._parse_radius(parts_cleaned[8])
                r34_nw = self._parse_radius(parts_cleaned[9])
                
                r50_ne = self._parse_radius(parts_cleaned[10])
                r50_se = self._parse_radius(parts_cleaned[11])
                r50_sw = self._parse_radius(parts_cleaned[12])
                r50_nw = self._parse_radius(parts_cleaned[13])
                
                r64_ne = self._parse_radius(parts_cleaned[14])
                r64_se = self._parse_radius(parts_cleaned[15])
                r64_sw = self._parse_radius(parts_cleaned[16])
                r64_nw = self._parse_radius(parts_cleaned[17])
                
                record = {
                    'timestamp': timestamp,
                    'radii': {
                        'NE': {
                            'r34_nm': r34_ne,
                            'r50_nm': r50_ne,
                            'r64_nm': r64_ne
                        },
                        'SE': {
                            'r34_nm': r34_se,
                            'r50_nm': r50_se,
                            'r64_nm': r64_se
                        },
                        'SW': {
                            'r34_nm': r34_sw,
                            'r50_nm': r50_sw,
                            'r64_nm': r64_sw
                        },
                        'NW': {
                            'r34_nm': r34_nw,
                            'r50_nm': r50_nw,
                            'r64_nm': r64_nw
                        }
                    }
                }
                
                records.append(record)
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse 2dwind line: {line} - {e}")
                continue
        
        logger.info(f"Parsed {len(records)} radii records from 2dwind")
        return records
    
    def _parse_radius(self, value: str) -> Optional[float]:
        """Parse radius value, handling missing data."""
        try:
            val = float(value)
            return val if val > 0 else None
        except (ValueError, TypeError):
            return None
    
    def fetch_and_parse(self, storm_id: str) -> List[Dict]:
        """
        Convenience method to fetch and parse in one call.
        
        Args:
            storm_id: Storm ID
        
        Returns:
            List of parsed radii records
        """
        content = self.fetch_2dwind(storm_id)
        if not content:
            return []
        
        return self.parse_2dwind(content)


# Singleton
_cimss_2dwind_service = None

def get_cimss_2dwind_service() -> CIMSS2dWindService:
    """Get singleton instance."""
    global _cimss_2dwind_service
    if _cimss_2dwind_service is None:
        _cimss_2dwind_service = CIMSS2dWindService()
    return _cimss_2dwind_service
