"""
Product-neutral SQLite persistence for Wingman OS.
"""

from wingman.core.ledger.database import (
    connect_database,
    get_database_path,
    require_transaction,
    transaction,
)
from wingman.core.ledger.migrations import apply_migrations


__all__ = [
    "apply_migrations",
    "connect_database",
    "get_database_path",
    "require_transaction",
    "transaction",
]
