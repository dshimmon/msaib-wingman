"""Versioned, single-use, exact-target Ledger transition authorization."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from wingman.core.ledger.backup import (
    checkpoint_for_backup,
)
from wingman.core.ledger.database import exclusive_connection
from wingman.core.ledger.locking import (
    canonical_database_path,
    database_identity,
)
from wingman.core.ledger.migrations import migration_plan_digest
from wingman.core.ledger.preservation import sha256_file
from wingman.core.ledger.readiness import (
    canonical_json_bytes,
    validate_readiness,
)


CANARY = "CANOPY-7C2F-ATLAS"
MANIFEST_SCHEMA_VERSION = 1
RECEIPT_SCHEMA_VERSION = 1
PERMITTED_OPERATIONS = {"migrate", "restore", "rollback"}
MANIFEST_FIELDS = {
    "schema_version", "record_type", "canary", "authority", "run_id",
    "expires_at", "permitted_operation", "target", "backup_destination",
    "code_identity", "migration_plan_sha256", "command", "receipt_path",
    "caller_supplied_sql", "caller_supplied_migration_selection",
    "automatic_retry_permitted", "manifest_id",
}
RECEIPT_FIELDS = {
    "schema_version", "record_type", "canary", "asserted_authority",
    "manifest", "run_id", "expires_at", "permitted_operation", "target",
    "backup_destination", "code_identity", "migration_plan_sha256",
    "command", "authorization_text_sha256", "single_use",
    "automatic_retry_permitted", "state", "trust_boundary", "receipt_id",
}


def _repository_root():
    return Path(__file__).resolve().parents[4]


def _git(repository, *arguments):
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=False,
    )
    return result.stdout.rstrip(b"\n")


def repository_code_identity(reviewed_base, reviewed_head):
    """Bind Git range, working diff, and every transition implementation byte."""
    repository = _repository_root()
    head = _git(repository, "rev-parse", "HEAD").decode()
    resolved_base = _git(repository, "rev-parse", reviewed_base).decode()
    resolved_head = _git(repository, "rev-parse", reviewed_head).decode()
    _git(repository, "merge-base", "--is-ancestor", resolved_base, resolved_head)
    diff = _git(repository, "diff", "--binary", "HEAD")
    status = _git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    paths = sorted(
        list((repository / "src/wingman/core/ledger").glob("**/*"))
        + [repository / "src/wingman/shared/source_registry.py"]
    )
    inventory = []
    for path in paths:
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        inventory.append(
            {
                "path": str(path.relative_to(repository)),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "repository": str(repository),
        "head": head,
        "reviewed_base": resolved_base,
        "reviewed_head": resolved_head,
        "working_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "status_sha256": hashlib.sha256(status).hexdigest(),
        "source_inventory": inventory,
    }


def _parse_expiry(value):
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise RuntimeError("Authorization expiry is invalid.") from error
    if parsed.tzinfo is None:
        raise RuntimeError("Authorization expiry must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _assert_not_expired(value, *, now=None):
    current = now or datetime.now(timezone.utc)
    if _parse_expiry(value) <= current:
        raise RuntimeError("Ledger transition authorization is expired.")


def _load_json_no_duplicates(path):
    def no_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError("Authorization JSON contains duplicate keys.")
            result[key] = value
        return result

    return json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=no_duplicates,
        parse_constant=lambda constant: (_ for _ in ()).throw(
            RuntimeError(f"Invalid JSON constant: {constant}")
        ),
    )


def _write_exclusive_document(path, document, *, read_only=True):
    destination = canonical_database_path(
        path,
        create_parent=True,
        reject_alias=True,
    )
    payload = canonical_json_bytes(document) + b"\n"
    descriptor = os.open(
        destination,
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
    if read_only:
        os.chmod(destination, 0o444)
    directory = os.open(destination.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return destination


def exact_execution_command(manifest_path, receipt_path):
    """Construct the only accepted execution command; callers supply no argv."""
    executable = Path(sys.executable).resolve()
    return {
        "executable": {
            "path": str(executable),
            "size": executable.stat().st_size,
            "sha256": sha256_file(executable),
        },
        "argv": [
            str(executable),
            "-m",
            "wingman.core.ledger.transition_cli",
            "execute",
            "--manifest",
            str(canonical_database_path(manifest_path, reject_alias=True)),
            "--receipt",
            str(canonical_database_path(receipt_path, reject_alias=True)),
        ],
    }


def create_transition_manifest(
    database_path,
    backup_path,
    manifest_path,
    receipt_path,
    *,
    operation,
    run_id,
    expires_at,
    reviewed_base,
    reviewed_head,
):
    """Freeze one exact quiescent target and its internally built operation."""
    if operation not in PERMITTED_OPERATIONS:
        raise ValueError("Ledger operation is not permitted.")
    _assert_not_expired(expires_at)
    target = canonical_database_path(database_path, reject_alias=True)
    backup = canonical_database_path(
        backup_path,
        create_parent=True,
        reject_alias=True,
    )
    manifest_destination = canonical_database_path(
        manifest_path,
        create_parent=True,
        reject_alias=True,
    )
    receipt_destination = canonical_database_path(
        receipt_path,
        create_parent=True,
        reject_alias=True,
    )
    if receipt_destination.exists():
        raise FileExistsError("Authorization receipt path already exists.")

    with exclusive_connection(target) as connection:
        readiness = validate_readiness(connection, database_path=target)
        inventory = checkpoint_for_backup(connection, target)
        identity = database_identity(target)

    document = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "record_type": "ledger_transition_manifest",
        "canary": CANARY,
        "authority": "Maverick",
        "run_id": run_id,
        "expires_at": expires_at,
        "permitted_operation": operation,
        "target": {
            "identity": identity,
            "schema": readiness,
            "inventory": inventory,
            "quiescent_checksum": inventory["database"]["sha256"],
        },
        "backup_destination": str(backup),
        "code_identity": repository_code_identity(
            reviewed_base,
            reviewed_head,
        ),
        "migration_plan_sha256": migration_plan_digest(),
        "command": exact_execution_command(
            manifest_destination,
            receipt_destination,
        ),
        "receipt_path": str(receipt_destination),
        "caller_supplied_sql": False,
        "caller_supplied_migration_selection": False,
        "automatic_retry_permitted": False,
    }
    document["manifest_id"] = hashlib.sha256(
        canonical_json_bytes(document)
    ).hexdigest()
    _write_exclusive_document(manifest_destination, document)
    return document


def create_authorization_receipt(
    manifest_path,
    receipt_path,
    *,
    authorization_text,
):
    """Record exact approval; this does not authenticate Maverick independently."""
    manifest = _load_json_no_duplicates(manifest_path)
    _assert_not_expired(manifest["expires_at"])
    destination = canonical_database_path(
        receipt_path,
        create_parent=True,
        reject_alias=True,
    )
    if str(destination) != manifest["receipt_path"]:
        raise RuntimeError("Receipt target differs from the reviewed manifest.")
    manifest_file = canonical_database_path(manifest_path, reject_alias=True)
    document = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "record_type": "ledger_transition_authorization_receipt",
        "canary": CANARY,
        "asserted_authority": "Maverick",
        "manifest": {
            "path": str(manifest_file),
            "size": manifest_file.stat().st_size,
            "sha256": sha256_file(manifest_file),
            "manifest_id": manifest["manifest_id"],
        },
        "run_id": manifest["run_id"],
        "expires_at": manifest["expires_at"],
        "permitted_operation": manifest["permitted_operation"],
        "target": manifest["target"],
        "backup_destination": manifest["backup_destination"],
        "code_identity": manifest["code_identity"],
        "migration_plan_sha256": manifest["migration_plan_sha256"],
        "command": manifest["command"],
        "authorization_text_sha256": hashlib.sha256(
            authorization_text.encode("utf-8")
        ).hexdigest(),
        "single_use": True,
        "automatic_retry_permitted": False,
        "state": "unused",
        "trust_boundary": (
            "authenticated Mission Control interaction plus the trusted local "
            "operating-system account; no independent human authentication"
        ),
    }
    document["receipt_id"] = hashlib.sha256(
        canonical_json_bytes(document)
    ).hexdigest()
    _write_exclusive_document(destination, document)
    return document


def _validate_content_id(document, field):
    declared = document.get(field)
    unsigned = dict(document)
    unsigned.pop(field, None)
    if hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest() != declared:
        raise RuntimeError(f"{field} does not match authorization content.")


def _validate_document_shapes(manifest, receipt):
    if set(manifest) != MANIFEST_FIELDS:
        raise RuntimeError("Ledger transition manifest shape is invalid.")
    if set(receipt) != RECEIPT_FIELDS:
        raise RuntimeError("Ledger authorization receipt shape is invalid.")
    if (
        manifest["schema_version"] != MANIFEST_SCHEMA_VERSION
        or manifest["record_type"] != "ledger_transition_manifest"
        or manifest["authority"] != "Maverick"
        or manifest["caller_supplied_sql"] is not False
        or manifest["caller_supplied_migration_selection"] is not False
        or manifest["automatic_retry_permitted"] is not False
    ):
        raise RuntimeError("Ledger transition manifest controls are invalid.")
    if (
        receipt["schema_version"] != RECEIPT_SCHEMA_VERSION
        or receipt["record_type"] != "ledger_transition_authorization_receipt"
        or receipt["asserted_authority"] != "Maverick"
        or receipt["single_use"] is not True
        or receipt["automatic_retry_permitted"] is not False
        or receipt["state"] != "unused"
    ):
        raise RuntimeError("Ledger authorization receipt controls are invalid.")


def validate_authorization(manifest_path, receipt_path, *, operation):
    """Recompute every exact binding before consuming authorization."""
    manifest_file = canonical_database_path(manifest_path, reject_alias=True)
    receipt_file = canonical_database_path(receipt_path, reject_alias=True)
    database_identity(manifest_file)
    database_identity(receipt_file)
    manifest = _load_json_no_duplicates(manifest_file)
    receipt = _load_json_no_duplicates(receipt_file)
    _validate_document_shapes(manifest, receipt)
    _validate_content_id(manifest, "manifest_id")
    _validate_content_id(receipt, "receipt_id")
    if authorization_consumption_marker(receipt_file, receipt).exists():
        raise RuntimeError("Ledger authorization receipt is already consumed.")
    _assert_not_expired(manifest["expires_at"])
    _assert_not_expired(receipt["expires_at"])
    if manifest.get("canary") != CANARY or receipt.get("canary") != CANARY:
        raise RuntimeError("Ledger authorization Canary does not match.")
    if operation not in PERMITTED_OPERATIONS:
        raise ValueError("Ledger operation is not permitted.")
    if (
        operation != manifest["permitted_operation"]
        or operation != receipt["permitted_operation"]
    ):
        raise RuntimeError("Ledger operation differs from authorization.")
    if receipt["manifest"] != {
        "path": str(manifest_file),
        "size": manifest_file.stat().st_size,
        "sha256": sha256_file(manifest_file),
        "manifest_id": manifest["manifest_id"],
    }:
        raise RuntimeError("Authorization receipt does not bind this manifest.")
    for field in (
        "run_id",
        "target",
        "backup_destination",
        "code_identity",
        "migration_plan_sha256",
        "command",
    ):
        if receipt[field] != manifest[field]:
            raise RuntimeError(f"Receipt field differs from manifest: {field}")
    expected_command = exact_execution_command(manifest_file, receipt_file)
    if manifest["command"] != expected_command:
        raise RuntimeError("Ledger execution command binding changed.")
    if manifest["migration_plan_sha256"] != migration_plan_digest():
        raise RuntimeError("Ledger migration plan changed after review.")
    code = manifest["code_identity"]
    if repository_code_identity(
        code["reviewed_base"],
        code["reviewed_head"],
    ) != code:
        raise RuntimeError("Ledger transition code changed after review.")
    return manifest, receipt


def validate_exact_target(manifest, *, connection=None):
    """Validate target identity, schema, and quiescent DB/WAL/SHM inventory."""
    target_path = manifest["target"]["identity"]["canonical_path"]
    target = canonical_database_path(target_path, reject_alias=True)
    if database_identity(target) != manifest["target"]["identity"]:
        raise RuntimeError("Ledger target identity changed after authorization.")
    if connection is None:
        with exclusive_connection(target) as opened_connection:
            readiness = validate_readiness(
                opened_connection,
                database_path=target,
            )
            inventory = checkpoint_for_backup(opened_connection, target)
    else:
        readiness = validate_readiness(connection, database_path=target)
        inventory = checkpoint_for_backup(connection, target)
    if readiness != manifest["target"]["schema"]:
        raise RuntimeError("Ledger schema identity changed after authorization.")
    if inventory != manifest["target"]["inventory"]:
        raise RuntimeError("Ledger DB/WAL/SHM inventory changed after authorization.")
    return target


def authorization_consumption_marker(receipt_path, receipt):
    receipt_file = canonical_database_path(receipt_path, reject_alias=True)
    return receipt_file.with_name(
        f"{receipt_file.name}.consumed-{receipt['receipt_id']}"
    )


def consume_authorization(receipt_path, receipt):
    """Atomically consume a receipt before work; failure never permits retry."""
    marker = authorization_consumption_marker(receipt_path, receipt)
    document = {
        "schema_version": 1,
        "receipt_id": receipt["receipt_id"],
        "run_id": receipt["run_id"],
        "consumed_at": datetime.now(timezone.utc).isoformat(),
        "automatic_retry_permitted": False,
    }
    _write_exclusive_document(marker, document)
    return marker


def authorize_execution(manifest_path, receipt_path, *, operation):
    manifest, receipt = validate_authorization(
        manifest_path,
        receipt_path,
        operation=operation,
    )
    target = validate_exact_target(manifest)
    consume_authorization(receipt_path, receipt)
    return target, manifest, receipt
