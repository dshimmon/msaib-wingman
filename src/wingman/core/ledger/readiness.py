"""Fail-closed Ledger history, schema, metadata, and integrity checks."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
from functools import lru_cache
from pathlib import Path

from wingman.core.ledger.locking import (
    assert_no_active_recovery,
    canonical_database_path,
)
from wingman.core.ledger.migrations import (
    apply_migrations,
    validate_migration_history,
)


SUPPORTED_LEDGER_VERSIONS = (3, 4)
TRANSITION_ARTIFACT_MARKERS = (
    "sources_rebuilt",
    "sources_old",
)


def canonical_json_bytes(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _rows_as_lists(rows):
    return [list(row) for row in rows]


def schema_manifest(connection):
    """Return an exact, deterministic physical-schema description."""
    objects = connection.execute(
        """
        SELECT type, name, tbl_name, sql
        FROM sqlite_master
        WHERE name NOT LIKE 'sqlite_%'
        ORDER BY type, name
        """
    ).fetchall()
    tables = [row["name"] for row in objects if row["type"] == "table"]
    return {
        "objects": _rows_as_lists(objects),
        "tables": {
            table: {
                "columns": _rows_as_lists(
                    connection.execute(
                        f'PRAGMA table_xinfo("{table}")'
                    ).fetchall()
                ),
                "foreign_keys": _rows_as_lists(
                    connection.execute(
                        f'PRAGMA foreign_key_list("{table}")'
                    ).fetchall()
                ),
                "indexes": _rows_as_lists(
                    connection.execute(
                        f'PRAGMA index_list("{table}")'
                    ).fetchall()
                ),
            }
            for table in tables
        },
    }


def schema_fingerprint(connection):
    return hashlib.sha256(
        canonical_json_bytes(schema_manifest(connection))
    ).hexdigest()


@lru_cache(maxsize=2)
def expected_schema_fingerprint(version):
    if version not in SUPPORTED_LEDGER_VERSIONS:
        raise ValueError("Unsupported Ledger schema version.")
    with tempfile.TemporaryDirectory() as directory:
        from wingman.core.ledger.database import connect_database

        path = Path(directory) / "expected.sqlite3"
        connection = connect_database(path, lock_mode="exclusive")
        try:
            apply_migrations(connection, target_version=version)
            return schema_fingerprint(connection)
        finally:
            connection.close()


def _strict_json(value, field_name, expected_types):
    try:
        parsed = json.loads(
            value,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError(constant)
            ),
        )
    except (TypeError, json.JSONDecodeError, ValueError) as error:
        raise RuntimeError(f"{field_name} is not strict JSON.") from error
    if not isinstance(parsed, expected_types):
        names = ", ".join(value.__name__ for value in expected_types)
        raise RuntimeError(f"{field_name} must contain {names}.")


def validate_metadata(connection):
    """Validate every released JSON storage contract without repairing it."""
    contracts = (
        ("entities", "metadata_json", (dict,)),
        ("source_versions", "metadata_json", (dict,)),
        ("briefing_versions", "briefing_json", (dict,)),
        ("briefing_versions", "retrieval_results_json", (list,)),
        ("briefing_versions", "evidence_snapshot_json", (dict, list)),
        ("diagnostic_events", "details_json", (dict,)),
        ("legacy_imports", "details_json", (dict,)),
    )
    for table, column, expected_types in contracts:
        rows = connection.execute(
            f'SELECT rowid, "{column}" FROM "{table}" ORDER BY rowid'
        ).fetchall()
        for row in rows:
            _strict_json(
                row[column],
                f"{table}.{column} row {row['rowid']}",
                expected_types,
            )


def validate_no_transition_artifacts(connection, database_path):
    names = {
        row["name"]
        for row in connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type IN ('table', 'index', 'trigger')
            """
        )
    }
    if names.intersection(TRANSITION_ARTIFACT_MARKERS):
        raise RuntimeError("Ledger contains abandoned transition objects.")

    path = canonical_database_path(database_path)
    prefixes = (
        f".{path.name}.transition-",
        f".{path.name}.restore-",
    )
    for entry in path.parent.iterdir():
        if any(entry.name.startswith(prefix) for prefix in prefixes):
            raise RuntimeError("Ledger has abandoned transition files.")


def validate_readiness(
    connection,
    *,
    database_path=None,
    allowed_versions=SUPPORTED_LEDGER_VERSIONS,
    expected_version=None,
    allow_recovery=False,
):
    """Return bound readiness evidence or fail before maintenance work."""
    path = canonical_database_path(
        database_path
        if database_path is not None
        else getattr(connection, "_ledger_path", "")
    )
    if not allow_recovery:
        assert_no_active_recovery(path)

    version = validate_migration_history(connection)
    if version not in allowed_versions:
        raise RuntimeError("Ledger schema version is outside the reviewed range.")
    if expected_version is not None and version != expected_version:
        raise RuntimeError("Ledger schema version does not match the target.")

    validate_no_transition_artifacts(connection, path)
    fingerprint = schema_fingerprint(connection)
    expected = expected_schema_fingerprint(version)
    if fingerprint != expected:
        raise RuntimeError("Ledger schema fingerprint does not match release.")

    validate_metadata(connection)
    integrity = connection.execute("PRAGMA integrity_check").fetchall()
    if [row[0] for row in integrity] != ["ok"]:
        raise RuntimeError("Ledger integrity check failed.")
    foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_keys:
        raise RuntimeError("Ledger foreign-key readiness check failed.")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("Ledger foreign-key enforcement is disabled.")

    return {
        "schema_version": version,
        "schema_fingerprint": fingerprint,
        "integrity_check": "ok",
        "foreign_key_violations": 0,
        "canonical_path": str(path),
    }


def open_read_only_database(database_path):
    """Open a validation-only SQLite connection without creating files."""
    path = canonical_database_path(database_path)
    connection = sqlite3.connect(
        f"file:{path}?mode=ro&immutable=1",
        uri=True,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
