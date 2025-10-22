"""
Coast Source Service - Handle coastline and community vectors for zone generation.
"""
import logging
from typing import List, Dict, Optional
from shapely.geometry import LineString, Point, MultiLineString
from shapely.ops import unary_union
import geopandas as gpd

logger = logging.getLogger(__name__)


class CoastSourceService:
    """
    Manages coastline and community location data for watch/warning zone generation.
    """
    
    def __init__(self, coastline_path: Optional[str] = None):
        """
        Initialize coast source service.
        
        Args:
            coastline_path: Path to coastline shapefile/geojson (optional)
        """
        self.coastline_path = coastline_path
        self.coastlines = None
        self.communities = {}
        
        if coastline_path:
            self._load_coastlines()
    
    def _load_coastlines(self):
        """Load coastline data from file."""
        try:
            self.coastlines = gpd.read_file(self.coastline_path)
            logger.info(f"Loaded coastlines from {self.coastline_path}")
        except Exception as e:
            logger.error(f"Failed to load coastlines: {e}")
            self.coastlines = None
    
    def get_coastline_segments(self, basin: str, bbox: Optional[tuple] = None) -> List[LineString]:
        """
        Get coastline segments for a basin, optionally filtered by bounding box.
        
        Args:
            basin: Basin code (WP, EP, SH, etc.)
            bbox: Optional (min_lon, min_lat, max_lon, max_lat)
        
        Returns:
            List of LineString geometries representing coastline
        """
        if self.coastlines is None:
            logger.warning("No coastline data loaded, using simplified placeholder")
            return self._get_placeholder_coastlines(basin)
        
        # Filter by basin if column exists
        gdf = self.coastlines
        if 'basin' in gdf.columns:
            gdf = gdf[gdf['basin'] == basin]
        
        # Filter by bounding box if provided
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            gdf = gdf.cx[min_lon:max_lon, min_lat:max_lat]
        
        # Extract geometries
        segments = []
        for geom in gdf.geometry:
            if geom.geom_type == 'LineString':
                segments.append(geom)
            elif geom.geom_type == 'MultiLineString':
                segments.extend(list(geom.geoms))
        
        return segments
    
    def _get_placeholder_coastlines(self, basin: str) -> List[LineString]:
        """
        Get simplified placeholder coastlines when real data not available.
        
        Args:
            basin: Basin code
        
        Returns:
            List of simplified coastline segments
        """
        # Very simplified coastlines for major basins
        # In production, use real high-resolution coastline data
        placeholders = {
            'WP': [
                # Philippines
                LineString([(120, 10), (125, 18), (122, 20), (120, 18)]),
                # Japan
                LineString([(130, 30), (140, 35), (142, 40), (140, 42)]),
                # China coast
                LineString([(110, 20), (120, 25), (122, 30)]),
            ],
            'EP': [
                # Mexico west coast
                LineString([(-115, 20), (-110, 25), (-105, 30)]),
            ],
            'AL': [
                # US East Coast
                LineString([(-80, 25), (-75, 35), (-70, 40)]),
                # Caribbean
                LineString([(-85, 15), (-70, 20), (-60, 18)]),
            ],
        }
        
        return placeholders.get(basin, [])
    
    def get_nearby_communities(self, center_lat: float, center_lon: float, radius_km: float = 500) -> List[Dict]:
        """
        Get communities within a radius of a point.
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_km: Search radius in kilometers
        
        Returns:
            List of community dictionaries with name, lat, lon
        """
        # Placeholder - in production, query from database or GeoNames
        # For now, return empty list
        return []
    
    def simplify_coastline(self, coastline: LineString, tolerance: float = 0.01) -> LineString:
        """
        Simplify coastline geometry using Douglas-Peucker algorithm.
        
        Args:
            coastline: LineString geometry
            tolerance: Simplification tolerance (degrees)
        
        Returns:
            Simplified LineString
        """
        return coastline.simplify(tolerance, preserve_topology=True)


# Singleton instance
_coast_source_service = None

def get_coast_source_service() -> CoastSourceService:
    """Get or create the singleton coast source service."""
    global _coast_source_service
    if _coast_source_service is None:
        _coast_source_service = CoastSourceService()
    return _coast_source_service
