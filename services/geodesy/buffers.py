"""
Buffers Service - Shapely and PostGIS geometry helpers.
"""
import logging
from typing import Union
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
from shapely.ops import transform
import pyproj
from functools import partial

logger = logging.getLogger(__name__)


class BuffersService:
    """
    Helper methods for creating buffers and manipulating geometries.
    """
    
    def buffer_point_km(self, lat: float, lon: float, radius_km: float, segments: int = 32) -> Polygon:
        """
        Create a circular buffer around a point with radius in kilometers.
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            radius_km: Buffer radius in kilometers
            segments: Number of segments for circle approximation
        
        Returns:
            Polygon representing buffered area
        """
        # Create point in WGS84
        point = Point(lon, lat)
        
        # Project to local UTM for accurate metric buffer
        # Determine UTM zone from longitude
        utm_zone = int((lon + 180) / 6) + 1
        hemisphere = 'north' if lat >= 0 else 'south'
        
        utm_crs = pyproj.CRS(f"+proj=utm +zone={utm_zone} +{hemisphere} +datum=WGS84")
        wgs84 = pyproj.CRS("EPSG:4326")
        
        # Transform to UTM
        project_to_utm = pyproj.Transformer.from_crs(wgs84, utm_crs, always_xy=True).transform
        point_utm = transform(project_to_utm, point)
        
        # Buffer in meters
        buffered_utm = point_utm.buffer(radius_km * 1000.0, resolution=segments)
        
        # Transform back to WGS84
        project_to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84, always_xy=True).transform
        buffered_wgs84 = transform(project_to_wgs84, buffered_utm)
        
        return buffered_wgs84
    
    def buffer_linestring_km(self, linestring: LineString, radius_km: float) -> Polygon:
        """
        Create buffer around a LineString with radius in kilometers.
        
        Args:
            linestring: LineString geometry in WGS84
            radius_km: Buffer radius in kilometers
        
        Returns:
            Buffered polygon
        """
        # Get approximate centroid for UTM zone calculation
        centroid = linestring.centroid
        lon, lat = centroid.x, centroid.y
        
        # Determine UTM zone
        utm_zone = int((lon + 180) / 6) + 1
        hemisphere = 'north' if lat >= 0 else 'south'
        
        utm_crs = pyproj.CRS(f"+proj=utm +zone={utm_zone} +{hemisphere} +datum=WGS84")
        wgs84 = pyproj.CRS("EPSG:4326")
        
        # Transform to UTM
        project_to_utm = pyproj.Transformer.from_crs(wgs84, utm_crs, always_xy=True).transform
        line_utm = transform(project_to_utm, linestring)
        
        # Buffer in meters
        buffered_utm = line_utm.buffer(radius_km * 1000.0)
        
        # Transform back to WGS84
        project_to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84, always_xy=True).transform
        buffered_wgs84 = transform(project_to_wgs84, buffered_utm)
        
        return buffered_wgs84
    
    def simplify_geometry(self, geom: Union[Polygon, MultiPolygon], tolerance_deg: float = 0.01) -> Union[Polygon, MultiPolygon]:
        """
        Simplify geometry using Douglas-Peucker algorithm.
        
        Args:
            geom: Polygon or MultiPolygon
            tolerance_deg: Simplification tolerance in degrees
        
        Returns:
            Simplified geometry
        """
        return geom.simplify(tolerance_deg, preserve_topology=True)
    
    def union_geometries(self, geometries: list) -> Union[Polygon, MultiPolygon]:
        """
        Union multiple geometries into one.
        
        Args:
            geometries: List of Polygon/MultiPolygon geometries
        
        Returns:
            Merged geometry
        """
        from shapely.ops import unary_union
        return unary_union(geometries)
    
    def intersection(self, geom1, geom2):
        """
        Calculate intersection of two geometries.
        
        Args:
            geom1: First geometry
            geom2: Second geometry
        
        Returns:
            Intersection geometry (may be empty)
        """
        return geom1.intersection(geom2)
    
    def contains_point(self, polygon: Polygon, lat: float, lon: float) -> bool:
        """
        Check if polygon contains a point.
        
        Args:
            polygon: Polygon geometry
            lat: Point latitude
            lon: Point longitude
        
        Returns:
            True if point is inside polygon
        """
        point = Point(lon, lat)
        return polygon.contains(point)
    
    def distance_to_geometry(self, lat: float, lon: float, geom) -> float:
        """
        Calculate distance from point to geometry (in kilometers).
        
        Args:
            lat: Point latitude
            lon: Point longitude
            geom: Target geometry
        
        Returns:
            Distance in kilometers (approximate)
        """
        point = Point(lon, lat)
        
        # Calculate distance in degrees
        dist_deg = point.distance(geom)
        
        # Convert to kilometers (rough: 1 degree ≈ 111 km at equator)
        dist_km = dist_deg * 111.0
        
        return dist_km
    
    def clip_to_bbox(self, geom, min_lon: float, min_lat: float, max_lon: float, max_lat: float):
        """
        Clip geometry to bounding box.
        
        Args:
            geom: Geometry to clip
            min_lon, min_lat: Southwest corner
            max_lon, max_lat: Northeast corner
        
        Returns:
            Clipped geometry
        """
        from shapely.geometry import box
        bbox = box(min_lon, min_lat, max_lon, max_lat)
        return geom.intersection(bbox)


# Singleton instance
_buffers_service = None

def get_buffers_service() -> BuffersService:
    """Get or create the singleton buffers service."""
    global _buffers_service
    if _buffers_service is None:
        _buffers_service = BuffersService()
    return _buffers_service
