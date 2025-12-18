"""
Sync Manager for synchronizing Zuper API data with local database.
Handles data synchronization from Zuper to SQLite database.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

from src.zuper_api.client import ZuperAPIClient
from database.connection import execute_query, get_db_connection
from src.zuper_api.exceptions import ZuperAPIError

logger = logging.getLogger(__name__)


class SyncManager:
    """Manages synchronization between Zuper API and local database."""

    def __init__(self, api_client: ZuperAPIClient):
        """
        Initialize sync manager.

        Args:
            api_client: Zuper API client instance
        """
        self.api_client = api_client

    def sync_all_jobs(self) -> Dict[str, Any]:
        """
        Synchronize all EU parts jobs from Zuper API to database.

        Returns:
            Dictionary with sync statistics
        """
        sync_start = datetime.now()
        stats = {
            "started": sync_start,
            "jobs_fetched": 0,
            "jobs_created": 0,
            "jobs_updated": 0,
            "errors": [],
            "status": "running"
        }

        try:
            # Log sync start
            self._log_sync_start(sync_start)

            # Fetch EU parts jobs from API
            logger.info("Fetching EU parts jobs from Zuper API")
            eu_jobs = self.api_client.get_eu_parts_jobs()
            stats["jobs_fetched"] = len(eu_jobs)

            logger.info(f"Fetched {len(eu_jobs)} EU parts jobs from API")

            # Prepare batch upsert
            for job in eu_jobs:
                try:
                    result = self._upsert_job(job)
                    if result == "created":
                        stats["jobs_created"] += 1
                    elif result == "updated":
                        stats["jobs_updated"] += 1
                except Exception as e:
                    error_msg = f"Error upserting job {job.get('jobNumber', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            # Mark sync as completed
            stats["status"] = "completed"
            stats["completed"] = datetime.now()
            stats["duration_seconds"] = (stats["completed"] - sync_start).total_seconds()

            logger.info(
                f"Sync completed: {stats['jobs_created']} created, "
                f"{stats['jobs_updated']} updated, "
                f"{len(stats['errors'])} errors"
            )

        except ZuperAPIError as e:
            stats["status"] = "failed"
            stats["errors"].append(f"API error: {str(e)}")
            logger.error(f"Sync failed due to API error: {e}")

        except Exception as e:
            stats["status"] = "failed"
            stats["errors"].append(f"Unexpected error: {str(e)}")
            logger.error(f"Sync failed due to unexpected error: {e}")

        finally:
            # Log sync completion
            self._log_sync_completion(stats)

        return stats

    def _upsert_job(self, job_data: Dict[str, Any]) -> str:
        """
        Insert or update a job in the database using SQLite upsert.

        Args:
            job_data: Job data from Zuper API

        Returns:
            "created" or "updated" depending on operation
        """
        job_uid = job_data.get("jobUid")

        # Check if job exists
        check_query = "SELECT job_uid FROM jobs WHERE job_uid = ?"
        result, _ = execute_query(check_query, (job_uid,))
        job_exists = bool(result)

        # SQLite INSERT OR REPLACE syntax
        query = """
        INSERT OR REPLACE INTO jobs (
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
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, datetime('now')
        )
        """

        # Convert tags list to JSON string for SQLite
        tags = job_data.get("tags", [])
        if isinstance(tags, list):
            tags = json.dumps(tags)

        # Extract and prepare job data
        params = (
            job_uid,
            job_data.get("jobNumber"),
            job_data.get("title"),
            job_data.get("description"),
            job_data.get("jobStatus"),  # Use job_status, not current_stage
            job_data.get("jobCategory"),
            job_data.get("priority"),
            job_data.get("customerName"),
            job_data.get("customerUid"),
            job_data.get("jobAddress"),
            job_data.get("latitude"),
            job_data.get("longitude"),
            job_data.get("assignedTechnician"),
            job_data.get("technicianUid"),
            self._format_datetime(job_data.get("scheduledStartTime")),
            self._format_datetime(job_data.get("scheduledEndTime")),
            self._format_datetime(job_data.get("actualStartTime")),
            self._format_datetime(job_data.get("actualEndTime")),
            self._format_datetime(job_data.get("createdTime")),
            self._format_datetime(job_data.get("modifiedTime")),
            job_data.get("partsStatus"),
            self._format_datetime(job_data.get("partsDeliveredDate")),
            json.dumps(job_data.get("customFields", {})),
            tags
        )

        execute_query(query, params, fetch=False)

        return "updated" if job_exists else "created"

    def _format_datetime(self, dt_string: Optional[str]) -> Optional[str]:
        """
        Format datetime string for SQLite storage.

        Args:
            dt_string: Datetime string in ISO format

        Returns:
            ISO format datetime string or None
        """
        if not dt_string:
            return None

        try:
            # Handle ISO format with timezone
            if 'T' in dt_string:
                # Remove timezone info if present and parse
                dt_string = dt_string.replace('Z', '+00:00')
                dt = datetime.fromisoformat(dt_string)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return dt_string
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse datetime: {dt_string}, error: {e}")
            return None

    def _log_sync_start(self, sync_time: datetime):
        """
        Log sync start in database.

        Args:
            sync_time: Sync start timestamp
        """
        query = """
        INSERT INTO sync_log (sync_started, status)
        VALUES (?, 'running')
        """

        try:
            execute_query(query, (sync_time.strftime('%Y-%m-%d %H:%M:%S'),), fetch=False)
        except Exception as e:
            logger.error(f"Failed to log sync start: {e}")

    def _log_sync_completion(self, stats: Dict[str, Any]):
        """
        Log sync completion in database.

        Args:
            stats: Sync statistics dictionary
        """
        query = """
        UPDATE sync_log
        SET
            sync_completed = ?,
            status = ?,
            jobs_fetched = ?,
            jobs_updated = ?,
            jobs_created = ?,
            errors = ?
        WHERE sync_started = ?
        """

        error_text = '\n'.join(stats.get("errors", [])) if stats.get("errors") else None
        completed = stats.get("completed")
        completed_str = completed.strftime('%Y-%m-%d %H:%M:%S') if completed else None
        started_str = stats.get("started").strftime('%Y-%m-%d %H:%M:%S') if stats.get("started") else None

        params = (
            completed_str,
            stats.get("status"),
            stats.get("jobs_fetched", 0),
            stats.get("jobs_updated", 0),
            stats.get("jobs_created", 0),
            error_text,
            started_str
        )

        try:
            execute_query(query, params, fetch=False)
        except Exception as e:
            logger.error(f"Failed to log sync completion: {e}")

    def get_last_sync_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the last sync operation.

        Returns:
            Dictionary with last sync info or None
        """
        query = """
        SELECT
            sync_started,
            sync_completed,
            status,
            jobs_fetched,
            jobs_updated,
            jobs_created,
            errors
        FROM sync_log
        ORDER BY sync_started DESC
        LIMIT 1
        """

        try:
            results, columns = execute_query(query)
            if results:
                return dict(zip(columns, results[0]))
            return None
        except Exception as e:
            logger.error(f"Failed to get last sync info: {e}")
            return None
