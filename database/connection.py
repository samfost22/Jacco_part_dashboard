"""
Database connection management for EU Parts Job Dashboard.
Handles SQLite connections for local/cloud deployment.
"""

import streamlit as st
import sqlite3
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = "data/jobs.db"


class DatabaseNotConfiguredError(Exception):
    """Raised when database configuration is missing."""
    pass


def get_database_path() -> str:
    """Get the database file path from secrets or use default."""
    try:
        return st.secrets.get("database", {}).get("path", DEFAULT_DB_PATH)
    except Exception:
        return DEFAULT_DB_PATH


def is_database_configured() -> bool:
    """
    Check if database is configured and accessible.
    For SQLite, we check if the database file exists or can be created.
    """
    try:
        db_path = get_database_path()
        # Check if database file exists
        if os.path.exists(db_path):
            return True
        # Check if we can create the directory
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Database configuration check failed: {e}")
        return False


def get_connection() -> sqlite3.Connection:
    """
    Get a SQLite database connection.

    Returns:
        SQLite connection object
    """
    db_path = get_database_path()

    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise DatabaseNotConfiguredError(f"Failed to connect to database: {e}")


def init_database():
    """Initialize the database schema if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Create jobs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_uid TEXT UNIQUE NOT NULL,
            job_number TEXT,
            title TEXT,
            description TEXT,
            job_status TEXT,
            job_category TEXT,
            priority TEXT,
            customer_name TEXT,
            customer_uid TEXT,
            job_address TEXT,
            latitude REAL,
            longitude REAL,
            assigned_technician TEXT,
            technician_uid TEXT,
            scheduled_start_time TEXT,
            scheduled_end_time TEXT,
            actual_start_time TEXT,
            actual_end_time TEXT,
            created_time TEXT,
            modified_time TEXT,
            parts_status TEXT,
            parts_delivered_date TEXT,
            custom_fields TEXT,
            tags TEXT,
            last_synced TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create sync_log table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_started TEXT,
            sync_completed TEXT,
            status TEXT,
            jobs_fetched INTEGER DEFAULT 0,
            jobs_updated INTEGER DEFAULT 0,
            jobs_created INTEGER DEFAULT 0,
            errors TEXT,
            sync_duration_seconds REAL
        )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_job_number ON jobs(job_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_job_status ON jobs(job_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_job_category ON jobs(job_category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_scheduled_start ON jobs(scheduled_start_time)")

        conn.commit()
        logger.info("Database schema initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise
    finally:
        conn.close()


def execute_query(query: str, params: tuple = None, fetch: bool = True):
    """
    Execute a SQL query with automatic connection management.

    Args:
        query: SQL query string
        params: Query parameters (optional)
        fetch: Whether to fetch results (default: True)

    Returns:
        Query results if fetch=True, otherwise None
    """
    # Convert PostgreSQL-style placeholders (%s) to SQLite-style (?)
    query = query.replace('%s', '?')

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if fetch:
            results = cursor.fetchall()
            column_names = [description[0] for description in cursor.description] if cursor.description else []
            conn.commit()
            # Convert Row objects to tuples for compatibility
            results = [tuple(row) for row in results]
            return results, column_names
        else:
            conn.commit()
            return None

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database query error: {e}")
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def execute_many(query: str, data: list):
    """
    Execute a query with multiple parameter sets (batch insert/update).

    Args:
        query: SQL query string with parameter placeholders
        data: List of parameter tuples

    Returns:
        Number of rows affected
    """
    # Convert PostgreSQL-style placeholders (%s) to SQLite-style (?)
    query = query.replace('%s', '?')

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.executemany(query, data)
        rows_affected = cursor.rowcount

        conn.commit()
        return rows_affected

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database batch operation error: {e}")
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Legacy compatibility - kept for backward compatibility with existing code
def get_db_connection():
    """
    Legacy function for backward compatibility.
    Returns a module-like object with get_connection method.
    """
    class DBConnectionWrapper:
        @staticmethod
        def get_connection():
            return get_connection()

        @staticmethod
        def return_connection(conn):
            if conn:
                conn.close()

    return DBConnectionWrapper()
