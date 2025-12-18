"""
Database module for EU Parts Job Dashboard.
Uses SQLite for local data storage.
"""

from database.connection import (
    get_db_connection,
    execute_query,
    execute_many,
    is_database_configured,
    DatabaseNotConfiguredError
)
from database.queries import JobQueries

__all__ = [
    'get_db_connection',
    'execute_query',
    'execute_many',
    'is_database_configured',
    'DatabaseNotConfiguredError',
    'JobQueries'
]
