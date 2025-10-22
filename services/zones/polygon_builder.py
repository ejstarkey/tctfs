"""
Polygon Builder Service - Build, dissolve, and smooth watch/warning polygons.
"""
import logging
from typing import List, Dict
from datetime import datetime
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
from shapely.ops import unary_union, cascaded_union
import numpy as np

logger = logging.getLogger(__name__)


class PolygonBuilderService:
    """
    Build watch/warning zone polygons from coastal segments and TOFI calculations.
    """
    
    def build_zone_polygon(
        self,
        affected_segments: List[LineString],
        buffer_km: float = 50,
        simplify_tolerance: float = 0.01
    ) -> Polygon:
        """
        Build a zone polygon from affected coastal segments.
        
        Args:
            affected_segments: List of coastal LineString segments
            buffer_km: Buffer distance in kilometers
            simplify_tolerance: Tolerance for polygon simplification (degrees)
        
        Returns:
            Merged and simplified Polygon
        """
        if not affected_segments:
            return None
        
        # Convert buffer from km to degrees (rough: 1° ≈ 111 km)
        buffer_deg = buffer_km / 111.0
        
        # Buffer each segment
        buffered_segments = [seg.buffer(buffer_deg) for seg in affected_segments]
        
        # Merge all buffered segments
        merged = unary_union(buffered_segments)
        
        # Simplify using Douglas-Peucker
        simplified = merged.simplify(simplify_tolerance, preserve_topology=True)
        
        # Ensure we have a Polygon or MultiPolygon
        if simplified.geom_type == 'Polygon':
            return simplified
        elif simplified.geom_type == 'MultiPolygon':
            # Return as MultiPolygon
            return simplified
        else:
            logger.warning(f"Unexpected geometry type after merge: {simplified.geom_type}")
            return None
    
    def dissolve_small_gaps(
        self,
        polygon: Polygon,
        max_gap_km: float = 100
    ) -> Polygon:
        """
        Dissolve small gaps between polygon parts.
        
        Args:
            polygon: Input polygon
            max_gap_km: Maximum gap size to dissolve (km)
        
        Returns:
            Polygon with gaps dissolved
        """
        # Convert gap size from km to degrees
        gap_deg = max_gap_km / 111.0
        
        # Apply small buffer to close gaps, then remove buffer
        closed = polygon.buffer(gap_deg).buffer(-gap_deg)
        
        return closed
    
    def smooth_edges(
        self,
        polygon: Polygon,
        smoothing_iterations: int = 2
    ) -> Polygon:
        """
        Smooth polygon edges using Chaikin's algorithm.
        
        Args:
            polygon: Input polygon
            smoothing_iterations: Number of smoothing passes
        
        Returns:
            Smoothed polygon
        """
        if polygon.geom_type == 'MultiPolygon':
            # Smooth each part separately
            smoothed_parts = [self._smooth_polygon(p, smoothing_iterations) for p in polygon.geoms]
            return MultiPolygon(smoothed_parts)
        else:
            return self._smooth_polygon(polygon, smoothing_iterations)
    
    def _smooth_polygon(self, polygon: Polygon, iterations: int) -> Polygon:
        """Apply Chaikin smoothing to a single polygon."""
        coords = list(polygon.exterior.coords)
        
        for _ in range(iterations):
            coords = self._chaikin_smooth(coords)
        
        # Recreate polygon with smoothed coordinates
        return Polygon(coords)
    
    def _chaikin_smooth(self, coords: List[tuple]) -> List[tuple]:
        """
        Apply one iteration of Chaikin's corner cutting algorithm.
        
        Args:
            coords: List of (x, y) coordinate tuples
        
        Returns:
            Smoothed coordinate list
        """
        smoothed = []
        
        for i in range(len(coords) - 1):
            p1 = np.array(coords[i])
            p2 = np.array(coords[i + 1])
            
            # Quarter point between p1 and p2
            q = p1 * 0.75 + p2 * 0.25
            # Three-quarter point
            r = p1 * 0.25 + p2 * 0.75
            
            smoothed.append(tuple(q))
            smoothed.append(tuple(r))
        
        # Close the polygon
        smoothed.append(smoothed[0])
        
        return smoothed
    
    def split_by_threshold(
        self,
        tofi_data: List[Dict],
        current_time: datetime
    ) -> Dict[str, List[Dict]]:
        """
        Split TOFI data into watch and warning categories.
        
        Args:
            tofi_data: List of TOFI dictionaries with tofi_utc and coastal segment
            current_time: Current time for threshold calculation
        
        Returns:
            Dictionary with 'watch' and 'warning' keys, each containing list of affected segments
        """
        warnings = []
        watches = []
        
        for tofi_entry in tofi_data:
            tofi = tofi_entry['tofi_utc']
            hours_until = (tofi - current_time).total_seconds() / 3600
            
            if hours_until <= 24:
                warnings.append(tofi_entry)
            elif hours_until <= 48:
                watches.append(tofi_entry)
        
        return {
            'warning': warnings,
            'watch': watches
        }
    
    def create_zone_from_forecast(
        self,
        forecast_track: List[Dict],
        coastlines: List[LineString],
        zone_type: str,
        current_time: datetime
    ) -> Polygon:
        """
        Complete pipeline to create a zone polygon from forecast track.
        
        Args:
            forecast_track: List of forecast points
            coastlines: List of coastal segments
            zone_type: 'watch' or 'warning'
            current_time: Current time
        
        Returns:
            Final zone polygon
        """
        from .gale_arrival import get_gale_arrival_service
        
        gale_service = get_gale_arrival_service()
        
        # Calculate TOFI for each coastal segment
        tofi_data = []
        for coastline in coastlines:
            tofi = gale_service.calculate_tofi(coastline, forecast_track)
            if tofi:
                # Classify the arrival
                category = gale_service.classify_arrival_window(tofi['tofi_utc'], current_time)
                if category == zone_type:
                    tofi_data.append({
                        'tofi_utc': tofi['tofi_utc'],
                        'segment': coastline
                    })
        
        if not tofi_data:
            return None
        
        # Extract affected segments
        affected_segments = [entry['segment'] for entry in tofi_data]
        
        # Build polygon
        polygon = self.build_zone_polygon(affected_segments)
        
        if polygon:
            # Smooth edges
            polygon = self.smooth_edges(polygon)
        
        return polygon


# Singleton instance
_polygon_builder_service = None

def get_polygon_builder_service() -> PolygonBuilderService:
    """Get or create the singleton polygon builder service."""
    global _polygon_builder_service
    if _polygon_builder_service is None:
        _polygon_builder_service = PolygonBuilderService()
    return _polygon_builder_service
