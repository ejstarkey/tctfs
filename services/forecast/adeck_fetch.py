"""
A-Deck Fetch Service - Download forecast files from UCAR.
"""
import logging
from typing import Optional, Dict
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class AdeckFetchService:
    """
    Service to fetch A-Deck files from UCAR repository.
    Files are named: a<basin><num><year>.dat
    Example: ash032024.dat (Southern Hemisphere, storm 03, year 2024)
    """
    
    def __init__(self, base_url: str = "http://hurricanes.ral.ucar.edu/repository/data/adecks_open/"):
        self.base_url = base_url.rstrip('/') + '/'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TCTFS/1.0 (Tropical Cyclone Forecast Service; contact@tctfs.example.com)'
        })
        self.cache = {}
    
    def fetch_adeck(self, basin: str, storm_num: int, year: int, use_cache: bool = True) -> Optional[Dict]:
        """
        Fetch an A-Deck file from UCAR.
        
        Args:
            basin: Basin code (WP, SH, EP, IO, AL, CP)
            storm_num: Storm number (1-99)
            year: Year (4 digits)
            use_cache: Use conditional GET
        
        Returns:
            Dict with keys: content (str), filename (str), fetched_at (datetime)
            Returns None if file not found or not modified
        """
        # Build filename: a<basin><num><year>.dat
        # Basin codes need to be lowercase single letter
        basin_map = {
            'WP': 'w',
            'EP': 'e', 
            'AL': 'l',  # Atlantic
            'CP': 'c',
            'SH': 's',
            'IO': 'i'
        }
        
        basin_code = basin_map.get(basin, basin.lower()[0])
        filename = f"a{basin_code}{storm_num:02d}{year}.dat"
        url = f"{self.base_url}{filename}"
        
        try:
            headers = {}
            
            if use_cache and url in self.cache:
                cache_entry = self.cache[url]
                if cache_entry.get('etag'):
                    headers['If-None-Match'] = cache_entry['etag']
                if cache_entry.get('last_modified'):
                    headers['If-Modified-Since'] = cache_entry['last_modified']
            
            logger.info(f"Fetching A-Deck file: {url}")
            response = self.session.get(url, headers=headers, timeout=30)
            
            # Handle 304 Not Modified
            if response.status_code == 304:
                logger.info(f"A-Deck file not modified: {filename}")
                return None
            
            response.raise_for_status()
            
            # Extract cache headers
            etag = response.headers.get('ETag')
            last_modified = response.headers.get('Last-Modified')
            
            # Update cache
            self.cache[url] = {
                'etag': etag,
                'last_modified': last_modified,
                'fetched_at': datetime.utcnow()
            }
            
            result = {
                'content': response.text,
                'filename': filename,
                'url': url,
                'etag': etag,
                'last_modified': last_modified,
                'fetched_at': datetime.utcnow()
            }
            
            logger.info(f"Successfully fetched A-Deck file: {filename} ({len(response.text)} bytes)")
            return result
            
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"A-Deck file not found: {filename}")
            else:
                logger.error(f"HTTP error fetching A-Deck {filename}: {e}")
            return None
        except requests.RequestException as e:
            logger.error(f"Failed to fetch A-Deck {filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching A-Deck {filename}: {e}", exc_info=True)
            return None


# Singleton instance
_adeck_fetch_service = None

def get_adeck_fetch_service() -> AdeckFetchService:
    """Get or create the singleton A-Deck fetch service."""
    global _adeck_fetch_service
    if _adeck_fetch_service is None:
        _adeck_fetch_service = AdeckFetchService()
    return _adeck_fetch_service
