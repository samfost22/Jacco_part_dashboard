"""
Database connection management for EU Parts Job Dashboard.
Handles PostgreSQL connections using connection pooling.
"""

import streamlit as st
import psycopg2
from psycopg2 import pool
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages database connection pool for the application."""

    _connection_pool: Optional[pool.SimpleConnectionPool] = None

    @classmethod
    def initialize_pool(cls, min_connections: int = 1, max_connections: int = 10):
        """
        Initialize the database connection pool.

        Args:
            min_connections: Minimum number of connections in the pool
            max_connections: Maximum number of connections in the pool
        """
        if cls._connection_pool is not None:
            logger.warning("Connection pool already initialized")
            return

        try:
            db_config = st.secrets["database"]

            cls._connection_pool = psycopg2.pool.SimpleConnectionPool(
                min_connections,
                max_connections,
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"]
            )
            logger.info("Database connection pool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise

    @classmethod
    def get_connection(cls):
        """
        Get a connection from the pool.

        Returns:
            A database connection from the pool
        """
        if cls._connection_pool is None:
            cls.initialize_pool()

        try:
            return cls._connection_pool.getconn()
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise

    @classmethod
    def return_connection(cls, connection):
        """
        Return a connection to the pool.

        Args:
            connection: The connection to return to the pool
        """
        if cls._connection_pool is not None and connection is not None:
            cls._connection_pool.putconn(connection)

    @classmethod
    def close_all_connections(cls):
        """Close all connections in the pool."""
        if cls._connection_pool is not None:
            cls._connection_pool.closeall()
            cls._connection_pool = None
            logger.info("All database connections closed")


@st.cache_resource
def get_db_connection():
    """
    Streamlit cached resource for database connection.
    This ensures the connection pool is initialized once and reused.

    Returns:
        DatabaseConnection class for managing connections
    """
    DatabaseConnection.initialize_pool()
    return DatabaseConnection


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
    db = get_db_connection()
    conn = None
    cursor = None

    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if fetch:
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            conn.commit()
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
            db.return_connection(conn)


def execute_many(query: str, data: list):
    """
    Execute a query with multiple parameter sets (batch insert/update).

    Args:
        query: SQL query string with parameter placeholders
        data: List of parameter tuples

    Returns:
        Number of rows affected
    """
    db = get_db_connection()
    conn = None
    cursor = None

    try:
        conn = db.get_connection()
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
            db.return_connection(conn)
