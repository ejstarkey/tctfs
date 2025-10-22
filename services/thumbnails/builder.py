"""
Thumbnail Builder Service - Generate map thumbnails for storm tracks.
"""
import logging
from typing import Optional, Dict
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io

logger = logging.getLogger(__name__)


class ThumbnailBuilderService:
    """
    Generate thumbnail images of storm tracks for dashboard and archive.
    """
    
    DEFAULT_WIDTH = 400
    DEFAULT_HEIGHT = 300
    DEFAULT_BG_COLOR = (240, 245, 250)  # Light blue-gray
    
    def __init__(self):
        """Initialize thumbnail builder."""
        self.font_regular = None
        self.font_bold = None
        
        # Try to load fonts, fall back to default if not available
        try:
            self.font_regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            self.font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except Exception as e:
            logger.warning(f"Failed to load fonts, using default: {e}")
            self.font_regular = ImageFont.load_default()
            self.font_bold = ImageFont.load_default()
    
    def generate_thumbnail(
        self,
        storm_data: Dict,
        track_points: list,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT
    ) -> bytes:
        """
        Generate thumbnail image for a storm.
        
        Args:
            storm_data: Dictionary with storm metadata (name, basin, intensity, etc.)
            track_points: List of (lat, lon) tuples for track
            width: Image width in pixels
            height: Image height in pixels
        
        Returns:
            PNG image as bytes
        """
        # Create image
        img = Image.new('RGB', (width, height), self.DEFAULT_BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        if not track_points:
            # No track data, just draw placeholder
            self._draw_placeholder(draw, width, height, storm_data)
        else:
            # Calculate bounds
            lats = [p[0] for p in track_points]
            lons = [p[1] for p in track_points]
            
            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)
            
            # Add 10% padding
            lat_range = max_lat - min_lat
            lon_range = max_lon - min_lon
            
            min_lat -= lat_range * 0.1
            max_lat += lat_range * 0.1
            min_lon -= lon_range * 0.1
            max_lon += lon_range * 0.1
            
            # Draw track
            self._draw_track(draw, track_points, min_lat, max_lat, min_lon, max_lon, width, height)
        
        # Draw storm info overlay
        self._draw_info_overlay(draw, width, height, storm_data)
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _draw_track(self, draw, track_points, min_lat, max_lat, min_lon, max_lon, width, height):
        """Draw the storm track on the image."""
        # Map coordinates to pixels
        margin = 30
        plot_width = width - 2 * margin
        plot_height = height - 2 * margin
        
        def map_coords(lat, lon):
            # Normalize to 0-1
            x_norm = (lon - min_lon) / (max_lon - min_lon) if max_lon != min_lon else 0.5
            y_norm = (max_lat - lat) / (max_lat - min_lat) if max_lat != min_lat else 0.5
            
            # Scale to pixels
            x_pixel = margin + x_norm * plot_width
            y_pixel = margin + y_norm * plot_height
            
            return (x_pixel, y_pixel)
        
        # Draw track line
        pixel_points = [map_coords(lat, lon) for lat, lon in track_points]
        
        if len(pixel_points) > 1:
            draw.line(pixel_points, fill=(30, 64, 175), width=2)  # Blue track
        
        # Draw points
        for i, point in enumerate(pixel_points):
            radius = 4 if i == len(pixel_points) - 1 else 2  # Larger for current position
            color = (220, 38, 38) if i == len(pixel_points) - 1 else (30, 64, 175)  # Red for current
            
            draw.ellipse(
                [point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius],
                fill=color
            )
    
    def _draw_placeholder(self, draw, width, height, storm_data):
        """Draw placeholder when no track data available."""
        text = "No track data"
        bbox = draw.textbbox((0, 0), text, font=self.font_regular)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        
        draw.text((x, y), text, fill=(100, 116, 139), font=self.font_regular)
    
    def _draw_info_overlay(self, draw, width, height, storm_data):
        """Draw storm information overlay."""
        # Semi-transparent background at bottom
        overlay_height = 60
        draw.rectangle(
            [(0, height - overlay_height), (width, height)],
            fill=(15, 23, 42, 200)  # Dark blue with transparency (Note: PIL doesn't support alpha in rectangle, this is conceptual)
        )
        
        # Actually for PIL, we need to use a solid color
        draw.rectangle(
            [(0, height - overlay_height), (width, height)],
            fill=(15, 23, 42)
        )
        
        # Storm name
        storm_name = storm_data.get('name', 'UNNAMED')
        storm_id = storm_data.get('storm_id', '')
        
        name_text = f"{storm_name} ({storm_id})"
        draw.text((10, height - 50), name_text, fill=(255, 255, 255), font=self.font_bold)
        
        # Intensity
        vmax = storm_data.get('vmax_kt')
        if vmax:
            intensity_text = f"{int(vmax)} kt"
            draw.text((10, height - 25), intensity_text, fill=(203, 213, 225), font=self.font_regular)


# Singleton instance
_thumbnail_builder_service = None

def get_thumbnail_builder_service() -> ThumbnailBuilderService:
    """Get or create the singleton thumbnail builder service."""
    global _thumbnail_builder_service
    if _thumbnail_builder_service is None:
        _thumbnail_builder_service = ThumbnailBuilderService()
    return _thumbnail_builder_service
