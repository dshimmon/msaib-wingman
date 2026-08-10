"""Shared deterministic and path-safety primitives for Crew Chief."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable


CANARY = "CANOPY-7C2F-ATLAS"
SCHEMA_VERSION = "1.0"
AGENT_PATH = Path(".codex/agents/crew-chief.toml")
SCHEMA_NAMES = (
    "audit-envelope-v1.schema.json",
    "authorization-receipt-v1.schema.json",
    "bootstrap-report-v1.schema.json",
    "finding-v1.schema.json",
    "report-v1.schema.json",
    "reconciliation-v1.schema.json",
)
RISK_PROFILES = frozenset({"standard", "deep", "exempt"})
PROFILE_FOCUS = {
    "standard": (
        "scope",
        "correctness",
        "tests",
        "documentation",
        "unrequested_changes",
        "completion_claims",
        "maintainability",
    ),
    "deep": (
        "scope",
        "architecture",
        "correctness",
        "security",
        "data",
        "tests",
        "documentation",
        "dependencies",
        "compatibility",
        "public_contracts",
        "migrations",
        "unrequested_changes",
        "completion_claims",
        "maintainability",
    ),
    "exempt": (
        "recorded_exemption_justification",
        "deterministic_governance_validation",
        "status_claim_accuracy",
    ),
}
ALL_AUDIT_FOCUS = frozenset(
    focus for profile in PROFILE_FOCUS.values() for focus in profile
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SECRET_EXACT = frozenset(
    {
        ".env",
        ".netrc",
        "credentials",
        "credentials.json",
        "id_dsa",
        "id_ed25519",
        "id_rsa",
        "private-key",
        "private_key",
        "secrets",
        "secrets.json",
        "token",
        "tokens",
    }
)
_SECRET_SUFFIXES = (".key", ".p12", ".pfx", ".pem")
_SECRET_MARKER = re.compile(
    r"(?:^|[._-])(?:api[._-]?key|access[._-]?token|auth[._-]?token|"
    r"credential(?:s)?|private[._-]?key|secret(?:s)?|token(?:s)?)(?:[._-]|$)",
    re.IGNORECASE,
)
_LIVE_DATA_PARTS = frozenset(
    {"data", "live", "live-data", "live_data", "production-data", "production_data"}
)


class CrewChiefError(ValueError):
    """A Crew Chief input or control failed closed."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the one canonical representation used for all JSON hashes."""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_encoding(value: bytes) -> tuple[str, int | None]:
    """Classify frozen bytes consistently for manifests and model payloads."""
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return "base64", None
    if "\x00" in text:
        return "base64", None
    return "utf-8", len(text.splitlines())


def atomic_write(path: Path, payload: bytes) -> None:
    """Write one file atomically without following a destination symlink."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent)
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write_canonical_json(path: Path, value: Any) -> None:
    atomic_write(path, canonical_json_bytes(value) + b"\n")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CrewChiefError(f"invalid JSON artifact {path}: {error}") from error


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise CrewChiefError("audit clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc).replace(microsecond=0)


def isoformat(value: datetime) -> str:
    return normalize_time(value).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise CrewChiefError(f"invalid audit timestamp: {value!r}") from error
    return normalize_time(parsed)


def validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise CrewChiefError(f"{label} must be a lowercase SHA-256 digest")


def normalize_repo_path(value: str) -> str:
    """Normalize a Git path while rejecting absolute or parent traversal."""
    if not isinstance(value, str) or not value:
        raise CrewChiefError("repository path must be a non-empty UTF-8 string")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CrewChiefError(f"repository path escapes its root: {value!r}")
    return path.as_posix()


def is_secret_path(value: str) -> bool:
    path = PurePosixPath(value)
    for part in path.parts:
        lowered = part.casefold()
        if (
            lowered in _SECRET_EXACT
            or lowered.startswith(".env.")
            or lowered.startswith("credentials.")
            or lowered.startswith("secrets.")
            or lowered.endswith(_SECRET_SUFFIXES)
            or _SECRET_MARKER.search(lowered)
        ):
            return True
    return False


def is_live_data_path(value: str) -> bool:
    return any(
        part.casefold() in _LIVE_DATA_PARTS for part in PurePosixPath(value).parts
    )


def validate_subject_path(value: str) -> str:
    normalized = normalize_repo_path(value)
    if is_secret_path(normalized):
        raise CrewChiefError(f"secret-bearing path is forbidden: {normalized}")
    if is_live_data_path(normalized):
        raise CrewChiefError(f"live-data path is forbidden: {normalized}")
    return normalized


def ensure_within_repository(repository: Path, path: Path, label: str) -> Path:
    repository = repository.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(repository)
    except ValueError as error:
        raise CrewChiefError(
            f"{label} resolves outside the authorized repository: {resolved}"
        ) from error
    return resolved


def ensure_external_path(repository: Path, path: Path, label: str) -> Path:
    repository = repository.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(repository)
    except ValueError:
        return resolved
    raise CrewChiefError(f"{label} must remain outside the repository: {resolved}")


def new_external_directory(
    repository: Path,
    requested: Path | None,
    *,
    prefix: str,
) -> Path:
    if requested is None:
        created = Path(tempfile.mkdtemp(prefix=prefix)).resolve()
        return ensure_external_path(repository, created, "audit output")
    target = ensure_external_path(repository, requested, "audit output")
    if target.exists():
        raise CrewChiefError(f"audit output already exists: {target}")
    if not target.parent.is_dir():
        raise CrewChiefError(
            f"audit output parent must already exist: {target.parent}"
        )
    target.mkdir(mode=0o700)
    return target


def bind_file(path: Path, relative_path: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CrewChiefError(f"evidence must be a regular file: {path}")
    return {
        "path": normalize_repo_path(relative_path),
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
    }


def copy_bound_file(source: Path, target: Path, relative_path: str) -> dict[str, Any]:
    if source.is_symlink() or not source.is_file():
        raise CrewChiefError(f"evidence must be a regular file: {source}")
    if is_secret_path(source.as_posix()):
        raise CrewChiefError(f"secret-bearing evidence path is forbidden: {source}")
    if is_live_data_path(source.as_posix()):
        raise CrewChiefError(f"live-data evidence path is forbidden: {source}")
    atomic_write(target, source.read_bytes())
    return bind_file(target, relative_path)


def clock_value(clock: Callable[[], datetime]) -> datetime:
    try:
        return normalize_time(clock())
    except CrewChiefError:
        raise
    except Exception as error:
        raise CrewChiefError(f"audit clock failed: {error}") from error


def redact_text(value: str) -> str:
    """Remove common authentication material before preserving CLI diagnostics."""
    patterns = (
        r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+",
        r"(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s]+",
        r"\bsk-[A-Za-z0-9_-]{8,}\b",
    )
    redacted = value
    for pattern in patterns:
        replacement = r"\1[REDACTED]" if pattern.startswith("(?i)(") else "[REDACTED]"
        redacted = re.sub(pattern, replacement, redacted)
    return redacted
