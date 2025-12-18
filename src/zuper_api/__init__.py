"""
Zuper API client module.
"""

from src.zuper_api.client import ZuperAPIClient, get_zuper_client
from src.zuper_api.exceptions import (
    ZuperAPIError,
    ZuperAuthenticationError,
    ZuperRateLimitError,
    ZuperNotFoundError,
    ZuperValidationError,
    ZuperServerError,
    ZuperNetworkError
)

__all__ = [
    'ZuperAPIClient',
    'get_zuper_client',
    'ZuperAPIError',
    'ZuperAuthenticationError',
    'ZuperRateLimitError',
    'ZuperNotFoundError',
    'ZuperValidationError',
    'ZuperServerError',
    'ZuperNetworkError'
]
