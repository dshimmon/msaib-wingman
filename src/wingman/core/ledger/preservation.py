"""Semantic and byte-preservation evidence for Ledger transitions."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from wingman.core.ledger.models import serialize_json
from wingman.core.ledger.readiness import canonical_json_bytes
from wingman.core.ledger.source_repository import list_sources


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _encoded_value(value):
    if isinstance(value, bytes):
        return {"encoding": "base64", "value": base64.b64encode(value).decode()}
    return value


def _table_snapshot(connection, table):
    columns = [
        row["name"]
        for row in connection.execute(f'PRAGMA table_xinfo("{table}")')
        if row["hidden"] == 0
    ]
    quoted = ", ".join(f'"{column}"' for column in columns)
    type_fields = ", ".join(
        f'typeof("{column}") AS "__type_{index}"'
        for index, column in enumerate(columns)
    )
    rows = connection.execute(
        f'SELECT {quoted}, {type_fields} FROM "{table}"'
    ).fetchall()
    encoded = []
    for row in rows:
        record = [
            {
                "column": column,
                "storage_class": row[f"__type_{index}"],
                "value": _encoded_value(row[column]),
            }
            for index, column in enumerate(columns)
        ]
        encoded.append(record)
    return sorted(encoded, key=canonical_json_bytes)


def capture_preservation_state(
    connection,
    *,
    non_ledger_paths=(),
):
    """Capture complete values, storage classes, public records, and bytes."""
    tables = [
        row["name"]
        for row in connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
    ]
    legacy_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(sources)")
    }
    source_storage = []
    if {"program", "academic_year"}.issubset(legacy_columns):
        source_storage = [
            dict(row)
            for row in connection.execute(
                """
                SELECT e.entity_id, e.metadata_json,
                       s.program, s.academic_year
                FROM entities AS e
                JOIN sources AS s ON s.entity_id = e.entity_id
                ORDER BY e.entity_id
                """
            ).fetchall()
        ]
    else:
        source_storage = [
            {
                "entity_id": row["entity_id"],
                "metadata_json": row["metadata_json"],
            }
            for row in connection.execute(
                """
                SELECT e.entity_id, e.metadata_json
                FROM entities AS e
                JOIN sources AS s ON s.entity_id = e.entity_id
                ORDER BY e.entity_id
                """
            ).fetchall()
        ]

    return {
        "tables": {
            table: _table_snapshot(connection, table)
            for table in tables
        },
        "public_sources": {
            source.entity_id: asdict(source)
            for source in list_sources(connection)
        },
        "source_storage": source_storage,
        "non_ledger_files": {
            str(Path(path).resolve()): {
                "size": Path(path).stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in non_ledger_paths
        },
    }


def _without_columns(table_rows, excluded):
    return [
        [cell for cell in row if cell["column"] not in excluded]
        for row in table_rows
    ]


def _source_metadata_expectations(before):
    expectations = {}
    allowed = []
    for row in before["source_storage"]:
        raw = row["metadata_json"]
        metadata = json.loads(raw)
        updated = dict(metadata)
        additions = {}
        for key in ("program", "academic_year"):
            if key not in updated and row.get(key) is not None:
                updated[key] = row[key]
                additions[key] = row[key]
        expected_raw = (
            serialize_json(updated, "source metadata", dict)
            if additions
            else raw
        )
        expectations[row["entity_id"]] = expected_raw
        if additions:
            allowed.append(
                {
                    "entity_id": row["entity_id"],
                    "metadata_keys_added": additions,
                }
            )
    return expectations, allowed


def compare_migration_preservation(before, after):
    """Enforce the complete Migration 4 allowed-difference model."""
    if before["non_ledger_files"] != after["non_ledger_files"]:
        raise RuntimeError("A non-Ledger file changed during transition.")
    if before["public_sources"] != after["public_sources"]:
        raise RuntimeError("Public SourceRecord behavior changed.")

    before_tables = before["tables"]
    after_tables = after["tables"]
    common_unchanged = set(before_tables).intersection(after_tables) - {
        "entities",
        "sources",
        "schema_migrations",
    }
    for table in sorted(common_unchanged):
        if before_tables[table] != after_tables[table]:
            raise RuntimeError(f"Ledger table changed unexpectedly: {table}")

    if _without_columns(
        before_tables["sources"],
        {"program", "academic_year"},
    ) != after_tables["sources"]:
        raise RuntimeError("A non-target sources value or storage class changed.")

    expectations, allowed = _source_metadata_expectations(before)
    after_raw = {
        row["entity_id"]: row["metadata_json"]
        for row in after["source_storage"]
    }
    if expectations != after_raw:
        raise RuntimeError("Source metadata bytes violate the fallback model.")

    before_entities = before_tables["entities"]
    after_entities = after_tables["entities"]
    before_by_id = {
        row[0]["value"]: row for row in before_entities
    }
    after_by_id = {
        row[0]["value"]: row for row in after_entities
    }
    if set(before_by_id) != set(after_by_id):
        raise RuntimeError("Ledger entity IDs changed during transition.")
    source_ids = set(expectations)
    for entity_id in before_by_id:
        before_row = before_by_id[entity_id]
        after_row = after_by_id[entity_id]
        if entity_id not in source_ids:
            if before_row != after_row:
                raise RuntimeError("A non-source entity changed during transition.")
            continue
        for before_cell, after_cell in zip(before_row, after_row):
            if before_cell["column"] == "metadata_json":
                continue
            if before_cell != after_cell:
                raise RuntimeError("A non-target source entity value changed.")

    before_history = before_tables["schema_migrations"]
    after_history = after_tables["schema_migrations"]
    if after_history[: len(before_history)] != before_history:
        raise RuntimeError("Released migration history changed.")
    if len(after_history) != len(before_history) + 1:
        raise RuntimeError("Migration 4 history was not appended exactly once.")

    manifest = {
        "schema_version": 1,
        "result": "preserved",
        "allowed_differences": {
            "removed_source_columns": ["program", "academic_year"],
            "metadata_fallbacks": allowed,
            "migration_history_append": 4,
        },
        "public_source_record_count": len(before["public_sources"]),
        "non_ledger_files": before["non_ledger_files"],
    }
    manifest["sha256"] = hashlib.sha256(
        canonical_json_bytes(manifest)
    ).hexdigest()
    return manifest
