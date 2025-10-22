"""
AP Mean Service - Compute AP1-AP30 ensemble mean forecast.
THIS IS THE ONLY FORECAST SHOWN TO USERS.
"""
import logging
from typing import List, Dict
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class APMeanService:
    """
    Computes the per-lead-time mean of AP1-AP30 ensemble members.
    This is the single final forecast displayed to users.
    """
    
    def compute_mean_forecast(self, ap_forecasts: List[Dict]) -> List[Dict]:
        """
        Compute AP1-AP30 mean forecast from individual members.
        
        Args:
            ap_forecasts: List of forecast points from AP01-AP30 members
        
        Returns:
            List of mean forecast points (one per lead time)
        """
        if not ap_forecasts:
            logger.warning("No AP forecasts provided for mean calculation")
            return []
        
        # Group by issuance time and lead time
        grouped = defaultdict(lambda: defaultdict(list))
        
        for forecast in ap_forecasts:
            issuance = forecast['issuance_time']
            lead_hour = forecast['forecast_hour']
            key = (issuance, lead_hour)
            
            grouped[issuance][lead_hour].append(forecast)
        
        # Get the most recent issuance
        latest_issuance = max(grouped.keys())
        
        logger.info(f"Computing AP mean for issuance: {latest_issuance}")
        
        # Compute means for each lead time
        mean_forecasts = []
        
        for lead_hour in sorted(grouped[latest_issuance].keys()):
            members = grouped[latest_issuance][lead_hour]
            
            mean_point = self._compute_mean_point(members, latest_issuance, lead_hour)
            if mean_point:
                mean_forecasts.append(mean_point)
        
        logger.info(f"Computed {len(mean_forecasts)} mean forecast points from {len(ap_forecasts)} members")
        
        return mean_forecasts
    
    def _compute_mean_point(self, members: List[Dict], issuance_time: datetime, lead_hour: int) -> Dict:
        """
        Compute mean forecast point from multiple ensemble members.
        
        Args:
            members: List of forecast points from different AP members at same lead time
            issuance_time: Issuance time of forecast
            lead_hour: Lead time in hours
        
        Returns:
            Dictionary with mean forecast point
        """
        if not members:
            return None
        
        # Extract valid data
        lats = [m['latitude'] for m in members if m.get('latitude') is not None]
        lons = [m['longitude'] for m in members if m.get('longitude') is not None]
        vmaxs = [m['vmax_kt'] for m in members if m.get('vmax_kt') is not None]
        mslps = [m['mslp_hpa'] for m in members if m.get('mslp_hpa') is not None]
        
        if not lats or not lons:
            logger.warning(f"Insufficient position data for lead hour {lead_hour}")
            return None
        
        # Compute spherical mean for position (simplified - using arithmetic mean)
        # For production, use proper great-circle averaging with geographiclib
        mean_lat = float(np.mean(lats))
        mean_lon = float(np.mean(lons))
        
        # Handle longitude wraparound (if points span 180° meridian)
        mean_lon = self._normalize_longitude_mean(lons)
        
        # Compute intensity means
        mean_vmax = float(np.mean(vmaxs)) if vmaxs else None
        mean_mslp = float(np.mean(mslps)) if mslps else None
        
        # Compute valid time
        valid_time = issuance_time + timedelta(hours=lead_hour)
        
        # TODO: Compute radii means if available in members
        mean_radii = None
        
        return {
            'issuance_time': issuance_time,
            'valid_at': valid_time,
            'lead_time_hours': lead_hour,
            'latitude': mean_lat,
            'longitude': mean_lon,
            'vmax_kt': mean_vmax,
            'mslp_hpa': mean_mslp,
            'radii': mean_radii,
            'member_count': len(members),
            'source_tag': 'adecks_open',
            'is_final': True
        }
    
    def _normalize_longitude_mean(self, lons: List[float]) -> float:
        """
        Compute mean longitude handling 180° wraparound.
        
        Args:
            lons: List of longitudes
        
        Returns:
            Mean longitude in range [-180, 180]
        """
        # Check if longitudes span the 180° meridian
        lon_range = max(lons) - min(lons)
        
        if lon_range > 180:
            # Adjust longitudes to 0-360 range for averaging
            adjusted_lons = [(lon + 360) if lon < 0 else lon for lon in lons]
            mean_lon = float(np.mean(adjusted_lons))
            
            # Convert back to -180 to 180
            if mean_lon > 180:
                mean_lon -= 360
        else:
            mean_lon = float(np.mean(lons))
        
        return mean_lon
    
    def compute_mean_radii(self, members: List[Dict]) -> Dict:
        """
        Compute quadrant-wise mean radii from ensemble members.
        
        Args:
            members: List of forecast points with radii data
        
        Returns:
            Dictionary with mean radii by quadrant
        """
        # Group radii by quadrant
        radii_by_quadrant = {
            'NE': {'r34': [], 'r50': [], 'r64': []},
            'SE': {'r34': [], 'r50': [], 'r64': []},
            'SW': {'r34': [], 'r50': [], 'r64': []},
            'NW': {'r34': [], 'r50': [], 'r64': []}
        }
        
        for member in members:
            if not member.get('radii'):
                continue
            
            radii = member['radii']
            for quadrant in ['NE', 'SE', 'SW', 'NW']:
                if quadrant in radii:
                    quad_radii = radii[quadrant]
                    if quad_radii.get('r34'):
                        radii_by_quadrant[quadrant]['r34'].append(quad_radii['r34'])
                    if quad_radii.get('r50'):
                        radii_by_quadrant[quadrant]['r50'].append(quad_radii['r50'])
                    if quad_radii.get('r64'):
                        radii_by_quadrant[quadrant]['r64'].append(quad_radii['r64'])
        
        # Compute means
        mean_radii = {}
        for quadrant, winds in radii_by_quadrant.items():
            mean_radii[quadrant] = {}
            for wind_threshold, values in winds.items():
                if values:
                    mean_radii[quadrant][wind_threshold] = float(np.mean(values))
        
        return mean_radii if any(mean_radii.values()) else None


# Singleton instance
_ap_mean_service = None

def get_ap_mean_service() -> APMeanService:
    """Get or create the singleton AP mean service."""
    global _ap_mean_service
    if _ap_mean_service is None:
        _ap_mean_service = APMeanService()
    return _ap_mean_service
