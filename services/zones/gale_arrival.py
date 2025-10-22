"""
Gale Arrival Service - Calculate Time of First Intersection (TOFI) for coastal segments.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import nearest_points
import numpy as np

logger = logging.getLogger(__name__)


class GaleArrivalService:
    """
    Calculate when gale-force winds (34kt+) will first reach coastal segments.
    """
    
    def calculate_tofi(
        self,
        coastline: LineString,
        forecast_track: List[Dict],
        wind_threshold_kt: int = 34
    ) -> Dict:
        """
        Calculate Time of First Intersection for a coastline segment.
        
        Args:
            coastline: Coastal LineString geometry
            forecast_track: List of forecast points with lat, lon, valid_at, vmax_kt, radii
            wind_threshold_kt: Wind threshold (34, 50, or 64 kt)
        
        Returns:
            Dictionary with TOFI information: {tofi_utc, distance_km, forecast_point_index}
        """
        min_tofi = None
        min_distance = float('inf')
        min_point_idx = None
        
        for idx, fpoint in enumerate(forecast_track):
            # Get wind radius for this threshold
            radii_nm = self._get_wind_radius(fpoint, wind_threshold_kt)
            if not radii_nm:
                continue
            
            # Convert radius to degrees (rough approximation: 1nm ≈ 0.0167°)
            radius_deg = radii_nm * 0.0167
            
            # Create wind field circle
            center = Point(fpoint['longitude'], fpoint['latitude'])
            wind_circle = center.buffer(radius_deg)
            
            # Check if wind circle intersects coastline
            if wind_circle.intersects(coastline):
                # Calculate closest distance to coast
                nearest_pt = nearest_points(center, coastline)[1]
                distance_deg = center.distance(nearest_pt)
                distance_km = distance_deg * 111  # 1 degree ≈ 111 km
                
                # Update minimum TOFI
                if min_tofi is None or fpoint['valid_at'] < min_tofi:
                    min_tofi = fpoint['valid_at']
                    min_distance = distance_km
                    min_point_idx = idx
        
        if min_tofi:
            return {
                'tofi_utc': min_tofi,
                'distance_km': min_distance,
                'forecast_point_index': min_point_idx,
                'wind_threshold_kt': wind_threshold_kt,
            }
        
        return None
    
    def _get_wind_radius(self, forecast_point: Dict, threshold_kt: int) -> Optional[float]:
        """
        Get wind radius for a specific threshold from forecast point.
        
        Args:
            forecast_point: Forecast point dictionary
            threshold_kt: Wind threshold (34, 50, or 64)
        
        Returns:
            Maximum radius across all quadrants in nautical miles, or None
        """
        radii = forecast_point.get('radii')
        if not radii:
            # No radii data, try to infer from intensity
            vmax = forecast_point.get('vmax_kt')
            if not vmax or vmax < threshold_kt:
                return None
            
            # Simple fallback: approximate radius based on intensity
            # This is very rough - production should use radii_inference service
            if threshold_kt == 34:
                return vmax * 0.8
            elif threshold_kt == 50:
                return vmax * 0.5
            elif threshold_kt == 64:
                return vmax * 0.3
            return None
        
        # Get maximum radius across quadrants
        threshold_key = f'r{threshold_kt}'
        max_radius = 0
        
        for quadrant in ['NE', 'SE', 'SW', 'NW']:
            if quadrant in radii:
                radius = radii[quadrant].get(threshold_key)
                if radius and radius > max_radius:
                    max_radius = radius
        
        return max_radius if max_radius > 0 else None
    
    def adjust_tofi_for_motion(
        self,
        tofi: datetime,
        forecast_point: Dict,
        forward_speed_kt: Optional[float] = None
    ) -> datetime:
        """
        Adjust TOFI based on storm forward speed and acceleration.
        
        Args:
            tofi: Initial TOFI estimate
            forecast_point: Forecast point at TOFI
            forward_speed_kt: Storm forward speed in knots
        
        Returns:
            Adjusted TOFI datetime
        """
        if not forward_speed_kt:
            forward_speed_kt = forecast_point.get('motion_speed_kt', 10)  # Default 10kt
        
        # Faster storms arrive sooner, slower storms arrive later
        # Adjustment factor: ±20% based on speed relative to climatology (15kt)
        speed_ratio = forward_speed_kt / 15.0
        adjustment_hours = (1.0 - speed_ratio) * 3  # Max ±3 hours adjustment
        
        adjusted_tofi = tofi + timedelta(hours=adjustment_hours)
        
        return adjusted_tofi
    
    def classify_arrival_window(self, tofi: datetime, current_time: datetime) -> str:
        """
        Classify TOFI into warning/watch categories.
        
        Args:
            tofi: Time of first intersection
            current_time: Current time
        
        Returns:
            'warning' (≤24h), 'watch' (24-48h), or 'none' (>48h)
        """
        hours_until = (tofi - current_time).total_seconds() / 3600
        
        if hours_until <= 24:
            return 'warning'
        elif hours_until <= 48:
            return 'watch'
        else:
            return 'none'


# Singleton instance
_gale_arrival_service = None

def get_gale_arrival_service() -> GaleArrivalService:
    """Get or create the singleton gale arrival service."""
    global _gale_arrival_service
    if _gale_arrival_service is None:
        _gale_arrival_service = GaleArrivalService()
    return _gale_arrival_service
