"""
History Fetch Service - Download *-list.txt files from CIMSS.
"""
import logging
from typing import Optional, Dict
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class HistoryFetchService:
    """
    Service to fetch history files (*-list.txt) from CIMSS.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TCTFS/1.0 (Tropical Cyclone Forecast Service; contact@tctfs.example.com)'
        })
        self.cache = {}  # Store ETags/Last-Modified per URL
    
    def fetch_history_file(self, url: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Fetch a history file from CIMSS.
        
        Args:
            url: Full URL to *-list.txt file
            use_cache: Use conditional GET with ETag/Last-Modified
        
        Returns:
            Dict with keys: content (str), last_modified (str), etag (str), fetched_at (datetime)
            Returns None if file not modified or fetch failed
        """
        try:
            headers = {}
            
            if use_cache and url in self.cache:
                cache_entry = self.cache[url]
                if cache_entry.get('etag'):
                    headers['If-None-Match'] = cache_entry['etag']
                if cache_entry.get('last_modified'):
                    headers['If-Modified-Since'] = cache_entry['last_modified']
            
            logger.info(f"Fetching history file: {url}")
            response = self.session.get(url, headers=headers, timeout=30)
            
            # Handle 304 Not Modified
            if response.status_code == 304:
                logger.info(f"History file not modified: {url}")
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
                'etag': etag,
                'last_modified': last_modified,
                'fetched_at': datetime.utcnow(),
                'url': url
            }
            
            logger.info(f"Successfully fetched history file: {url} ({len(response.text)} bytes)")
            return result
            
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"History file not found: {url}")
            else:
                logger.error(f"HTTP error fetching history file {url}: {e}")
            return None
        except requests.RequestException as e:
            logger.error(f"Failed to fetch history file {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching history file {url}: {e}", exc_info=True)
            return None


# Singleton instance
_history_fetch_service = None

def get_history_fetch_service() -> HistoryFetchService:
    """Get or create the singleton history fetch service."""
    global _history_fetch_service
    if _history_fetch_service is None:
        _history_fetch_service = HistoryFetchService()
    return _history_fetch_service
