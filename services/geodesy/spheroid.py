"""
Spheroid Service - Great-circle distance and bearing calculations.
"""
import logging
import math
from typing import Tuple
from geographiclib.geodesic import Geodesic

logger = logging.getLogger(__name__)


class SpheroidService:
    """
    Perform geodesic calculations on Earth's surface.
    Uses WGS84 ellipsoid for accurate distance/bearing computations.
    """
    
    def __init__(self):
        """Initialize with WGS84 geodesic."""
        self.geod = Geodesic.WGS84
    
    def distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate great-circle distance between two points.
        
        Args:
            lat1, lon1: First point coordinates (degrees)
            lat2, lon2: Second point coordinates (degrees)
        
        Returns:
            Distance in kilometers
        """
        result = self.geod.Inverse(lat1, lon1, lat2, lon2)
        return result['s12'] / 1000.0  # Convert meters to kilometers
    
    def bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate initial bearing from point 1 to point 2.
        
        Args:
            lat1, lon1: Starting point (degrees)
            lat2, lon2: Ending point (degrees)
        
        Returns:
            Initial bearing in degrees (0-360)
        """
        result = self.geod.Inverse(lat1, lon1, lat2, lon2)
        bearing = result['azi1']
        
        # Normalize to 0-360
        if bearing < 0:
            bearing += 360
        
        return bearing
    
    def destination(self, lat: float, lon: float, bearing: float, distance_km: float) -> Tuple[float, float]:
        """
        Calculate destination point given start, bearing, and distance.
        
        Args:
            lat, lon: Starting point (degrees)
            bearing: Initial bearing (degrees, 0-360)
            distance_km: Distance to travel (kilometers)
        
        Returns:
            Tuple of (dest_lat, dest_lon) in degrees
        """
        distance_m = distance_km * 1000.0
        result = self.geod.Direct(lat, lon, bearing, distance_m)
        
        return (result['lat2'], result['lon2'])
    
    def intermediate_point(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
        fraction: float
    ) -> Tuple[float, float]:
        """
        Calculate intermediate point along great circle.
        
        Args:
            lat1, lon1: Start point (degrees)
            lat2, lon2: End point (degrees)
            fraction: Fraction of distance (0.0 to 1.0)
        
        Returns:
            Tuple of (lat, lon) at fraction of distance
        """
        line = self.geod.InverseLine(lat1, lon1, lat2, lon2)
        distance = line.s13 * fraction
        
        pos = line.Position(distance)
        return (pos['lat2'], pos['lon2'])
    
    def spherical_mean(self, points: list) -> Tuple[float, float]:
        """
        Calculate spherical mean of multiple points.
        Properly handles points near poles and date line.
        
        Args:
            points: List of (lat, lon) tuples
        
        Returns:
            Tuple of (mean_lat, mean_lon)
        """
        if not points:
            return None
        
        if len(points) == 1:
            return points[0]
        
        # Convert to Cartesian coordinates
        x_sum = 0
        y_sum = 0
        z_sum = 0
        
        for lat, lon in points:
            lat_rad = math.radians(lat)
            lon_rad = math.radians(lon)
            
            x_sum += math.cos(lat_rad) * math.cos(lon_rad)
            y_sum += math.cos(lat_rad) * math.sin(lon_rad)
            z_sum += math.sin(lat_rad)
        
        # Average
        n = len(points)
        x_avg = x_sum / n
        y_avg = y_sum / n
        z_avg = z_sum / n
        
        # Convert back to spherical
        lon_avg = math.atan2(y_avg, x_avg)
        hyp = math.sqrt(x_avg * x_avg + y_avg * y_avg)
        lat_avg = math.atan2(z_avg, hyp)
        
        return (math.degrees(lat_avg), math.degrees(lon_avg))
    
    def cross_track_distance(
        self,
        lat: float, lon: float,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Calculate perpendicular distance from point to great circle.
        
        Args:
            lat, lon: Point coordinates
            lat1, lon1: Start of great circle
            lat2, lon2: End of great circle
        
        Returns:
            Cross-track distance in kilometers (positive = right, negative = left)
        """
        # Distance from point to start
        d13 = self.distance(lat1, lon1, lat, lon)
        
        # Bearing from start to point
        brng13 = math.radians(self.bearing(lat1, lon1, lat, lon))
        
        # Bearing from start to end
        brng12 = math.radians(self.bearing(lat1, lon1, lat2, lon2))
        
        # Cross-track distance
        R = 6371.0  # Earth radius in km
        dxt = math.asin(math.sin(d13/R) * math.sin(brng13 - brng12)) * R
        
        return dxt


# Singleton instance
_spheroid_service = None

def get_spheroid_service() -> SpheroidService:
    """Get or create the singleton spheroid service."""
    global _spheroid_service
    if _spheroid_service is None:
        _spheroid_service = SpheroidService()
    return _spheroid_service
