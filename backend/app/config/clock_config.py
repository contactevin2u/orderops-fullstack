"""Clock-in/Clock-out system configuration"""

from typing import Tuple

# Home base location (Batu Caves)
HOME_BASE_LAT = 3.2379
HOME_BASE_LNG = 101.6841
HOME_BASE_RADIUS_KM = 100.0  # RM 100 allowance for locations >100km from home base

# Working hours and allowances
OUTSTATION_ALLOWANCE_AMOUNT = 100.0  # RM 100 for outstation shifts
STANDARD_WORKING_HOURS = 8.0
OVERTIME_THRESHOLD = 8.0

# Shift settings
MAX_SHIFT_DURATION_HOURS = 168.0  # Maximum allowed shift duration (1 week for testing)
AUTO_CLOCK_OUT_AFTER_HOURS = 168.0  # Auto clock-out if no manual clock-out (1 week for testing)

# Location accuracy requirements
MIN_LOCATION_ACCURACY_METERS = 100.0
LOCATION_TIMEOUT_SECONDS = 30.0

# API rate limiting
MAX_CLOCK_EVENTS_PER_HOUR = 10

# Time zones
DEFAULT_TIMEZONE = "Asia/Kuala_Lumpur"

def get_home_base_coordinates() -> Tuple[float, float]:
    """Get home base coordinates as (lat, lng) tuple"""
    return (HOME_BASE_LAT, HOME_BASE_LNG)