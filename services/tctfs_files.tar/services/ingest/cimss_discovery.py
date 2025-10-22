"""
CIMSS Discovery Service - Poll CIMSS ADT page and extract active storm links.
This is the SOURCE OF TRUTH for discovering active tropical cyclones.
"""
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CIMSSDiscoveryService:
    """
    Service to discover active storms from CIMSS ADT page.
    Parses only the target <td height="100" width="200" valign="top" align="center"> block.
    """
    
    def __init__(self, base_url: str = "https://tropic.ssec.wisc.edu/real-time/adt/adt.html"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TCTFS/1.0 (Tropical Cyclone Forecast Service; contact@tctfs.example.com)'
        })
        self.last_etag = None
        self.last_modified = None
    
    def discover_storms(self, use_conditional_get: bool = True) -> List[Dict]:
        """
        Poll CIMSS ADT page and extract storm information.
        
        Args:
            use_conditional_get: Use ETag/Last-Modified for efficient polling
        
        Returns:
            List of storm dictionaries with keys: storm_id, name, basin, history_url
        """
        try:
            headers = {}
            if use_conditional_get:
                if self.last_etag:
                    headers['If-None-Match'] = self.last_etag
                if self.last_modified:
                    headers['If-Modified-Since'] = self.last_modified
            
            logger.info(f"Fetching CIMSS ADT page: {self.base_url}")
            response = self.session.get(self.base_url, headers=headers, timeout=30)
            
            # Handle 304 Not Modified
            if response.status_code == 304:
                logger.info("CIMSS page not modified (304), skipping parse")
                return []
            
            response.raise_for_status()
            
            # Update cache headers
            self.last_etag = response.headers.get('ETag')
            self.last_modified = response.headers.get('Last-Modified')
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'lxml')
            storms = self._parse_storm_bucket(soup)
            
            logger.info(f"Discovered {len(storms)} active storms from CIMSS")
            return storms
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch CIMSS page: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing CIMSS page: {e}", exc_info=True)
            return []
    
    def _parse_storm_bucket(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Parse the target <td height="100" width="200" valign="top" align="center"> block.
        Extract storm links and metadata.
        """
        storms = []
        
        # Find the target TD element
        target_td = soup.find('td', {
            'height': '100',
            'width': '200',
            'valign': 'top',
            'align': 'center'
        })
        
        if not target_td:
            logger.warning("Could not find target TD block in CIMSS page")
            return storms
        
        # Find all anchor tags within this TD
        links = target_td.find_all('a', href=True)
        
        for link in links:
            try:
                href = link['href']
                text = link.get_text(strip=True)
                
                # Look for history file links (*-list.txt)
                if '-list.txt' in href:
                    storm_info = self._extract_storm_info(href, text)
                    if storm_info:
                        storms.append(storm_info)
                        logger.debug(f"Found storm: {storm_info['storm_id']} - {storm_info.get('name', 'UNNAMED')}")
                        
            except Exception as e:
                logger.warning(f"Error parsing storm link: {e}")
                continue
        
        return storms
    
    def _extract_storm_info(self, href: str, link_text: str) -> Optional[Dict]:
        """
        Extract storm ID, basin, and name from history file link.
        
        Example URLs:
        - 28W-list.txt → storm_id=28W, basin=WP
        - 03S-list.txt → storm_id=03S, basin=SH (or IO)
        - 15E-list.txt → storm_id=15E, basin=EP
        """
        # Extract storm_id from filename (e.g., "28W" from "28W-list.txt")
        match = re.search(r'(\d{2}[A-Z])-list\.txt', href)
        if not match:
            return None
        
        storm_id = match.group(1)
        basin_code = storm_id[-1]  # Last character (W, E, S, L, etc.)
        
        # Map basin codes to full basin names
        basin_map = {
            'W': 'WP',  # Western Pacific
            'E': 'EP',  # Eastern Pacific
            'S': 'SH',  # Southern Hemisphere (generic)
            'L': 'AL',  # Atlantic
            'C': 'CP',  # Central Pacific
            'I': 'IO',  # Indian Ocean
            'A': 'IO',  # Also Indian Ocean sometimes
            'B': 'IO',  # Bay of Bengal
        }
        
        basin = basin_map.get(basin_code, basin_code)
        
        # Try to extract name from link text
        name = self._extract_name(link_text, storm_id)
        
        # Build full URL if relative
        if href.startswith('http'):
            history_url = href
        else:
            # Relative to CIMSS base
            base = self.base_url.rsplit('/', 1)[0]
            history_url = f"{base}/{href.lstrip('/')}"
        
        return {
            'storm_id': storm_id,
            'basin': basin,
            'name': name,
            'history_url': history_url,
            'discovered_at': datetime.utcnow().isoformat()
        }
    
    def _extract_name(self, link_text: str, storm_id: str) -> Optional[str]:
        """
        Try to extract storm name from link text.
        Examples: "28W YINXING", "03S UNNAMED", "15E KRISTY"
        """
        # Remove storm_id from text
        text = link_text.replace(storm_id, '').strip()
        
        # Clean up common separators
        text = re.sub(r'^[-:\s]+', '', text)
        text = re.sub(r'[-:\s]+$', '', text)
        
        # If text is "UNNAMED" or empty, return None
        if not text or text.upper() in ['UNNAMED', 'INVEST', 'TD']:
            return None
        
        return text.upper() if text else None


# Singleton instance for reuse
_discovery_service = None

def get_discovery_service() -> CIMSSDiscoveryService:
    """Get or create the singleton discovery service."""
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = CIMSSDiscoveryService()
    return _discovery_service
