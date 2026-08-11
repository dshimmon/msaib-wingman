"""Durably journaled Ledger restoration and incomplete-recovery handling."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
from datetime import datetime, timezone

from wingman.core.ledger.backup import (
    _copy_exclusive,
    checkpoint_for_backup,
    fsync_directory,
    load_and_validate_backup,
)
from wingman.core.ledger.locking import (
    LedgerFileLock,
    canonical_database_path,
    recovery_journal_path_for,
)
from wingman.core.ledger.preservation import sha256_file
from wingman.core.ledger.readiness import (
    canonical_json_bytes,
    open_read_only_database,
    validate_readiness,
)


_RECOVERY_FIELDS = {
    "schema_version", "record_type", "operation", "run_id", "target",
    "backup", "backup_sha256", "phase", "events", "staging", "failed",
    "expected_version",
}
_RECOVERY_PHASES = {
    "backup_verified", "migration_committed", "prepared",
    "staging_validated", "failed_preserved", "candidate_installed",
    "result_validated",
}


def _write_all(descriptor, payload):
    offset = 0
    while offset < len(payload):
        offset += os.write(descriptor, payload[offset:])


def _create_journal(database_path, document):
    path = recovery_journal_path_for(database_path)
    payload = canonical_json_bytes(document) + b"\n"
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    fsync_directory(path.parent)
    return path


def _update_journal(path, document):
    temporary = path.with_name(
        f"{path.name}.update-{document['run_id']}"
    )
    payload = canonical_json_bytes(document) + b"\n"
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    fsync_directory(path.parent)


def _load_recovery_journal(path):
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError("Recovery journal contains duplicate keys.")
            result[key] = value
        return result

    document = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicates,
        parse_constant=lambda value: (_ for _ in ()).throw(
            RuntimeError(f"Invalid recovery JSON constant: {value}")
        ),
    )
    required = {
        "schema_version", "record_type", "operation", "run_id", "target",
        "backup", "backup_sha256", "phase", "events",
    }
    if not required.issubset(document) or not set(document).issubset(
        _RECOVERY_FIELDS
    ):
        raise RuntimeError("Recovery journal shape is invalid.")
    if (
        document["schema_version"] != 1
        or document["record_type"] != "ledger_recovery_journal"
        or document["operation"]
        not in {"migrate", "restore", "rollback", "migration_recovery"}
        or document["phase"] not in _RECOVERY_PHASES
        or not isinstance(document["run_id"], str)
        or not document["run_id"]
        or not isinstance(document["events"], list)
    ):
        raise RuntimeError("Recovery journal controls are invalid.")
    return document


def advance_recovery_journal(path, document, phase, **evidence):
    updated = dict(document)
    updated["phase"] = phase
    events = list(document.get("events", []))
    events.append(
        {
            "phase": phase,
            "at": datetime.now(timezone.utc).isoformat(),
            "evidence": evidence,
        }
    )
    updated["events"] = events
    _update_journal(path, updated)
    return updated


def complete_recovery_journal(path, document, **evidence):
    completed = advance_recovery_journal(
        path,
        document,
        "completed",
        **evidence,
    )
    archive = path.with_name(
        f"{path.name}.completed-{document['run_id']}"
    )
    if archive.exists():
        raise FileExistsError("Completed recovery journal already exists.")
    os.link(path, archive)
    fsync_directory(path.parent)
    path.unlink()
    fsync_directory(path.parent)
    return completed, archive


def start_migration_journal(
    database_path,
    *,
    run_id,
    backup_path,
    backup_manifest,
):
    target = canonical_database_path(database_path, reject_alias=True)
    document = {
        "schema_version": 1,
        "record_type": "ledger_recovery_journal",
        "operation": "migrate",
        "run_id": run_id,
        "target": str(target),
        "backup": str(canonical_database_path(backup_path, reject_alias=True)),
        "backup_sha256": backup_manifest["backup"]["sha256"],
        "phase": "backup_verified",
        "events": [
            {
                "phase": "backup_verified",
                "at": datetime.now(timezone.utc).isoformat(),
                "evidence": {
                    "backup_size": backup_manifest["backup"]["size"],
                },
            }
        ],
    }
    path = _create_journal(target, document)
    return path, document


def _restore_paths(target, run_id):
    return (
        target.with_name(f".{target.name}.restore-{run_id}"),
        target.with_name(f"{target.name}.failed-{run_id}"),
    )


def _validate_candidate(path, expected_version=None):
    connection = open_read_only_database(path)
    try:
        return validate_readiness(
            connection,
            database_path=path,
            expected_version=expected_version,
            allow_recovery=True,
        )
    finally:
        connection.close()


def restore_backup_locked(
    connection,
    database_path,
    backup_path,
    *,
    run_id,
    operation="restore",
    phase_hook=None,
    existing_journal=None,
):
    """Install a verified backup while preserving the failed target forever."""
    target = canonical_database_path(database_path, reject_alias=True)
    backup = canonical_database_path(backup_path, reject_alias=True)
    backup_manifest = load_and_validate_backup(backup)
    expected_version = backup_manifest["source"]["readiness"]["schema_version"]
    staging, failed = _restore_paths(target, run_id)
    if existing_journal is None:
        checkpoint_for_backup(connection, target)
        if staging.exists() or failed.exists():
            raise RuntimeError("Restoration target artifacts already exist.")
        document = {
            "schema_version": 1,
            "record_type": "ledger_recovery_journal",
            "operation": operation,
            "run_id": run_id,
            "target": str(target),
            "backup": str(backup),
            "backup_sha256": backup_manifest["backup"]["sha256"],
            "staging": str(staging),
            "failed": str(failed),
            "expected_version": expected_version,
            "phase": "prepared",
            "events": [
                {
                    "phase": "prepared",
                    "at": datetime.now(timezone.utc).isoformat(),
                    "evidence": {},
                }
            ],
        }
        journal_path = _create_journal(target, document)
        if phase_hook:
            phase_hook("prepared")
    else:
        journal_path, document = existing_journal
        if (
            document.get("target") != str(target)
            or document.get("backup") != str(backup)
            or document.get("run_id") != run_id
            or document.get("backup_sha256")
            != backup_manifest["backup"]["sha256"]
        ):
            raise RuntimeError("Recovery journal binding is invalid.")

    phase = document["phase"]
    if phase == "prepared":
        if not staging.exists():
            _copy_exclusive(backup, staging)
        if (
            staging.stat().st_size != backup_manifest["backup"]["size"]
            or sha256_file(staging) != backup_manifest["backup"]["sha256"]
        ):
            raise RuntimeError("Restoration staging bytes are corrupt.")
        readiness = _validate_candidate(staging, expected_version)
        document = advance_recovery_journal(
            journal_path,
            document,
            "staging_validated",
            readiness=readiness,
        )
        if phase_hook:
            phase_hook("staging_validated")
        phase = document["phase"]

    if phase == "staging_validated":
        if target.exists() and not failed.exists():
            os.link(target, failed)
            fsync_directory(target.parent)
        elif target.exists() and failed.exists():
            if not os.path.samefile(target, failed):
                raise RuntimeError(
                    "Target differs from its incomplete failed preservation."
                )
        elif not failed.exists():
            raise RuntimeError("Original Ledger was not preserved.")
        document = advance_recovery_journal(
            journal_path,
            document,
            "failed_preserved",
            failed_size=failed.stat().st_size,
            failed_sha256=sha256_file(failed),
        )
        if phase_hook:
            phase_hook("failed_preserved")
        phase = document["phase"]

    if phase == "failed_preserved":
        if staging.exists():
            if target.exists() and failed.exists() and not os.path.samefile(
                target,
                failed,
            ):
                raise RuntimeError("Restoration file state is ambiguous.")
            os.replace(staging, target)
            fsync_directory(target.parent)
        elif (
            not target.exists()
            or not failed.exists()
            or os.path.samefile(target, failed)
        ):
            raise RuntimeError("Atomic restoration candidate is missing.")
        os.chmod(failed, 0o444)
        failed_descriptor = os.open(failed, os.O_RDONLY)
        try:
            os.fsync(failed_descriptor)
        finally:
            os.close(failed_descriptor)
        fsync_directory(target.parent)
        if sha256_file(target) != backup_manifest["backup"]["sha256"]:
            raise RuntimeError("Atomically installed Ledger differs from backup.")
        if target.stat().st_ino == failed.stat().st_ino:
            raise RuntimeError("Restored and failed Ledgers share an inode.")
        if staging.exists():
            raise RuntimeError("Restoration staging survived atomic install.")
        if target.stat().st_nlink != 1 or failed.stat().st_nlink != 1:
            raise RuntimeError("Restoration file identity is ambiguous.")
        if target.stat().st_mode & 0o222 == 0:
            os.chmod(target, 0o600)
            fsync_directory(target.parent)
        document = advance_recovery_journal(
            journal_path,
            document,
            "candidate_installed",
            installed_size=target.stat().st_size,
            installed_sha256=sha256_file(target),
        )
        if phase_hook:
            phase_hook("candidate_installed")
        phase = document["phase"]

    if phase == "candidate_installed":
        readiness = _validate_candidate(target, expected_version)
        if sha256_file(target) != backup_manifest["backup"]["sha256"]:
            raise RuntimeError("Installed Ledger differs from verified backup.")
        document = advance_recovery_journal(
            journal_path,
            document,
            "result_validated",
            readiness=readiness,
        )
        if phase_hook:
            phase_hook("result_validated")
        phase = document["phase"]

    if phase == "result_validated":
        document, archive = complete_recovery_journal(
            journal_path,
            document,
            installed_sha256=sha256_file(target),
        )
        if phase_hook:
            phase_hook("completed")
        return {
            "status": "restored",
            "target": str(target),
            "failed_database": str(failed),
            "journal": str(archive),
            "readiness": document["events"][-2]["evidence"]["readiness"],
        }
    raise RuntimeError(f"Unknown restoration recovery phase: {phase}")


def recover_incomplete(database_path, *, phase_hook=None):
    """Continue an interrupted restore or safely reverse an interrupted migration."""
    target = canonical_database_path(database_path, reject_alias=True)
    journal_path = recovery_journal_path_for(target)
    if not journal_path.exists():
        raise RuntimeError("No incomplete Ledger recovery exists.")
    if journal_path.is_symlink():
        raise RuntimeError("Recovery journal path is a symlink alias.")
    journal_info = journal_path.stat()
    if (
        not stat.S_ISREG(journal_info.st_mode)
        or journal_info.st_nlink != 1
    ):
        raise RuntimeError("Recovery journal identity is unsafe.")
    document = _load_recovery_journal(journal_path)
    if document.get("target") != str(target):
        raise RuntimeError("Recovery journal target does not match.")

    with LedgerFileLock(target, "exclusive"):
        connection = None
        operation = document.get("operation")
        if operation == "migrate":
            backup = canonical_database_path(document["backup"], reject_alias=True)
            backup_manifest = load_and_validate_backup(backup)
            if (
                backup_manifest["backup"]["sha256"]
                != document["backup_sha256"]
            ):
                raise RuntimeError("Recovery backup binding is invalid.")
            current_version = None
            if target.exists():
                connection = sqlite3.connect(target, isolation_level=None)
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute("PRAGMA busy_timeout = 5000")
                try:
                    current_version = validate_readiness(
                        connection,
                        database_path=target,
                        allow_recovery=True,
                    )["schema_version"]
                except RuntimeError:
                    current_version = None
            if (
                current_version == 3
                and sha256_file(target) == backup_manifest["backup"]["sha256"]
            ):
                completed, archive = complete_recovery_journal(
                    journal_path,
                    document,
                    recovery="pre_transition_state_unchanged",
                )
                connection.close()
                return {
                    "status": "recovered_without_restore",
                    "journal": str(archive),
                    "phase": completed["phase"],
                }
            if connection is not None:
                # A committed migration may still live in the WAL. Flush it
                # into the failed target and close before installing the
                # backup, or the later close could replay v4 pages into the
                # restored v3 pathname.
                checkpoint_for_backup(connection, target)
                connection.close()
                connection = None
            document = advance_recovery_journal(
                journal_path,
                document,
                "prepared",
                recovery="restore_verified_backup",
            )
            staging, failed = _restore_paths(target, document["run_id"])
            document.update(
                {
                    "operation": "migration_recovery",
                    "staging": str(staging),
                    "failed": str(failed),
                    "expected_version": 3,
                }
            )
            _update_journal(journal_path, document)

        try:
            return restore_backup_locked(
                connection,
                target,
                document["backup"],
                run_id=document["run_id"],
                operation=document["operation"],
                phase_hook=phase_hook,
                existing_journal=(journal_path, document),
            )
        finally:
            if connection is not None:
                connection.close()
