"""
Custom exceptions for Zuper API client.
"""


class ZuperAPIError(Exception):
    """Base exception for Zuper API errors."""
    pass


class ZuperAuthenticationError(ZuperAPIError):
    """Raised when API authentication fails."""
    pass


class ZuperRateLimitError(ZuperAPIError):
    """Raised when API rate limit is exceeded."""
    pass


class ZuperNotFoundError(ZuperAPIError):
    """Raised when requested resource is not found."""
    pass


class ZuperValidationError(ZuperAPIError):
    """Raised when request validation fails."""
    pass


class ZuperServerError(ZuperAPIError):
    """Raised when Zuper server returns 5xx error."""
    pass


class ZuperNetworkError(ZuperAPIError):
    """Raised when network connection fails."""
    pass
