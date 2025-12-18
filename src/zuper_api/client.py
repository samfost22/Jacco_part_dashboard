"""
Zuper API client for fetching job data.
This is a READ-ONLY client that only fetches data from Zuper API.
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time
import streamlit as st

from src.zuper_api.exceptions import (
    ZuperAPIError,
    ZuperAuthenticationError,
    ZuperRateLimitError,
    ZuperNotFoundError,
    ZuperValidationError,
    ZuperServerError,
    ZuperNetworkError
)

logger = logging.getLogger(__name__)


class ZuperAPINotConfiguredError(Exception):
    """Raised when Zuper API configuration is missing."""
    pass


def is_zuper_configured() -> bool:
    """Check if Zuper API secrets are configured."""
    try:
        zuper_config = st.secrets.get("zuper", {})
        required_keys = ["api_key", "org_uid", "base_url"]
        return all(key in zuper_config for key in required_keys)
    except Exception:
        return False


class ZuperAPIClient:
    """
    Client for interacting with Zuper API.
    READ-ONLY operations for fetching job data.
    """

    def __init__(self, api_key: str = None, org_uid: str = None, base_url: str = None):
        """
        Initialize Zuper API client.

        Args:
            api_key: Zuper API key (from secrets if not provided)
            org_uid: Organization UID (from secrets if not provided)
            base_url: Base API URL (from secrets if not provided)

        Raises:
            ZuperAPINotConfiguredError: If API secrets are not configured
        """
        if not api_key and not is_zuper_configured():
            raise ZuperAPINotConfiguredError(
                "Zuper API secrets not configured. Please add zuper configuration to Streamlit secrets."
            )

        zuper_config = st.secrets.get("zuper", {})
        self.api_key = api_key or zuper_config.get("api_key")
        self.org_uid = org_uid or zuper_config.get("org_uid")
        self.base_url = base_url or zuper_config.get("base_url")

        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Rate limiting
        self.request_count = 0
        self.request_window_start = time.time()
        self.max_requests_per_minute = 100

    def _handle_rate_limit(self):
        """Handle rate limiting for API requests."""
        self.request_count += 1

        # Reset counter after 60 seconds
        if time.time() - self.request_window_start > 60:
            self.request_count = 1
            self.request_window_start = time.time()

        # If approaching rate limit, wait
        if self.request_count >= self.max_requests_per_minute:
            wait_time = 60 - (time.time() - self.request_window_start)
            if wait_time > 0:
                logger.warning(f"Rate limit approaching, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                self.request_count = 1
                self.request_window_start = time.time()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        json_data: Dict = None,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Zuper API with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON request body
            retry_count: Number of retries for failed requests

        Returns:
            JSON response data

        Raises:
            Various ZuperAPIError exceptions based on error type
        """
        url = f"{self.base_url}/{endpoint}"
        self._handle_rate_limit()

        for attempt in range(retry_count):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=30
                )

                # Handle different HTTP status codes
                if response.status_code == 200:
                    return response.json()

                elif response.status_code == 401:
                    raise ZuperAuthenticationError("Invalid API key or authentication failed")

                elif response.status_code == 404:
                    raise ZuperNotFoundError(f"Resource not found: {endpoint}")

                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit exceeded, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    continue

                elif response.status_code == 400:
                    error_msg = response.json().get('message', 'Validation error')
                    raise ZuperValidationError(f"Validation error: {error_msg}")

                elif 500 <= response.status_code < 600:
                    if attempt < retry_count - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    raise ZuperServerError(f"Server error: {response.status_code}")

                else:
                    raise ZuperAPIError(f"Unexpected status code: {response.status_code}")

            except requests.exceptions.Timeout:
                if attempt < retry_count - 1:
                    logger.warning(f"Request timeout, retrying... (attempt {attempt + 1}/{retry_count})")
                    time.sleep(2 ** attempt)
                    continue
                raise ZuperNetworkError("Request timeout")

            except requests.exceptions.ConnectionError:
                if attempt < retry_count - 1:
                    logger.warning(f"Connection error, retrying... (attempt {attempt + 1}/{retry_count})")
                    time.sleep(2 ** attempt)
                    continue
                raise ZuperNetworkError("Connection error")

            except requests.exceptions.RequestException as e:
                raise ZuperNetworkError(f"Network error: {str(e)}")

        raise ZuperAPIError("Max retries exceeded")

    def get_jobs(
        self,
        page: int = 1,
        page_size: int = 100,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Fetch jobs from Zuper API with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of jobs per page
            filters: Additional filters for jobs

        Returns:
            Dictionary containing jobs data and pagination info
        """
        endpoint = f"organizations/{self.org_uid}/jobs"

        params = {
            "page": page,
            "pageSize": page_size
        }

        if filters:
            params.update(filters)

        logger.info(f"Fetching jobs page {page} with page_size {page_size}")

        return self._make_request("GET", endpoint, params=params)

    def get_job_by_id(self, job_uid: str) -> Dict[str, Any]:
        """
        Fetch a specific job by its UID.

        Args:
            job_uid: Job unique identifier

        Returns:
            Job data dictionary
        """
        endpoint = f"organizations/{self.org_uid}/jobs/{job_uid}"

        logger.info(f"Fetching job {job_uid}")

        return self._make_request("GET", endpoint)

    def get_all_parts_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs with category "Field Requires Parts".
        Handles pagination automatically.

        Returns:
            List of all parts jobs
        """
        all_jobs = []
        page = 1
        page_size = 100

        # Filter for "Field Requires Parts" category
        filters = {
            "jobCategory": "Field Requires Parts"
        }

        logger.info("Starting to fetch all Field Requires Parts jobs")

        while True:
            try:
                response = self.get_jobs(page=page, page_size=page_size, filters=filters)

                jobs = response.get("data", [])
                if not jobs:
                    break

                all_jobs.extend(jobs)

                # Check if there are more pages
                pagination = response.get("pagination", {})
                total_pages = pagination.get("totalPages", 1)

                logger.info(f"Fetched page {page}/{total_pages}, got {len(jobs)} jobs")

                if page >= total_pages:
                    break

                page += 1

            except ZuperAPIError as e:
                logger.error(f"Error fetching jobs on page {page}: {e}")
                break

        logger.info(f"Fetched total of {len(all_jobs)} Field Requires Parts jobs")

        return all_jobs

    def get_eu_parts_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all EU parts jobs (within geographic bounds).
        Filters for:
        - Category: "Field Requires Parts"
        - Location: Europe (35-72°N, -11 to 40°E)

        Returns:
            List of EU parts jobs
        """
        all_parts_jobs = self.get_all_parts_jobs()

        # Filter by EU geographic bounds
        eu_jobs = []
        for job in all_parts_jobs:
            lat = job.get("latitude")
            lon = job.get("longitude")

            if lat is not None and lon is not None:
                # Check if within EU bounds
                if 35 <= lat <= 72 and -11 <= lon <= 40:
                    eu_jobs.append(job)

        logger.info(f"Filtered to {len(eu_jobs)} EU parts jobs from {len(all_parts_jobs)} total")

        return eu_jobs

    def test_connection(self) -> bool:
        """
        Test API connection and authentication.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            endpoint = f"organizations/{self.org_uid}"
            self._make_request("GET", endpoint)
            logger.info("API connection test successful")
            return True
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False


def get_zuper_client() -> ZuperAPIClient:
    """
    Get Zuper API client instance.
    Note: Not cached to allow proper error recovery.

    Returns:
        ZuperAPIClient instance

    Raises:
        ZuperAPINotConfiguredError: If API is not configured
    """
    if not is_zuper_configured():
        raise ZuperAPINotConfiguredError(
            "Zuper API secrets not configured. Please add zuper configuration to Streamlit secrets."
        )
    return ZuperAPIClient()
