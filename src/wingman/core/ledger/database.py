"""
Creates configured SQLite connections and transactions.
"""

import os
import sqlite3
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from wingman.core.ledger.locking import (
    DEFAULT_LOCK_TIMEOUT_SECONDS,
    LedgerFileLock,
    assert_no_active_recovery,
    canonical_database_path,
)


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


class LedgerConnection(sqlite3.Connection):
    """A SQLite connection that owns its cooperative lifetime lock."""

    _ledger_lock = None
    _ledger_path = None

    def close(self):
        ledger_lock = self._ledger_lock
        self._ledger_lock = None
        try:
            super().close()
        finally:
            if ledger_lock is not None:
                ledger_lock.release()


def connect_database(
    database_path=None,
    *,
    lock_mode="shared",
    lock_timeout=DEFAULT_LOCK_TIMEOUT_SECONDS,
    allow_recovery=False,
):
    """
    Open a configured Ledger SQLite connection.
    """
    configured_path = Path(
        database_path
        if database_path is not None
        else get_database_path()
    )
    path = canonical_database_path(
        configured_path,
        create_parent=True,
    )
    if not allow_recovery:
        assert_no_active_recovery(path)

    ledger_lock = LedgerFileLock(
        path,
        lock_mode,
        timeout=lock_timeout,
    ).acquire()

    try:
        # Recovery can begin while an ordinary opener is waiting for its
        # shared lock. Recheck only after the lock is held to close that race.
        if not allow_recovery:
            assert_no_active_recovery(path)
        connection = sqlite3.connect(
            path,
            isolation_level=None,
            factory=LedgerConnection,
        )
    except Exception:
        ledger_lock.release()
        raise
    connection._ledger_lock = ledger_lock
    connection._ledger_path = path
    try:
        connection.row_factory = sqlite3.Row
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        connection.execute(
            "PRAGMA busy_timeout = 5000"
        )
        connection.execute(
            "PRAGMA journal_mode = WAL"
        )
    except Exception:
        connection.close()
        raise

    return connection


@contextmanager
def exclusive_connection(
    database_path,
    *,
    lock_timeout=DEFAULT_LOCK_TIMEOUT_SECONDS,
    allow_recovery=False,
):
    """Open a connection while holding the exclusive application lock."""
    connection = connect_database(
        database_path,
        lock_mode="exclusive",
        lock_timeout=lock_timeout,
        allow_recovery=allow_recovery,
    )
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def exclusive_connection_lock(connection):
    """Require maintenance to start with a managed exclusive lock."""
    ledger_lock = getattr(connection, "_ledger_lock", None)
    if ledger_lock is None or ledger_lock.mode != "exclusive":
        raise RuntimeError(
            "Ledger maintenance requires a connection opened with an "
            "exclusive lock from the outset."
        )
    yield connection


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
def transaction(connection, *, immediate=False):
    """
    Commit on success and roll back on failure.

    Immediate mode acquires SQLite's writer reservation before a caller reads
    state that it will merge and write inside the same transaction.
    """
    if connection.in_transaction:
        raise RuntimeError(
            "A Ledger transaction is already active."
        )

    connection.execute(
        "BEGIN IMMEDIATE" if immediate else "BEGIN"
    )

    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
