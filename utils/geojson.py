"""
GeoJSON utilities - Conversions.
"""
import json
from shapely.geometry import shape, mapping


def geometry_to_geojson(geom):
    """
    Convert Shapely geometry to GeoJSON dict.
    
    Args:
        geom: Shapely geometry
    
    Returns:
        GeoJSON dict
    """
    return mapping(geom)


def geojson_to_geometry(geojson_dict):
    """
    Convert GeoJSON dict to Shapely geometry.
    
    Args:
        geojson_dict: GeoJSON dictionary
    
    Returns:
        Shapely geometry
    """
    return shape(geojson_dict)


def point_to_geojson(lat, lon, properties=None):
    """
    Create GeoJSON Point feature.
    
    Args:
        lat: Latitude
        lon: Longitude
        properties: Optional properties dict
    
    Returns:
        GeoJSON Feature dict
    """
    return {
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [lon, lat]
        },
        'properties': properties or {}
    }


def linestring_to_geojson(coordinates, properties=None):
    """
    Create GeoJSON LineString feature.
    
    Args:
        coordinates: List of [lon, lat] pairs
        properties: Optional properties dict
    
    Returns:
        GeoJSON Feature dict
    """
    return {
        'type': 'Feature',
        'geometry': {
            'type': 'LineString',
            'coordinates': coordinates
        },
        'properties': properties or {}
    }


def polygon_to_geojson(geometry, properties=None):
    """
    Create GeoJSON Polygon feature from Shapely geometry.
    
    Args:
        geometry: Shapely Polygon
        properties: Optional properties dict
    
    Returns:
        GeoJSON Feature dict
    """
    return {
        'type': 'Feature',
        'geometry': geometry_to_geojson(geometry),
        'properties': properties or {}
    }
