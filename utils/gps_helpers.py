"""
GPS and geographic utilities for the dashboard.
Handles coordinate validation, distance calculations, and map display.
"""

import math
from typing import Tuple, Optional, List, Dict, Any
import streamlit as st


# EU geographic bounds for filtering
EU_BOUNDS = {
    "min_lat": 35.0,
    "max_lat": 72.0,
    "min_lon": -11.0,
    "max_lon": 40.0
}


def is_in_eu_bounds(latitude: float, longitude: float) -> bool:
    """
    Check if coordinates are within EU geographic bounds.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        True if within EU bounds, False otherwise
    """
    if latitude is None or longitude is None:
        return False

    return (
        EU_BOUNDS["min_lat"] <= latitude <= EU_BOUNDS["max_lat"] and
        EU_BOUNDS["min_lon"] <= longitude <= EU_BOUNDS["max_lon"]
    )


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """
    Validate GPS coordinates.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        True if valid coordinates, False otherwise
    """
    if latitude is None or longitude is None:
        return False

    try:
        lat = float(latitude)
        lon = float(longitude)

        # Check if within valid GPS ranges
        if not (-90 <= lat <= 90):
            return False

        if not (-180 <= lon <= 180):
            return False

        return True

    except (ValueError, TypeError):
        return False


def calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in kilometers
    """
    if not all([lat1, lon1, lat2, lon2]):
        return 0.0

    # Earth's radius in kilometers
    R = 6371.0

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    distance = R * c

    return distance


def get_center_point(coordinates: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calculate center point of multiple coordinates.

    Args:
        coordinates: List of (latitude, longitude) tuples

    Returns:
        Tuple of (center_lat, center_lon)
    """
    if not coordinates:
        # Default to center of EU
        return (52.5, 13.4)  # Berlin

    valid_coords = [(lat, lon) for lat, lon in coordinates if lat and lon]

    if not valid_coords:
        return (52.5, 13.4)

    avg_lat = sum(lat for lat, lon in valid_coords) / len(valid_coords)
    avg_lon = sum(lon for lat, lon in valid_coords) / len(valid_coords)

    return (avg_lat, avg_lon)


def get_country_from_coordinates(latitude: float, longitude: float) -> str:
    """
    Get approximate country from coordinates (simplified).
    This is a very basic approximation based on rough coordinate ranges.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        Country name (approximate)
    """
    # Simplified country detection based on coordinate ranges
    # This is NOT accurate and should be replaced with proper geocoding in production

    if not validate_coordinates(latitude, longitude):
        return "Unknown"

    # Very rough approximations
    if 50 <= latitude <= 54 and 3 <= longitude <= 7:
        return "Netherlands"
    elif 49 <= latitude <= 51.5 and 2 <= longitude <= 6:
        return "Belgium"
    elif 47 <= latitude <= 55 and 5 <= longitude <= 15:
        return "Germany"
    elif 42 <= latitude <= 51 and -5 <= longitude <= 9:
        return "France"
    elif 49.5 <= latitude <= 52 and -6 <= longitude <= 2:
        return "United Kingdom"
    elif 55 <= latitude <= 69 and 5 <= longitude <= 31:
        return "Scandinavia"
    elif 36 <= latitude <= 47 and 6 <= longitude <= 19:
        return "Italy/Switzerland"
    elif 36 <= latitude <= 43.5 and -9 <= longitude <= 4:
        return "Spain/Portugal"
    elif 44 <= latitude <= 54 and 12 <= longitude <= 24:
        return "Poland/Czech Republic"
    else:
        return "Europe"


def format_map_data(jobs_df) -> List[Dict[str, Any]]:
    """
    Format job data for map display.

    Args:
        jobs_df: DataFrame with job data

    Returns:
        List of dictionaries formatted for map markers
    """
    map_data = []

    for _, job in jobs_df.iterrows():
        lat = job.get('latitude')
        lon = job.get('longitude')

        if validate_coordinates(lat, lon):
            map_data.append({
                'lat': lat,
                'lon': lon,
                'job_number': job.get('job_number', 'N/A'),
                'title': job.get('title', 'N/A'),
                'status': job.get('job_status', 'Unknown'),
                'customer': job.get('customer_name', 'N/A'),
                'address': job.get('job_address', 'N/A')
            })

    return map_data


def create_map_tooltip(job: Dict[str, Any]) -> str:
    """
    Create tooltip text for map marker.

    Args:
        job: Job dictionary

    Returns:
        HTML tooltip string
    """
    return f"""
    <b>{job['job_number']}</b><br/>
    {job['title']}<br/>
    Status: {job['status']}<br/>
    Customer: {job['customer']}
    """


def get_zoom_level(jobs_count: int) -> int:
    """
    Calculate appropriate map zoom level based on number of jobs.

    Args:
        jobs_count: Number of jobs to display

    Returns:
        Zoom level (1-20)
    """
    if jobs_count == 0:
        return 4  # Europe-wide view
    elif jobs_count == 1:
        return 13  # City-level view
    elif jobs_count < 10:
        return 8   # Regional view
    elif jobs_count < 50:
        return 6   # Country-level view
    else:
        return 4   # Europe-wide view


def parse_coordinates_string(coord_string: str) -> Optional[Tuple[float, float]]:
    """
    Parse coordinates from a string format.

    Args:
        coord_string: String like "52.3676, 4.9041" or "52.3676,4.9041"

    Returns:
        Tuple of (latitude, longitude) or None if invalid
    """
    if not coord_string:
        return None

    try:
        # Split by comma
        parts = coord_string.replace(' ', '').split(',')

        if len(parts) != 2:
            return None

        lat = float(parts[0])
        lon = float(parts[1])

        if validate_coordinates(lat, lon):
            return (lat, lon)

        return None

    except (ValueError, AttributeError):
        return None


def get_bounding_box(coordinates: List[Tuple[float, float]]) -> Dict[str, float]:
    """
    Calculate bounding box for a list of coordinates.

    Args:
        coordinates: List of (latitude, longitude) tuples

    Returns:
        Dictionary with min_lat, max_lat, min_lon, max_lon
    """
    if not coordinates:
        return EU_BOUNDS

    valid_coords = [(lat, lon) for lat, lon in coordinates if lat and lon]

    if not valid_coords:
        return EU_BOUNDS

    lats = [lat for lat, lon in valid_coords]
    lons = [lon for lat, lon in valid_coords]

    return {
        "min_lat": min(lats),
        "max_lat": max(lats),
        "min_lon": min(lons),
        "max_lon": max(lons)
    }
