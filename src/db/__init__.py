"""
Database module - database connection and query functions.
"""

from .database import init_db, get_db_connection, ensure_db_exists
from .queries import (
    save_verification,
    get_verification,
    get_recent_verifications,
    delete_verification,
)

__all__ = [
    "init_db",
    "get_db_connection",
    "ensure_db_exists",
    "save_verification",
    "get_verification",
    "get_recent_verifications",
    "delete_verification",
]
