"""Tests for geofencing utilities"""

import pytest
from app.utils.geofencing import (
    haversine_distance,
    is_within_home_base,
    distance_from_home_base,
    is_outstation_location,
    get_location_description
)
from app.config.clock_config import HOME_BASE_LAT, HOME_BASE_LNG, HOME_BASE_RADIUS_KM


class TestGeofencing:
    def test_haversine_distance_same_point(self):
        """Test distance calculation for same coordinates"""
        distance = haversine_distance(HOME_BASE_LAT, HOME_BASE_LNG, HOME_BASE_LAT, HOME_BASE_LNG)
        assert distance == 0.0

    def test_haversine_distance_known_points(self):
        """Test distance calculation between known points"""
        # Distance from Batu Caves to KL city center (approximately 15km)
        kl_lat, kl_lng = 3.1569, 101.7123
        distance = haversine_distance(HOME_BASE_LAT, HOME_BASE_LNG, kl_lat, kl_lng)
        
        # Should be approximately 15km (allow some tolerance)
        assert 14.0 < distance < 16.0

    def test_is_within_home_base_true(self):
        """Test location within home base radius"""
        # Point very close to home base
        nearby_lat = HOME_BASE_LAT + 0.01  # ~1km away
        nearby_lng = HOME_BASE_LNG + 0.01
        
        assert is_within_home_base(nearby_lat, nearby_lng) is True

    def test_is_within_home_base_false(self):
        """Test location outside home base radius"""
        # KL city center (much farther than 3km)
        kl_lat, kl_lng = 3.1569, 101.7123
        
        assert is_within_home_base(kl_lat, kl_lng) is False

    def test_distance_from_home_base(self):
        """Test distance calculation from home base"""
        kl_lat, kl_lng = 3.1569, 101.7123
        distance = distance_from_home_base(kl_lat, kl_lng)
        
        # Should be approximately 15km
        assert 14.0 < distance < 16.0

    def test_is_outstation_location_within_base(self):
        """Test outstation check for location within home base"""
        nearby_lat = HOME_BASE_LAT + 0.01
        nearby_lng = HOME_BASE_LNG + 0.01
        
        is_outstation, distance = is_outstation_location(nearby_lat, nearby_lng)
        
        assert is_outstation is False
        assert distance < HOME_BASE_RADIUS_KM

    def test_is_outstation_location_outside_base(self):
        """Test outstation check for location outside home base"""
        kl_lat, kl_lng = 3.1569, 101.7123
        
        is_outstation, distance = is_outstation_location(kl_lat, kl_lng)
        
        assert is_outstation is True
        assert distance > HOME_BASE_RADIUS_KM

    def test_get_location_description_within_base(self):
        """Test location description for area within home base"""
        nearby_lat = HOME_BASE_LAT + 0.01
        nearby_lng = HOME_BASE_LNG + 0.01
        
        description = get_location_description(nearby_lat, nearby_lng)
        
        assert "Within Batu Caves area" in description

    def test_get_location_description_outstation(self):
        """Test location description for outstation area"""
        kl_lat, kl_lng = 3.1569, 101.7123
        
        description = get_location_description(kl_lat, kl_lng)
        
        assert "km from Batu Caves (Outstation)" in description
        assert "14." in description or "15." in description  # Distance should be ~15km