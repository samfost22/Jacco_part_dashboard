"""
Formatting utilities for displaying data in the dashboard.
"""

from datetime import datetime
from typing import Optional, Any
import streamlit as st


def format_datetime(dt: Optional[datetime], date_only: bool = False) -> str:
    """
    Format datetime for display.

    Args:
        dt: Datetime object
        date_only: If True, show only date

    Returns:
        Formatted datetime string
    """
    if dt is None:
        return "N/A"

    try:
        if date_only:
            return dt.strftime("%Y-%m-%d")
        else:
            return dt.strftime("%Y-%m-%d %H:%M")
    except (AttributeError, ValueError):
        return str(dt)


def format_status(status: Optional[str]) -> str:
    """
    Format job status for display.
    Note: Use lowercase 'd' in "Parts delivered"

    Args:
        status: Job status string

    Returns:
        Formatted status string
    """
    if not status:
        return "Unknown"

    # Ensure correct capitalization for "Parts delivered"
    if status.lower() == "parts delivered":
        return "Parts delivered"

    return status


def format_priority(priority: Optional[str]) -> str:
    """
    Format priority with emoji indicator.

    Args:
        priority: Priority level

    Returns:
        Formatted priority string
    """
    if not priority:
        return "Normal"

    priority_lower = priority.lower()

    priority_map = {
        "high": "High",
        "urgent": "Urgent",
        "medium": "Medium",
        "normal": "Normal",
        "low": "Low"
    }

    return priority_map.get(priority_lower, priority)


def format_currency(amount: Optional[float], currency: str = "EUR") -> str:
    """
    Format currency for display.

    Args:
        amount: Amount to format
        currency: Currency code

    Returns:
        Formatted currency string
    """
    if amount is None:
        return "N/A"

    try:
        if currency == "EUR":
            return f"€{amount:,.2f}"
        elif currency == "USD":
            return f"${amount:,.2f}"
        elif currency == "GBP":
            return f"£{amount:,.2f}"
        else:
            return f"{amount:,.2f} {currency}"
    except (ValueError, TypeError):
        return str(amount)


def format_coordinates(lat: Optional[float], lon: Optional[float]) -> str:
    """
    Format GPS coordinates for display.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Formatted coordinates string
    """
    if lat is None or lon is None:
        return "N/A"

    try:
        return f"{lat:.6f}, {lon:.6f}"
    except (ValueError, TypeError):
        return f"{lat}, {lon}"


def format_address(address: Optional[str], max_length: int = 100) -> str:
    """
    Format address for display with optional truncation.

    Args:
        address: Address string
        max_length: Maximum length before truncation

    Returns:
        Formatted address string
    """
    if not address:
        return "N/A"

    if len(address) > max_length:
        return address[:max_length-3] + "..."

    return address


def format_duration(start: Optional[datetime], end: Optional[datetime]) -> str:
    """
    Format duration between two datetimes.

    Args:
        start: Start datetime
        end: End datetime

    Returns:
        Formatted duration string
    """
    if not start or not end:
        return "N/A"

    try:
        duration = end - start
        hours = duration.total_seconds() / 3600

        if hours < 1:
            minutes = duration.total_seconds() / 60
            return f"{int(minutes)} min"
        elif hours < 24:
            return f"{hours:.1f} hrs"
        else:
            days = duration.days
            return f"{days} days"
    except (TypeError, AttributeError):
        return "N/A"


def format_list(items: Optional[list], separator: str = ", ") -> str:
    """
    Format list items for display.

    Args:
        items: List of items
        separator: Separator between items

    Returns:
        Formatted string
    """
    if not items:
        return "N/A"

    try:
        return separator.join(str(item) for item in items)
    except (TypeError, AttributeError):
        return str(items)


def format_phone(phone: Optional[str]) -> str:
    """
    Format phone number for display.

    Args:
        phone: Phone number string

    Returns:
        Formatted phone number
    """
    if not phone:
        return "N/A"

    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, phone))

    # Format based on length
    if len(digits) == 10:  # Dutch mobile
        return f"+31 {digits[1:4]} {digits[4:7]} {digits[7:]}"
    elif len(digits) == 11 and digits.startswith('31'):
        return f"+{digits[:2]} {digits[2:5]} {digits[5:8]} {digits[8:]}"
    else:
        return phone


def truncate_text(text: Optional[str], max_length: int = 50) -> str:
    """
    Truncate text with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length-3] + "..."


def format_boolean(value: Optional[bool], true_text: str = "Yes", false_text: str = "No") -> str:
    """
    Format boolean value for display.

    Args:
        value: Boolean value
        true_text: Text to show for True
        false_text: Text to show for False

    Returns:
        Formatted string
    """
    if value is None:
        return "N/A"

    return true_text if value else false_text


def status_badge(status: str) -> str:
    """
    Create a colored badge for job status.
    Uses actual Zuper status names.

    Args:
        status: Job status

    Returns:
        HTML string with colored badge
    """
    status_colors = {
        "new ticket": "#3498db",        # Blue
        "received request": "#9b59b6",  # Purple
        "parts on order": "#f39c12",    # Orange
        "shop pick up": "#27ae60",      # Green
        "shipped": "#16a085",           # Teal
        "parts delivered": "#2ecc71",   # Bright green
        "done": "#2ecc71",              # Bright green
        "canceled": "#95a5a6",          # Gray
    }

    color = status_colors.get(status.lower(), "#607D8B")  # Default: Blue Grey

    return f'<span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 500;">{status}</span>'


def priority_badge(priority: str) -> str:
    """
    Create a colored badge for priority.

    Args:
        priority: Priority level

    Returns:
        HTML string with colored badge
    """
    priority_colors = {
        "urgent": "#F44336",    # Red
        "high": "#FF9800",      # Orange
        "medium": "#2196F3",    # Blue
        "normal": "#4CAF50",    # Green
        "low": "#9E9E9E",       # Grey
    }

    color = priority_colors.get(priority.lower(), "#607D8B")

    return f'<span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 500;">{priority}</span>'
