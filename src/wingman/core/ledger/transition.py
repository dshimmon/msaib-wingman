"""Authorized Migration 4, restoration, rollback, and recovery orchestration."""

from __future__ import annotations

from wingman.core.ledger.authorization import (
    consume_authorization,
    validate_authorization,
    validate_exact_target,
)
from wingman.core.ledger.backup import create_immutable_backup_locked
from wingman.core.ledger.database import exclusive_connection
from wingman.core.ledger.migrations import apply_migrations
from wingman.core.ledger.preservation import (
    capture_preservation_state,
    compare_migration_preservation,
)
from wingman.core.ledger.readiness import validate_readiness
from wingman.core.ledger.recovery import (
    advance_recovery_journal,
    complete_recovery_journal,
    recover_incomplete,
    restore_backup_locked,
    start_migration_journal,
)


def execute_authorized_transition(
    manifest_path,
    receipt_path,
    *,
    non_ledger_paths=(),
    _phase_hook=None,
):
    """Execute exactly the manifest operation; no SQL or migration is selectable."""
    manifest, receipt = validate_authorization(
        manifest_path,
        receipt_path,
        operation=manifest_operation(manifest_path),
    )
    operation = manifest["permitted_operation"]
    target_path = manifest["target"]["identity"]["canonical_path"]
    with exclusive_connection(target_path) as connection:
        target = validate_exact_target(manifest, connection=connection)
        consume_authorization(receipt_path, receipt)

        if operation in {"restore", "rollback"}:
            return restore_backup_locked(
                connection,
                target,
                manifest["backup_destination"],
                run_id=manifest["run_id"],
                operation=operation,
                phase_hook=_phase_hook,
            )

        readiness = validate_readiness(
            connection,
            database_path=target,
            expected_version=3,
        )
        before = capture_preservation_state(
            connection,
            non_ledger_paths=non_ledger_paths,
        )
        backup_manifest = create_immutable_backup_locked(
            connection,
            target,
            manifest["backup_destination"],
            run_id=manifest["run_id"],
            expected_source_identity=manifest["target"]["inventory"]["database"],
        )
        journal_path, journal = start_migration_journal(
            target,
            run_id=manifest["run_id"],
            backup_path=manifest["backup_destination"],
            backup_manifest=backup_manifest,
        )
        if _phase_hook:
            _phase_hook("backup_verified")

        apply_migrations(
            connection,
            target_version=4,
            allow_existing_transition=True,
        )
        journal = advance_recovery_journal(
            journal_path,
            journal,
            "migration_committed",
        )
        if _phase_hook:
            _phase_hook("migration_committed")

        after_readiness = validate_readiness(
            connection,
            database_path=target,
            expected_version=4,
            allow_recovery=True,
        )
        after = capture_preservation_state(
            connection,
            non_ledger_paths=non_ledger_paths,
        )
        preservation = compare_migration_preservation(before, after)
        journal = advance_recovery_journal(
            journal_path,
            journal,
            "result_validated",
            preservation=preservation,
        )
        if _phase_hook:
            _phase_hook("result_validated")
        _, archive = complete_recovery_journal(
            journal_path,
            journal,
            final_schema=after_readiness,
        )
        if _phase_hook:
            _phase_hook("completed")
        return {
            "status": "migrated",
            "before": readiness,
            "after": after_readiness,
            "backup": backup_manifest,
            "preservation": preservation,
            "journal": str(archive),
        }


def manifest_operation(manifest_path):
    """Read only the operation for the strict validation dispatch."""
    import json
    from pathlib import Path

    document = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    operation = document.get("permitted_operation")
    if operation not in {"migrate", "restore", "rollback"}:
        raise ValueError("Ledger operation is not permitted.")
    return operation


__all__ = [
    "execute_authorized_transition",
    "recover_incomplete",
]
