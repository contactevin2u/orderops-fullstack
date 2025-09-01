"""Geofencing utilities for driver location tracking"""

import math
from typing import Tuple
from app.config.clock_config import HOME_BASE_LAT, HOME_BASE_LNG, HOME_BASE_RADIUS_KM


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great circle distance between two points on earth in kilometers
    using the Haversine formula.
    
    Args:
        lat1, lng1: Latitude and longitude of first point in decimal degrees
        lat2, lng2: Latitude and longitude of second point in decimal degrees
    
    Returns:
        Distance between points in kilometers
    """
    # Convert latitude and longitude from degrees to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


def is_within_home_base(lat: float, lng: float) -> bool:
    """
    Check if given coordinates are within home base radius
    
    Args:
        lat, lng: Coordinates to check
    
    Returns:
        True if within home base radius, False otherwise
    """
    distance = haversine_distance(lat, lng, HOME_BASE_LAT, HOME_BASE_LNG)
    return distance <= HOME_BASE_RADIUS_KM


def distance_from_home_base(lat: float, lng: float) -> float:
    """
    Calculate distance from home base in kilometers
    
    Args:
        lat, lng: Coordinates to check
    
    Returns:
        Distance from home base in kilometers
    """
    return haversine_distance(lat, lng, HOME_BASE_LAT, HOME_BASE_LNG)


def is_outstation_location(lat: float, lng: float) -> Tuple[bool, float]:
    """
    Check if location is outstation (outside home base radius) and return distance
    
    Args:
        lat, lng: Coordinates to check
    
    Returns:
        Tuple of (is_outstation, distance_from_home_base_km)
    """
    distance = distance_from_home_base(lat, lng)
    is_outstation = distance > HOME_BASE_RADIUS_KM
    return is_outstation, distance


def get_location_description(lat: float, lng: float) -> str:
    """
    Get human-readable description of location relative to home base
    
    Args:
        lat, lng: Coordinates to describe
    
    Returns:
        Description string like "132.4km from Batu Caves (Outstation)" or "Within 100km of Batu Caves"
    """
    is_outstation, distance = is_outstation_location(lat, lng)
    
    if is_outstation:
        return f"{distance:.1f}km from Batu Caves (Outstation - RM100 allowance)"
    else:
        return f"{distance:.1f}km from Batu Caves (Within 100km radius)"