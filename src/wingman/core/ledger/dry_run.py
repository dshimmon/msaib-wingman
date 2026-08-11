"""A genuinely disposable clone-based Ledger transition rehearsal."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from wingman.core.ledger.database import connect_database
from wingman.core.ledger.locking import canonical_database_path
from wingman.core.ledger.migrations import apply_migrations
from wingman.core.ledger.preservation import (
    capture_preservation_state,
    compare_migration_preservation,
    sha256_file,
)
from wingman.core.ledger.readiness import validate_readiness


def run_disposable_dry_run(
    database_path,
    workspace,
    *,
    non_ledger_paths=(),
):
    """Clone a v3 Ledger, migrate only the clone, and preserve evidence."""
    source = canonical_database_path(database_path, reject_alias=True)
    root = canonical_database_path(
        Path(workspace) / "dry-run-root",
        reject_alias=True,
    ).parent
    if root.exists():
        raise FileExistsError("Disposable dry-run workspace already exists.")
    root.mkdir(parents=True, mode=0o700)
    clone = root / "ledger-clone.sqlite3"
    source_before = sha256_file(source)

    source_connection = connect_database(source)
    try:
        source_readiness = validate_readiness(
            source_connection,
            database_path=source,
            expected_version=3,
        )
        clone_connection = sqlite3.connect(clone)
        try:
            source_connection.backup(clone_connection)
            clone_connection.commit()
        finally:
            clone_connection.close()
        clone_descriptor = os.open(clone, os.O_RDONLY)
        try:
            os.fsync(clone_descriptor)
        finally:
            os.close(clone_descriptor)
    finally:
        source_connection.close()

    clone_connection = connect_database(clone, lock_mode="exclusive")
    try:
        before = capture_preservation_state(
            clone_connection,
            non_ledger_paths=non_ledger_paths,
        )
        apply_migrations(
            clone_connection,
            target_version=4,
            allow_existing_transition=True,
        )
        target_readiness = validate_readiness(
            clone_connection,
            database_path=clone,
            expected_version=4,
        )
        after = capture_preservation_state(
            clone_connection,
            non_ledger_paths=non_ledger_paths,
        )
        preservation = compare_migration_preservation(before, after)
    finally:
        clone_connection.close()

    source_after = sha256_file(source)
    if source_before != source_after:
        raise RuntimeError("Disposable dry run changed the source Ledger.")
    report = {
        "schema_version": 1,
        "record_type": "ledger_transition_disposable_dry_run",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "source_checksum_before": source_before,
        "source_checksum_after": source_after,
        "clone": str(clone),
        "source_readiness": source_readiness,
        "target_readiness": target_readiness,
        "preservation": preservation,
        "disposable": True,
        "live_target_writes": False,
    }
    report_path = root / "dry-run-report.json"
    report_path.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
