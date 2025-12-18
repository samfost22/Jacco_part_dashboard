"""
Utility functions for EU Parts Job Dashboard.
"""

from utils.language import Language
from utils.formatters import (
    format_datetime,
    format_status,
    format_priority,
    format_currency,
    format_coordinates,
    format_address,
    format_duration,
    format_list,
    format_phone,
    truncate_text,
    format_boolean,
    status_badge,
    priority_badge
)
from utils.gps_helpers import (
    is_in_eu_bounds,
    validate_coordinates,
    calculate_distance,
    get_center_point,
    get_country_from_coordinates,
    format_map_data,
    create_map_tooltip,
    get_zoom_level,
    parse_coordinates_string,
    get_bounding_box,
    EU_BOUNDS
)

__all__ = [
    'Language',
    'format_datetime',
    'format_status',
    'format_priority',
    'format_currency',
    'format_coordinates',
    'format_address',
    'format_duration',
    'format_list',
    'format_phone',
    'truncate_text',
    'format_boolean',
    'status_badge',
    'priority_badge',
    'is_in_eu_bounds',
    'validate_coordinates',
    'calculate_distance',
    'get_center_point',
    'get_country_from_coordinates',
    'format_map_data',
    'create_map_tooltip',
    'get_zoom_level',
    'parse_coordinates_string',
    'get_bounding_box',
    'EU_BOUNDS'
]
