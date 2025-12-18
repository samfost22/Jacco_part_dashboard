"""
Database queries for EU Parts Job Dashboard.
All queries are view-only (SELECT statements).
Uses SQLite syntax with ? placeholders.
"""

import logging
import pandas as pd
from typing import List, Dict, Optional, Any
from datetime import datetime
from database.connection import execute_query

logger = logging.getLogger(__name__)


class JobQueries:
    """Database queries for job data."""

    @staticmethod
    def get_all_eu_parts_jobs() -> pd.DataFrame:
        """
        Get all EU parts jobs (within geographic bounds).

        Returns:
            DataFrame with all EU parts jobs
        """
        query = """
        SELECT
            job_uid,
            job_number,
            title,
            description,
            job_status,
            job_category,
            priority,
            customer_name,
            customer_uid,
            job_address,
            latitude,
            longitude,
            assigned_technician,
            technician_uid,
            scheduled_start_time,
            scheduled_end_time,
            actual_start_time,
            actual_end_time,
            created_time,
            modified_time,
            parts_status,
            parts_delivered_date,
            custom_fields,
            tags,
            last_synced
        FROM jobs
        WHERE
            job_category = 'Field Requires Parts'
            AND latitude BETWEEN 35 AND 72
            AND longitude BETWEEN -11 AND 40
        ORDER BY scheduled_start_time DESC
        """

        try:
            results, columns = execute_query(query)
            df = pd.DataFrame(results, columns=columns)
            return df
        except Exception as e:
            logger.error(f"Error fetching EU parts jobs: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_jobs_by_status(statuses: List[str]) -> pd.DataFrame:
        """
        Get EU parts jobs filtered by status.

        Args:
            statuses: List of job statuses to filter by

        Returns:
            DataFrame with filtered jobs
        """
        if not statuses:
            return pd.DataFrame()

        placeholders = ','.join(['?'] * len(statuses))
        query = f"""
        SELECT
            job_uid,
            job_number,
            title,
            description,
            job_status,
            job_category,
            priority,
            customer_name,
            customer_uid,
            job_address,
            latitude,
            longitude,
            assigned_technician,
            technician_uid,
            scheduled_start_time,
            scheduled_end_time,
            actual_start_time,
            actual_end_time,
            created_time,
            modified_time,
            parts_status,
            parts_delivered_date,
            custom_fields,
            tags,
            last_synced
        FROM jobs
        WHERE
            job_category = 'Field Requires Parts'
            AND latitude BETWEEN 35 AND 72
            AND longitude BETWEEN -11 AND 40
            AND job_status IN ({placeholders})
        ORDER BY scheduled_start_time DESC
        """

        try:
            results, columns = execute_query(query, tuple(statuses))
            df = pd.DataFrame(results, columns=columns)
            return df
        except Exception as e:
            logger.error(f"Error fetching jobs by status: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_job_by_number(job_number: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific job by job number.

        Args:
            job_number: The job number to search for

        Returns:
            Dictionary with job data or None if not found
        """
        query = """
        SELECT
            job_uid,
            job_number,
            title,
            description,
            job_status,
            job_category,
            priority,
            customer_name,
            customer_uid,
            job_address,
            latitude,
            longitude,
            assigned_technician,
            technician_uid,
            scheduled_start_time,
            scheduled_end_time,
            actual_start_time,
            actual_end_time,
            created_time,
            modified_time,
            parts_status,
            parts_delivered_date,
            custom_fields,
            tags,
            last_synced
        FROM jobs
        WHERE
            job_number = ?
            AND job_category = 'Field Requires Parts'
            AND latitude BETWEEN 35 AND 72
            AND longitude BETWEEN -11 AND 40
        """

        try:
            results, columns = execute_query(query, (job_number,))
            if results:
                return dict(zip(columns, results[0]))
            return None
        except Exception as e:
            logger.error(f"Error fetching job by number: {e}")
            return None

    @staticmethod
    def get_job_by_uid(job_uid: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific job by job UID.

        Args:
            job_uid: The job UID to search for

        Returns:
            Dictionary with job data or None if not found
        """
        query = """
        SELECT
            job_uid,
            job_number,
            title,
            description,
            job_status,
            job_category,
            priority,
            customer_name,
            customer_uid,
            job_address,
            latitude,
            longitude,
            assigned_technician,
            technician_uid,
            scheduled_start_time,
            scheduled_end_time,
            actual_start_time,
            actual_end_time,
            created_time,
            modified_time,
            parts_status,
            parts_delivered_date,
            custom_fields,
            tags,
            last_synced
        FROM jobs
        WHERE job_uid = ?
        """

        try:
            results, columns = execute_query(query, (job_uid,))
            if results:
                return dict(zip(columns, results[0]))
            return None
        except Exception as e:
            logger.error(f"Error fetching job by UID: {e}")
            return None

    @staticmethod
    def get_jobs_by_numbers(job_numbers: List[str]) -> pd.DataFrame:
        """
        Get multiple jobs by job numbers (bulk lookup).

        Args:
            job_numbers: List of job numbers to search for

        Returns:
            DataFrame with matching jobs
        """
        if not job_numbers:
            return pd.DataFrame()

        placeholders = ','.join(['?'] * len(job_numbers))
        query = f"""
        SELECT
            job_uid,
            job_number,
            title,
            description,
            job_status,
            job_category,
            priority,
            customer_name,
            customer_uid,
            job_address,
            latitude,
            longitude,
            assigned_technician,
            technician_uid,
            scheduled_start_time,
            scheduled_end_time,
            actual_start_time,
            actual_end_time,
            created_time,
            modified_time,
            parts_status,
            parts_delivered_date,
            custom_fields,
            tags,
            last_synced
        FROM jobs
        WHERE
            job_number IN ({placeholders})
            AND job_category = 'Field Requires Parts'
            AND latitude BETWEEN 35 AND 72
            AND longitude BETWEEN -11 AND 40
        ORDER BY scheduled_start_time DESC
        """

        try:
            results, columns = execute_query(query, tuple(job_numbers))
            df = pd.DataFrame(results, columns=columns)
            return df
        except Exception as e:
            logger.error(f"Error fetching jobs by numbers: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_job_statistics() -> Dict[str, Any]:
        """
        Get summary statistics for EU parts jobs.

        Returns:
            Dictionary with job statistics
        """
        query = """
        SELECT
            COUNT(*) as total_jobs,
            COUNT(DISTINCT job_status) as unique_statuses,
            COUNT(CASE WHEN parts_delivered_date IS NOT NULL THEN 1 END) as parts_delivered_count,
            COUNT(CASE WHEN parts_delivered_date IS NULL THEN 1 END) as parts_pending_count,
            MIN(scheduled_start_time) as earliest_scheduled,
            MAX(scheduled_start_time) as latest_scheduled,
            MAX(last_synced) as last_sync_time
        FROM jobs
        WHERE
            job_category = 'Field Requires Parts'
            AND latitude BETWEEN 35 AND 72
            AND longitude BETWEEN -11 AND 40
        """

        try:
            results, columns = execute_query(query)
            if results:
                return dict(zip(columns, results[0]))
            return {}
        except Exception as e:
            logger.error(f"Error fetching job statistics: {e}")
            return {}

    @staticmethod
    def get_status_counts() -> pd.DataFrame:
        """
        Get count of jobs by status.

        Returns:
            DataFrame with status counts
        """
        query = """
        SELECT
            job_status,
            COUNT(*) as count
        FROM jobs
        WHERE
            job_category = 'Field Requires Parts'
            AND latitude BETWEEN 35 AND 72
            AND longitude BETWEEN -11 AND 40
        GROUP BY job_status
        ORDER BY count DESC
        """

        try:
            results, columns = execute_query(query)
            df = pd.DataFrame(results, columns=columns)
            return df
        except Exception as e:
            logger.error(f"Error fetching status counts: {e}")
            return pd.DataFrame()

    @staticmethod
    def search_jobs(search_term: str) -> pd.DataFrame:
        """
        Search jobs by job number, title, customer name, or address.

        Args:
            search_term: Search term to look for

        Returns:
            DataFrame with matching jobs
        """
        query = """
        SELECT
            job_uid,
            job_number,
            title,
            description,
            job_status,
            job_category,
            priority,
            customer_name,
            customer_uid,
            job_address,
            latitude,
            longitude,
            assigned_technician,
            technician_uid,
            scheduled_start_time,
            scheduled_end_time,
            actual_start_time,
            actual_end_time,
            created_time,
            modified_time,
            parts_status,
            parts_delivered_date,
            custom_fields,
            tags,
            last_synced
        FROM jobs
        WHERE
            job_category = 'Field Requires Parts'
            AND latitude BETWEEN 35 AND 72
            AND longitude BETWEEN -11 AND 40
            AND (
                job_number LIKE ?
                OR title LIKE ?
                OR customer_name LIKE ?
                OR job_address LIKE ?
            )
        ORDER BY scheduled_start_time DESC
        """

        search_pattern = f"%{search_term}%"

        try:
            results, columns = execute_query(
                query,
                (search_pattern, search_pattern, search_pattern, search_pattern)
            )
            df = pd.DataFrame(results, columns=columns)
            return df
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return pd.DataFrame()
