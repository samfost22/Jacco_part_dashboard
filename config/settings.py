"""
Application configuration settings.
"""

from typing import Dict, Any
import streamlit as st


class AppSettings:
    """Application settings and configuration."""

    # Geographic bounds for EU filtering
    EU_BOUNDS = {
        "min_lat": 35.0,
        "max_lat": 72.0,
        "min_lon": -11.0,
        "max_lon": 40.0
    }

    # Job category filter - MUST use capital R
    JOB_CATEGORY = "Field Requires Parts"

    # Pagination settings
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 100

    # Sync settings
    DEFAULT_SYNC_INTERVAL_MINUTES = 15
    MAX_SYNC_INTERVAL_MINUTES = 60

    # Display settings
    DEFAULT_LANGUAGE = "en"
    AVAILABLE_LANGUAGES = ["en", "nl"]

    # Map settings
    DEFAULT_MAP_ZOOM = 4
    CITY_MAP_ZOOM = 13
    REGION_MAP_ZOOM = 8

    # Status options (actual Zuper status names)
    JOB_STATUSES = [
        "New Ticket",
        "Received Request",
        "Parts On Order",
        "Shop Pick UP",
        "Shipped",
        "Parts delivered",  # lowercase 'd' - important!
        "Done",
        "Canceled"
    ]

    # Priority levels
    PRIORITY_LEVELS = [
        "Urgent",
        "High",
        "Medium",
        "Normal",
        "Low"
    ]

    # Date format
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M"

    # API settings
    API_TIMEOUT_SECONDS = 30
    API_MAX_RETRIES = 3
    API_RATE_LIMIT_PER_MINUTE = 100

    # Database settings
    DB_CONNECTION_POOL_MIN = 1
    DB_CONNECTION_POOL_MAX = 10
    DB_QUERY_TIMEOUT_SECONDS = 30

    # Cache settings (Streamlit cache TTL in seconds)
    CACHE_TTL_SHORT = 300      # 5 minutes
    CACHE_TTL_MEDIUM = 900     # 15 minutes
    CACHE_TTL_LONG = 3600      # 1 hour

    # Export settings
    EXPORT_MAX_ROWS = 10000
    EXPORT_FORMATS = ["CSV", "JSON", "Excel"]

    @classmethod
    def get_sync_interval(cls) -> int:
        """
        Get sync interval from secrets or use default.

        Returns:
            Sync interval in minutes
        """
        try:
            interval = st.secrets.get("app", {}).get("refresh_interval_minutes")
            if interval:
                return min(int(interval), cls.MAX_SYNC_INTERVAL_MINUTES)
        except Exception:
            pass

        return cls.DEFAULT_SYNC_INTERVAL_MINUTES

    @classmethod
    def get_max_jobs_per_page(cls) -> int:
        """
        Get max jobs per page from secrets or use default.

        Returns:
            Maximum jobs per page
        """
        try:
            max_jobs = st.secrets.get("app", {}).get("max_jobs_per_page")
            if max_jobs:
                return min(int(max_jobs), cls.MAX_PAGE_SIZE)
        except Exception:
            pass

        return cls.DEFAULT_PAGE_SIZE

    @classmethod
    def is_valid_eu_location(cls, latitude: float, longitude: float) -> bool:
        """
        Check if coordinates are within EU bounds.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            True if within EU bounds
        """
        if latitude is None or longitude is None:
            return False

        return (
            cls.EU_BOUNDS["min_lat"] <= latitude <= cls.EU_BOUNDS["max_lat"] and
            cls.EU_BOUNDS["min_lon"] <= longitude <= cls.EU_BOUNDS["max_lon"]
        )

    @classmethod
    def get_app_config(cls) -> Dict[str, Any]:
        """
        Get complete application configuration.

        Returns:
            Dictionary with all configuration settings
        """
        return {
            "eu_bounds": cls.EU_BOUNDS,
            "job_category": cls.JOB_CATEGORY,
            "page_size": cls.get_max_jobs_per_page(),
            "sync_interval": cls.get_sync_interval(),
            "default_language": cls.DEFAULT_LANGUAGE,
            "available_languages": cls.AVAILABLE_LANGUAGES,
            "job_statuses": cls.JOB_STATUSES,
            "priority_levels": cls.PRIORITY_LEVELS,
            "date_format": cls.DATE_FORMAT,
            "datetime_format": cls.DATETIME_FORMAT
        }


# Feature flags
class FeatureFlags:
    """Feature flags for enabling/disabling features."""

    # Dashboard features
    ENABLE_MAP_VIEW = True
    ENABLE_BULK_LOOKUP = True
    ENABLE_PARTS_INVENTORY = True
    ENABLE_EXPORT = True

    # Sync features
    ENABLE_MANUAL_SYNC = True
    ENABLE_AUTO_SYNC = False  # Auto-sync in background

    # Advanced features
    ENABLE_ADVANCED_FILTERS = True
    ENABLE_CUSTOM_FIELDS = True
    ENABLE_DARK_MODE = False

    # AI features (Anthropic API)
    ENABLE_AI_ASSISTANT = True
    ENABLE_AI_SEARCH = True
    ENABLE_AI_ANALYSIS = True

    @classmethod
    def is_enabled(cls, feature_name: str) -> bool:
        """
        Check if a feature is enabled.

        Args:
            feature_name: Name of the feature flag

        Returns:
            True if feature is enabled
        """
        return getattr(cls, feature_name, False)
