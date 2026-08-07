"""
Creates configured SQLite connections and transactions.
"""

import os
import sqlite3
from contextlib import contextmanager
from functools import wraps
from pathlib import Path


DEFAULT_LEDGER_PATH = Path(
    "data/ledger/wingman-ledger.sqlite3"
)
LEDGER_PATH_ENVIRONMENT_VARIABLE = (
    "WINGMAN_LEDGER_PATH"
)


def get_database_path():
    """
    Return the configured Ledger database path.
    """
    configured_path = os.getenv(
        LEDGER_PATH_ENVIRONMENT_VARIABLE
    )

    if configured_path:
        return Path(configured_path)

    return DEFAULT_LEDGER_PATH


def connect_database(database_path=None):
    """
    Open a configured Ledger SQLite connection.
    """
    path = Path(
        database_path
        if database_path is not None
        else get_database_path()
    )
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        path,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )
    connection.execute(
        "PRAGMA journal_mode = WAL"
    )
    connection.execute(
        "PRAGMA busy_timeout = 5000"
    )

    return connection


def require_transaction(connection):
    """
    Require repository mutations to join an active transaction.
    """
    if not connection.in_transaction:
        raise RuntimeError(
            "Ledger repository writes require "
            "an active transaction."
        )


def atomic_repository_write(function):
    """
    Roll back one repository mutation without committing its caller.
    """
    savepoint_name = (
        "ledger_"
        + function.__module__.replace(".", "_")
        + "_"
        + function.__name__
    )

    @wraps(function)
    def wrapped(connection, *args, **kwargs):
        require_transaction(connection)
        connection.execute(
            f"SAVEPOINT {savepoint_name}"
        )

        try:
            result = function(
                connection,
                *args,
                **kwargs,
            )
        except Exception:
            connection.execute(
                f"ROLLBACK TO SAVEPOINT {savepoint_name}"
            )
            connection.execute(
                f"RELEASE SAVEPOINT {savepoint_name}"
            )
            raise
        else:
            connection.execute(
                f"RELEASE SAVEPOINT {savepoint_name}"
            )
            return result

    return wrapped


@contextmanager
def transaction(connection):
    """
    Commit a transaction on success and roll it back on failure.
    """
    if connection.in_transaction:
        raise RuntimeError(
            "A Ledger transaction is already active."
        )

    connection.execute("BEGIN")

    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
