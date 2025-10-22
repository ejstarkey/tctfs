"""
CIMSS Discovery Service - Poll CIMSS ADT page and extract ALL active storm links.
"""
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CIMSSDiscoveryService:
    """Service to discover active storms from CIMSS ADT page."""
    
    def __init__(self, base_url: str = "https://tropic.ssec.wisc.edu/real-time/adt/"):
        self.base_url = base_url
        self.main_page_url = base_url + "adt.html"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TCTFS/1.0 (Tropical Cyclone Forecast Service)'
        })
        self.last_etag = None
        self.last_modified = None
    
    def discover_storms(self, use_conditional_get: bool = True) -> List[Dict]:
        """Poll CIMSS ADT page and extract ALL storm information."""
        try:
            headers = {}
            if use_conditional_get:
                if self.last_etag:
                    headers['If-None-Match'] = self.last_etag
                if self.last_modified:
                    headers['If-Modified-Since'] = self.last_modified
            
            logger.info(f"Fetching CIMSS ADT page: {self.main_page_url}")
            response = self.session.get(self.main_page_url, headers=headers, timeout=30)
            
            if response.status_code == 304:
                logger.info("CIMSS page not modified (304)")
                return []
            
            response.raise_for_status()
            
            self.last_etag = response.headers.get('ETag')
            self.last_modified = response.headers.get('Last-Modified')
            
            soup = BeautifulSoup(response.text, 'lxml')
            storms = self._parse_all_storms(soup)
            
            logger.info(f"Discovered {len(storms)} active storms")
            return storms
            
        except Exception as e:
            logger.error(f"Error discovering storms: {e}", exc_info=True)
            return []
    
    def _parse_all_storms(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse ALL storm links on the entire page, not just one TD."""
        storms = []
        
        # Find ALL links on the page that point to storm detail pages (odt*.html)
        all_links = soup.find_all('a', href=True)
        
        seen_storm_ids = set()
        
        for link in all_links:
            try:
                href = link['href']
                text = link.get_text(strip=True)
                
                # Look for storm detail pages (e.g., odt30W.html, odt25S.html, etc.)
                if href.startswith('odt') and href.endswith('.html'):
                    # Extract storm ID from filename (e.g., odt30W.html -> 30W)
                    match = re.search(r'odt(\d{2}[A-Z])\.html', href)
                    if match:
                        storm_id = match.group(1)
                        
                        # Skip duplicates
                        if storm_id in seen_storm_ids:
                            continue
                        
                        seen_storm_ids.add(storm_id)
                        
                        storm_info = self._fetch_storm_details(href, text)
                        if storm_info:
                            storms.append(storm_info)
                            logger.info(f"Found: {storm_info['storm_id']} - {storm_info.get('name', 'UNNAMED')}")
                        
            except Exception as e:
                logger.warning(f"Error parsing link: {e}")
                continue
        
        return storms
    
    def _fetch_storm_details(self, storm_page_href: str, storm_name: str) -> Optional[Dict]:
        """Fetch storm detail page to get history file and satellite image."""
        try:
            storm_page_url = self.base_url + storm_page_href
            
            logger.debug(f"Fetching {storm_page_url}")
            response = self.session.get(storm_page_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find history file link
            history_link = soup.find('a', href=re.compile(r'.*-list\.txt'))
            if not history_link:
                logger.warning(f"No history file found on {storm_page_url}")
                return None
            
            history_href = history_link['href']
            history_url = self.base_url + history_href if not history_href.startswith('http') else history_href
            
            # Extract storm_id
            match = re.search(r'(\d{2}[A-Z])-list\.txt', history_href)
            if not match:
                return None
            
            storm_id = match.group(1)
            
            # Get satellite image
            satellite_image_url = None
            img_link = soup.find('a', href=re.compile(rf'{storm_id}\.GIF$'))
            if img_link:
                img_href = img_link['href']
                satellite_image_url = self.base_url + img_href if not img_href.startswith('http') else img_href
            else:
                img_tag = soup.find('img', src=re.compile(rf'{storm_id}'))
                if img_tag:
                    img_src = img_tag['src']
                    satellite_image_url = self.base_url + img_src if not img_src.startswith('http') else img_src
            
            basin_code = storm_id[-1]
            basin_map = {
                'W': 'WP', 'E': 'EP', 'S': 'SH', 'L': 'AL',
                'C': 'CP', 'I': 'IO', 'A': 'IO', 'B': 'IO',
            }
            basin = basin_map.get(basin_code, basin_code)
            
            name = self._extract_name(storm_name, storm_id)
            
            return {
                'storm_id': storm_id,
                'basin': basin,
                'name': name,
                'history_url': history_url,
                'satellite_image_url': satellite_image_url,
                'discovered_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching storm details: {e}")
            return None
    
    def _extract_name(self, storm_text: str, storm_id: str) -> Optional[str]:
        """Extract storm name from text."""
        text = storm_text
        for prefix in ['Tropical Storm', 'Hurricane', 'Typhoon', 'Cyclone', 'Tropical Depression']:
            text = text.replace(prefix, '').strip()
        
        text = text.replace(storm_id, '').strip()
        text = re.sub(r'^[-:\s]+', '', text)
        text = re.sub(r'[-:\s]+$', '', text)
        
        if not text or text.upper() in ['UNNAMED', 'INVEST', 'TD', '']:
            return None
        
        return text.upper() if text else None


_discovery_service = None

def get_discovery_service() -> CIMSSDiscoveryService:
    """Get singleton discovery service."""
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = CIMSSDiscoveryService()
    return _discovery_service
