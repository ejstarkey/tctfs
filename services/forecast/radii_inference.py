"""
Radii Inference Service - Derive wind radii when missing from forecast data.
Uses basin-specific radius-intensity curves.
"""
import logging
from typing import Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)


class RadiiInferenceService:
    """
    Infer wind radii (R34/R50/R64) from intensity when not provided in A-Deck data.
    Uses empirical radius-intensity relationships and forward speed adjustments.
    """
    
    # Basin-specific coefficients for radius-intensity curves
    # Format: {basin: {wind_threshold: (a, b, c)}} for R = a * Vmax^b + c
    BASIN_COEFFICIENTS = {
        'WP': {
            34: (0.45, 1.2, 20),  # R34 = 0.45 * Vmax^1.2 + 20
            50: (0.30, 1.3, 10),  # R50
            64: (0.20, 1.4, 5),   # R64
        },
        'EP': {
            34: (0.40, 1.25, 25),
            50: (0.28, 1.35, 12),
            64: (0.18, 1.45, 6),
        },
        'SH': {
            34: (0.42, 1.22, 22),
            50: (0.29, 1.32, 11),
            64: (0.19, 1.42, 5),
        },
        'IO': {
            34: (0.43, 1.23, 23),
            50: (0.29, 1.33, 11),
            64: (0.19, 1.43, 5),
        },
        'AL': {
            34: (0.38, 1.28, 28),
            50: (0.26, 1.38, 14),
            64: (0.17, 1.48, 7),
        },
    }
    
    def infer_radii(self, vmax_kt: float, basin: str = 'WP', forward_speed_kt: Optional[float] = None) -> Dict:
        """
        Infer wind radii from intensity.
        
        Args:
            vmax_kt: Maximum sustained winds in knots
            basin: Basin code for coefficient selection
            forward_speed_kt: Forward speed for asymmetry adjustment
        
        Returns:
            Dictionary with R34, R50, R64 by quadrant (NE, SE, SW, NW)
        """
        if vmax_kt < 34:
            # Tropical storm not strong enough for 34kt winds
            return None
        
        # Get basin coefficients (default to WP if unknown)
        coeffs = self.BASIN_COEFFICIENTS.get(basin, self.BASIN_COEFFICIENTS['WP'])
        
        # Compute base radii (symmetric, no motion effect)
        base_radii = {}
        for threshold in [34, 50, 64]:
            if vmax_kt >= threshold:
                a, b, c = coeffs[threshold]
                radius = a * (vmax_kt ** b) + c
                base_radii[threshold] = max(radius, 0)  # Ensure non-negative
        
        if not base_radii:
            return None
        
        # Apply forward speed asymmetry if provided
        if forward_speed_kt and forward_speed_kt > 0:
            radii_by_quadrant = self._apply_asymmetry(base_radii, forward_speed_kt)
        else:
            # Symmetric radii (all quadrants same)
            radii_by_quadrant = {
                'NE': base_radii,
                'SE': base_radii,
                'SW': base_radii,
                'NW': base_radii,
            }
        
        return radii_by_quadrant
    
    def _apply_asymmetry(self, base_radii: Dict, forward_speed_kt: float) -> Dict:
        """
        Apply asymmetry to radii based on forward speed.
        Assuming motion is northward (typical), right front quadrant (NE) gets enhanced.
        
        Args:
            base_radii: Symmetric radii dictionary {34: r34, 50: r50, 64: r64}
            forward_speed_kt: Forward speed in knots
        
        Returns:
            Radii by quadrant
        """
        # Asymmetry factors based on forward speed
        # Faster motion = more asymmetric
        speed_factor = min(forward_speed_kt / 20.0, 1.5)  # Cap at 1.5x asymmetry
        
        # Quadrant multipliers (assuming northward motion)
        # Right-front (NE): enhanced
        # Left-front (NW): slightly enhanced
        # Right-rear (SE): slightly reduced
        # Left-rear (SW): reduced
        multipliers = {
            'NE': 1.0 + (0.3 * speed_factor),  # Enhanced right-front
            'NW': 1.0 + (0.1 * speed_factor),  # Slightly enhanced left-front
            'SE': 1.0 - (0.1 * speed_factor),  # Slightly reduced right-rear
            'SW': 1.0 - (0.2 * speed_factor),  # Reduced left-rear
        }
        
        radii_by_quadrant = {}
        for quadrant, mult in multipliers.items():
            radii_by_quadrant[quadrant] = {
                threshold: radius * mult
                for threshold, radius in base_radii.items()
            }
        
        return radii_by_quadrant
    
    def infer_quadrant_radii_for_forecast(self, forecast_point: Dict, basin: str = 'WP') -> Optional[Dict]:
        """
        Convenience method to infer radii for a forecast point.
        
        Args:
            forecast_point: Dictionary with 'vmax_kt' and optionally 'motion_speed_kt'
            basin: Basin code
        
        Returns:
            Radii dictionary suitable for storing in forecast_point.radii_json
        """
        vmax = forecast_point.get('vmax_kt')
        if not vmax:
            return None
        
        forward_speed = forecast_point.get('motion_speed_kt')
        
        radii = self.infer_radii(vmax, basin, forward_speed)
        
        if not radii:
            return None
        
        # Convert to format suitable for JSON storage
        radii_json = {}
        for quadrant in ['NE', 'SE', 'SW', 'NW']:
            quad_radii = radii.get(quadrant, {})
            radii_json[quadrant] = {
                'r34': quad_radii.get(34),
                'r50': quad_radii.get(50),
                'r64': quad_radii.get(64),
            }
        
        return radii_json


# Singleton instance
_radii_inference_service = None

def get_radii_inference_service() -> RadiiInferenceService:
    """Get or create the singleton radii inference service."""
    global _radii_inference_service
    if _radii_inference_service is None:
        _radii_inference_service = RadiiInferenceService()
    return _radii_inference_service
