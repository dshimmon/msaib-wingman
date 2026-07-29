"""
Product-neutral SQLite persistence for Wingman OS.
"""

from ledger.database import (
    connect_database,
    get_database_path,
    require_transaction,
    transaction,
)
from ledger.migrations import apply_migrations


__all__ = [
    "apply_migrations",
    "connect_database",
    "get_database_path",
    "require_transaction",
    "transaction",
]
