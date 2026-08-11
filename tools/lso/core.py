"""Shared deterministic primitives for LSO v1."""

from __future__ import annotations

import copy
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tools.crew_chief.core import (
    CANARY,
    atomic_write,
    canonical_json_bytes,
    is_live_data_path,
    is_secret_path,
    parse_time,
    read_json,
    sha256_bytes,
    sha256_file,
    validate_subject_path,
    write_canonical_json,
)


SCHEMA_VERSION = "1.0"
SCHEMA_ROOT = Path(__file__).resolve().parent / "schemas"
SCHEMA_NAMES = (
    "closeout-evidence-v1.schema.json",
    "closeout-plan-v1.schema.json",
    "authorization-receipt-v1.schema.json",
    "execution-report-v1.schema.json",
)
CLOSEOUT_ACTIONS = (
    "stage_exact_audited_paths",
    "commit_implementation",
    "publish_implementation_branch",
    "fast_forward_main",
    "publish_completion_records",
    "commit_completion_records",
    "publish_closeout",
    "verify_remote",
    "declare_complete",
)
GENERATED_GOVERNANCE_PATHS = (
    "CURRENT_MISSION.md",
    "docs/decisions/README.md",
    "docs/governance/mission-control-context.md",
    "docs/missions/README.md",
)


class LSOError(ValueError):
    """An LSO input, invariant, or authorized operation failed closed."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(value: datetime) -> str:
    if value.tzinfo is None:
        raise LSOError("LSO clock must be timezone-aware")
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_schema(name: str) -> dict[str, Any]:
    if name not in SCHEMA_NAMES:
        raise LSOError(f"unrecognized LSO schema: {name}")
    path = SCHEMA_ROOT / name
    try:
        value = read_json(path)
    except ValueError as error:
        raise LSOError(str(error)) from error
    if not isinstance(value, dict):
        raise LSOError(f"LSO schema is not an object: {path}")
    Draft202012Validator.check_schema(value)
    return value


def validate_instance(name: str, value: Any) -> None:
    errors = sorted(
        Draft202012Validator(load_schema(name)).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if not errors:
        return
    details = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        details.append(f"{location}: {error.message}")
    raise LSOError("schema validation failed: " + "; ".join(details))


def artifact_binding(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_file():
        raise LSOError(f"artifact must be a regular file: {resolved}")
    rendered = resolved.as_posix()
    if is_secret_path(rendered) or is_live_data_path(rendered):
        raise LSOError(f"secret or live-data artifact is forbidden: {resolved}")
    return {
        "path": str(resolved),
        "sha256": sha256_file(resolved),
        "size": resolved.stat().st_size,
    }


def verify_artifact(binding: dict[str, Any], label: str) -> Path:
    path = Path(binding["path"])
    observed = artifact_binding(path)
    if observed != binding:
        raise LSOError(f"{label} changed after LSO binding")
    return path.resolve()


def plan_core(plan: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(plan)
    value.pop("plan_id", None)
    value.pop("approval", None)
    return value


def plan_identifier(plan: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(plan_core(plan)))


def receipt_identifier(receipt: dict[str, Any]) -> str:
    value = copy.deepcopy(receipt)
    value.pop("receipt_id", None)
    return sha256_bytes(canonical_json_bytes(value))


def report_identifier(report: dict[str, Any]) -> str:
    value = copy.deepcopy(report)
    value.pop("report_id", None)
    return sha256_bytes(canonical_json_bytes(value))


def ensure_external(repository: Path, path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(repository.resolve())
    except ValueError:
        return resolved
    raise LSOError(f"{label} must remain outside the repository: {resolved}")


def new_external_directory(repository: Path, requested: Path) -> Path:
    target = ensure_external(repository, requested, "LSO output")
    if target.exists():
        raise LSOError(f"LSO output already exists: {target}")
    if not target.parent.is_dir():
        raise LSOError(f"LSO output parent must exist: {target.parent}")
    target.mkdir(mode=0o700)
    return target


def consume_once(marker_root: Path, receipt_id: str) -> Path:
    if marker_root.is_symlink():
        raise LSOError("LSO receipt consumption directory must not be a symlink")
    marker_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if marker_root.is_symlink() or not marker_root.is_dir():
        raise LSOError("LSO receipt consumption directory is invalid")
    marker = marker_root / validate_subject_path(receipt_id)
    try:
        descriptor = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise LSOError("LSO authorization receipt was already consumed") from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(b"consumed\n")
        handle.flush()
        os.fsync(handle.fileno())
    return marker


__all__ = [
    "CANARY",
    "CLOSEOUT_ACTIONS",
    "GENERATED_GOVERNANCE_PATHS",
    "LSOError",
    "SCHEMA_VERSION",
    "artifact_binding",
    "atomic_write",
    "canonical_json_bytes",
    "consume_once",
    "ensure_external",
    "isoformat",
    "load_schema",
    "new_external_directory",
    "parse_time",
    "plan_identifier",
    "read_json",
    "receipt_identifier",
    "report_identifier",
    "sha256_bytes",
    "utc_now",
    "validate_instance",
    "verify_artifact",
    "write_canonical_json",
]
