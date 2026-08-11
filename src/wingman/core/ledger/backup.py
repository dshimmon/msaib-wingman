"""Immutable, verified, WAL-safe Ledger backup publication."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

from wingman.core.ledger.database import exclusive_connection
from wingman.core.ledger.locking import (
    LedgerPathError,
    canonical_database_path,
    database_identity,
)
from wingman.core.ledger.preservation import sha256_file
from wingman.core.ledger.readiness import (
    canonical_json_bytes,
    open_read_only_database,
    validate_readiness,
)


def fsync_directory(path):
    descriptor = os.open(Path(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def ledger_inventory(database_path):
    path = canonical_database_path(database_path)
    inventory = {}
    for label, candidate in (
        ("database", path),
        ("wal", Path(f"{path}-wal")),
        ("shm", Path(f"{path}-shm")),
    ):
        if candidate.is_symlink():
            raise LedgerPathError(f"Ledger {label} sidecar is a symlink.")
        if candidate.exists():
            details = candidate.stat()
            if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
                raise LedgerPathError(
                    f"Ledger {label} sidecar identity is unsafe."
                )
            inventory[label] = {
                "path": str(candidate),
                "exists": True,
                "size": details.st_size,
                "sha256": (
                    None if label == "shm" else sha256_file(candidate)
                ),
                "durable_bytes": label != "shm",
            }
        else:
            inventory[label] = {
                "path": str(candidate),
                "exists": False,
                "size": 0,
                "sha256": None,
                "durable_bytes": label != "shm",
            }
    return inventory


def checkpoint_for_backup(connection, database_path):
    """Checkpoint all durable bytes and prove no WAL pages remain."""
    row = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if row is None or row[0] != 0 or row[1] != 0 or row[2] != 0:
        raise RuntimeError("Ledger WAL did not reach quiescent truncation.")
    inventory = ledger_inventory(database_path)
    if inventory["wal"]["exists"] and inventory["wal"]["size"] != 0:
        raise RuntimeError("Ledger WAL contains uncheckpointed bytes.")
    return inventory


def _copy_exclusive(source, destination, mode=0o600):
    source_descriptor = os.open(source, os.O_RDONLY)
    try:
        destination_descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            mode,
        )
        try:
            while True:
                block = os.read(source_descriptor, 1024 * 1024)
                if not block:
                    break
                offset = 0
                while offset < len(block):
                    offset += os.write(destination_descriptor, block[offset:])
            os.fsync(destination_descriptor)
        finally:
            os.close(destination_descriptor)
    finally:
        os.close(source_descriptor)


def _publish_file_without_overwrite(temporary, destination, *, read_only):
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    if read_only:
        os.chmod(temporary, 0o444)
    os.link(temporary, destination)
    fsync_directory(destination.parent)
    temporary.unlink()
    fsync_directory(destination.parent)


def _publish_json_without_overwrite(document, destination, run_id):
    temporary = destination.with_name(
        f".{destination.name}.partial-{run_id}"
    )
    payload = canonical_json_bytes(document) + b"\n"
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _publish_file_without_overwrite(temporary, destination, read_only=True)


def backup_manifest_path(backup_path):
    path = canonical_database_path(backup_path, reject_alias=True)
    return path.with_name(f"{path.name}.manifest.json")


def create_immutable_backup(
    database_path,
    backup_path,
    *,
    run_id,
    expected_source_identity=None,
):
    """Publish one non-overwriting byte-exact backup and manifest."""
    source = canonical_database_path(database_path, reject_alias=True)
    database_identity(source)
    destination = canonical_database_path(
        backup_path,
        create_parent=True,
        reject_alias=True,
    )
    manifest_path = backup_manifest_path(destination)
    if destination.exists() or manifest_path.exists():
        raise FileExistsError("Backup or backup manifest already exists.")

    with exclusive_connection(source) as connection:
        return create_immutable_backup_locked(
            connection,
            source,
            destination,
            run_id=run_id,
            expected_source_identity=expected_source_identity,
        )


def create_immutable_backup_locked(
    connection,
    database_path,
    backup_path,
    *,
    run_id,
    expected_source_identity=None,
):
    """Create a backup while the caller retains the exclusive target lock."""
    source = canonical_database_path(database_path, reject_alias=True)
    destination = canonical_database_path(
        backup_path,
        create_parent=True,
        reject_alias=True,
    )
    manifest_path = backup_manifest_path(destination)
    if destination.exists() or manifest_path.exists():
        raise FileExistsError("Backup or backup manifest already exists.")
    readiness = validate_readiness(connection, database_path=source)
    inventory = checkpoint_for_backup(connection, source)
    if expected_source_identity is not None:
        current = inventory["database"]
        expected = expected_source_identity
        if (
            current["size"] != expected["size"]
            or current["sha256"] != expected["sha256"]
        ):
            raise RuntimeError("Ledger target changed after authorization.")

    temporary = destination.with_name(
        f".{destination.name}.partial-{run_id}"
    )
    _copy_exclusive(source, temporary)
    source_size = source.stat().st_size
    source_sha256 = sha256_file(source)
    if temporary.stat().st_size != source_size:
        raise RuntimeError("Backup byte count does not match source.")
    if sha256_file(temporary) != source_sha256:
        raise RuntimeError("Backup checksum does not match source.")

    validation = open_read_only_database(temporary)
    try:
        validate_readiness(
            validation,
            database_path=temporary,
            expected_version=readiness["schema_version"],
        )
    finally:
        validation.close()
    _publish_file_without_overwrite(
        temporary,
        destination,
        read_only=True,
    )

    manifest = {
        "schema_version": 1,
        "record_type": "immutable_ledger_backup",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "canonical_path": str(source),
            "inventory": inventory,
            "readiness": readiness,
        },
        "backup": {
            "canonical_path": str(destination),
            "size": destination.stat().st_size,
            "sha256": sha256_file(destination),
            "read_only": destination.stat().st_mode & 0o222 == 0,
        },
        "non_overwrite": True,
        "never_delete": True,
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        canonical_json_bytes(manifest)
    ).hexdigest()
    _publish_json_without_overwrite(manifest, manifest_path, run_id)
    return manifest


def load_and_validate_backup(backup_path):
    """Validate an immutable backup and its exact manifest binding."""
    path = canonical_database_path(backup_path, reject_alias=True)
    database_identity(path)
    manifest_path = canonical_database_path(
        backup_manifest_path(path),
        reject_alias=True,
    )
    database_identity(manifest_path)
    if manifest_path.stat().st_mode & 0o222:
        raise RuntimeError("Backup manifest is not read-only.")

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError("Backup manifest contains duplicate keys.")
            result[key] = value
        return result

    document = json.loads(
        manifest_path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicates,
        parse_constant=lambda value: (_ for _ in ()).throw(
            RuntimeError(f"Invalid backup JSON constant: {value}")
        ),
    )
    expected_fields = {
        "schema_version", "record_type", "run_id", "created_at", "source",
        "backup", "non_overwrite", "never_delete", "manifest_sha256",
    }
    if set(document) != expected_fields:
        raise RuntimeError("Backup manifest shape is invalid.")
    if document.get("schema_version") != 1:
        raise RuntimeError("Unsupported backup manifest version.")
    if (
        document.get("record_type") != "immutable_ledger_backup"
        or document.get("non_overwrite") is not True
        or document.get("never_delete") is not True
    ):
        raise RuntimeError("Backup manifest controls are invalid.")
    declared = document.get("manifest_sha256")
    unsigned = dict(document)
    unsigned.pop("manifest_sha256", None)
    if hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest() != declared:
        raise RuntimeError("Backup manifest digest is invalid.")
    binding = document.get("backup", {})
    if binding.get("canonical_path") != str(path):
        raise RuntimeError("Backup manifest target does not match.")
    if path.stat().st_size != binding.get("size"):
        raise RuntimeError("Backup byte count is invalid.")
    if sha256_file(path) != binding.get("sha256"):
        raise RuntimeError("Backup checksum is invalid.")
    if path.stat().st_mode & 0o222:
        raise RuntimeError("Backup is not read-only.")
    connection = open_read_only_database(path)
    try:
        readiness = validate_readiness(connection, database_path=path)
    finally:
        connection.close()
    source_readiness = document["source"]["readiness"]
    for field in (
        "schema_version",
        "schema_fingerprint",
        "integrity_check",
        "foreign_key_violations",
    ):
        if readiness[field] != source_readiness[field]:
            raise RuntimeError("Backup schema identity differs from its source.")
    return document
