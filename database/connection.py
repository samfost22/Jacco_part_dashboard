"""
Database connection management for EU Parts Job Dashboard.
Handles SQLite connections - no external database server required.
"""

import streamlit as st
import sqlite3
from typing import Optional, List, Tuple, Any
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Database file path
DB_DIR = Path(__file__).parent.parent / "data"
DB_FILE = DB_DIR / "eu_parts_jobs.db"


class DatabaseNotConfiguredError(Exception):
    """Raised when database configuration is missing."""
    pass


def get_db_path() -> str:
    """
    Get the database file path, creating directory if needed.

    Returns:
        Path to SQLite database file
    """
    # Create data directory if it doesn't exist
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return str(DB_FILE)


def is_database_configured() -> bool:
    """
    Check if database is available.
    SQLite is always available - just needs the data directory.

    Returns:
        True (SQLite requires no configuration)
    """
    return True


@st.cache_resource
def get_db_connection():
    """
    Get a SQLite database connection.
    Cached as a Streamlit resource to persist across reruns.

    Returns:
        SQLite connection object
    """
    db_path = get_db_path()
    logger.info(f"Connecting to SQLite database at {db_path}")

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows

    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")

    # Initialize database schema if needed
    _initialize_schema(conn)

    return conn


def _initialize_schema(conn: sqlite3.Connection):
    """
    Initialize the database schema if tables don't exist.

    Args:
        conn: SQLite connection
    """
    cursor = conn.cursor()

    # Check if jobs table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='jobs'
    """)

    if cursor.fetchone() is None:
        logger.info("Initializing database schema...")
        schema_file = Path(__file__).parent / "schema.sql"

        if schema_file.exists():
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
            logger.info("Database schema initialized successfully")
        else:
            logger.warning(f"Schema file not found: {schema_file}")
    else:
        # Run migrations for existing database
        _run_migrations(conn)

    cursor.close()


def _run_migrations(conn: sqlite3.Connection):
    """
    Run database migrations for schema updates.

    Args:
        conn: SQLite connection
    """
    cursor = conn.cursor()

    # Check if asset_name column exists, add if not
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'asset_name' not in columns:
        logger.info("Running migration: Adding asset_name column...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN asset_name TEXT")
        conn.commit()
        logger.info("Migration complete: asset_name column added")

    if 'asset_uid' not in columns:
        logger.info("Running migration: Adding asset_uid column...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN asset_uid TEXT")
        conn.commit()
        logger.info("Migration complete: asset_uid column added")

    cursor.close()


def execute_query(query: str, params: tuple = None, fetch: bool = True) -> Optional[Tuple[List, List[str]]]:
    """
    Execute a SQL query with automatic connection management.

    Args:
        query: SQL query string
        params: Query parameters (optional)
        fetch: Whether to fetch results (default: True)

    Returns:
        Tuple of (results, column_names) if fetch=True, otherwise None
    """
    conn = get_db_connection()
    cursor = None

    try:
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if fetch:
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.commit()
            # Convert Row objects to tuples for compatibility
            results = [tuple(row) for row in results]
            return results, column_names
        else:
            conn.commit()
            return None

    except Exception as e:
        conn.rollback()
        logger.error(f"Database query error: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        raise

    finally:
        if cursor:
            cursor.close()


def execute_many(query: str, data: list) -> int:
    """
    Execute a query with multiple parameter sets (batch insert/update).

    Args:
        query: SQL query string with parameter placeholders
        data: List of parameter tuples

    Returns:
        Number of rows affected
    """
    conn = get_db_connection()
    cursor = None

    try:
        cursor = conn.cursor()
        cursor.executemany(query, data)
        rows_affected = cursor.rowcount
        conn.commit()
        return rows_affected

    except Exception as e:
        conn.rollback()
        logger.error(f"Database batch operation error: {e}")
        raise

    finally:
        if cursor:
            cursor.close()


def close_connection():
    """Close the database connection."""
    try:
        conn = get_db_connection()
        conn.close()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")
