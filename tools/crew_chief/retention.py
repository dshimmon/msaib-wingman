"""Bounded, root-confined retention for external Crew Chief report bundles."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from tools.crew_chief.core import (
    CrewChiefError,
    clock_value,
    isoformat,
    normalize_repo_path,
    parse_time,
    read_json,
    utc_now,
    write_canonical_json,
)
from tools.crew_chief.validation import validate_instance


DEFAULT_RETENTION_DAYS = 30
DEFAULT_MAX_RETAINED_REPORTS = 100
ROOT_MARKER = ".crew-chief-retention-root.json"
REPORT_METADATA = "retention-report.json"
RETENTION_STATE = "retention-state.json"
_REPORT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,255}$")


@dataclass(frozen=True)
class RetainedReport:
    """One completely validated report-bundle record."""

    report_id: str
    report_kind: str
    state: str
    bundle: Path
    completed_at: datetime | None


def validate_retention_limits(retention_days: int, max_retained_reports: int) -> None:
    if isinstance(retention_days, bool) or not isinstance(retention_days, int):
        raise CrewChiefError("retention days must be an integer")
    if retention_days < 0:
        raise CrewChiefError("retention days must be zero or greater")
    if isinstance(max_retained_reports, bool) or not isinstance(
        max_retained_reports, int
    ):
        raise CrewChiefError("maximum retained reports must be an integer")
    if max_retained_reports < 1:
        raise CrewChiefError("maximum retained reports must be at least one")


def validate_report_id(report_id: str) -> str:
    if not isinstance(report_id, str) or _REPORT_ID.fullmatch(report_id) is None:
        raise CrewChiefError("retention report ID is malformed")
    return report_id


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise CrewChiefError(f"retention path contains a symlink: {current}")


def validate_new_retention_root_path(root: Path) -> Path:
    """Validate an existing or proposed external root without creating it."""
    if not root.is_absolute():
        raise CrewChiefError("retention output root must be an absolute path")
    if ".." in root.parts:
        raise CrewChiefError("retention output root is ambiguous")
    _reject_symlink_components(root)
    resolved = root.resolve()
    for ancestor in (resolved, *resolved.parents):
        git_marker = ancestor / ".git"
        if git_marker.exists() or git_marker.is_symlink():
            raise CrewChiefError(
                f"retention output root cannot be inside a Git repository: {resolved}"
            )
    return resolved


def _basic_root(root: Path) -> Path:
    resolved = validate_new_retention_root_path(root)
    if not resolved.is_dir():
        raise CrewChiefError(f"retention output root is not a directory: {resolved}")
    return resolved


def initialize_retention_root(root: Path) -> Path:
    """Create or validate the exact marker that authorizes one external root."""
    root = _basic_root(root)
    marker = root / ROOT_MARKER
    expected = {
        "schema_version": "1.0",
        "canonical_root": str(root),
        "marker": "crew-chief-retention-root",
    }
    if marker.exists() or marker.is_symlink():
        if marker.is_symlink() or not marker.is_file():
            raise CrewChiefError("retention root marker must be a regular file")
        if read_json(marker) != expected:
            raise CrewChiefError("retention root marker is malformed or ambiguous")
    else:
        write_canonical_json(marker, expected)
    return root


def validate_retention_root(root: Path) -> Path:
    root = _basic_root(root)
    marker = root / ROOT_MARKER
    if marker.is_symlink() or not marker.is_file():
        raise CrewChiefError("retention output root lacks its canonical marker")
    expected = {
        "schema_version": "1.0",
        "canonical_root": str(root),
        "marker": "crew-chief-retention-root",
    }
    if read_json(marker) != expected:
        raise CrewChiefError("retention root marker is malformed or ambiguous")
    return root


def _bundle_within_root(root: Path, bundle: Path) -> tuple[Path, str]:
    root = validate_retention_root(root)
    if not bundle.is_absolute() or ".." in bundle.parts:
        raise CrewChiefError("report bundle path must be absolute and unambiguous")
    _reject_symlink_components(bundle)
    resolved = bundle.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise CrewChiefError(f"report bundle escapes retention root: {resolved}") from error
    if not relative.parts:
        raise CrewChiefError("retention root cannot itself be a report bundle")
    return resolved, normalize_repo_path(relative.as_posix())


def write_report_metadata(
    root: Path,
    bundle: Path,
    *,
    report_id: str,
    report_kind: str,
    state: str,
    created_at: datetime,
    completed_at: datetime | None = None,
) -> dict[str, Any]:
    """Write the bounded state record for one isolated report bundle."""
    validate_report_id(report_id)
    bundle, relative = _bundle_within_root(root, bundle)
    if not bundle.is_dir():
        raise CrewChiefError(f"report bundle is not a directory: {bundle}")
    value = {
        "schema_version": "1.0",
        "report_id": report_id,
        "report_kind": report_kind,
        "state": state,
        "bundle_path": relative,
        "created_at": isoformat(created_at),
        "completed_at": isoformat(completed_at) if completed_at else None,
    }
    validate_instance("retention-report-v1.schema.json", value)
    if state == "completed" and completed_at is None:
        raise CrewChiefError("completed report metadata requires a completion time")
    if state != "completed" and completed_at is not None:
        raise CrewChiefError("active report metadata cannot have a completion time")
    write_canonical_json(bundle / REPORT_METADATA, value)
    return value


def _reject_tree_symlinks(root: Path) -> None:
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in (*directories, *files):
            candidate = current_path / name
            if candidate.is_symlink():
                raise CrewChiefError(
                    f"retention output contains a symlink: {candidate}"
                )


def _load_reports(root: Path, *, now: datetime) -> list[RetainedReport]:
    _reject_tree_symlinks(root)
    records: list[RetainedReport] = []
    identifiers: set[str] = set()
    for metadata_path in sorted(root.rglob(REPORT_METADATA)):
        value = read_json(metadata_path)
        if not isinstance(value, dict):
            raise CrewChiefError("retention report metadata must be an object")
        validate_instance("retention-report-v1.schema.json", value)
        bundle, relative = _bundle_within_root(root, metadata_path.parent)
        if value["bundle_path"] != relative:
            raise CrewChiefError("retention report metadata bundle path is mismatched")
        report_id = value["report_id"]
        expected_bundle = root / "reports" / report_id
        if bundle != expected_bundle:
            raise CrewChiefError(
                f"retention report bundle location is invalid: {report_id}"
            )
        if report_id in identifiers:
            raise CrewChiefError(f"retention report ID is duplicated: {report_id}")
        identifiers.add(report_id)
        created_at = parse_time(value["created_at"])
        if created_at > now:
            raise CrewChiefError(
                f"retention report creation is in the future: {report_id}"
            )
        completed_at = None
        if value["state"] == "completed":
            if value["completed_at"] is None:
                raise CrewChiefError(
                    "completed retention report lacks a completion timestamp"
                )
            completed_at = parse_time(value["completed_at"])
            if completed_at > now:
                raise CrewChiefError(
                    f"retention report completion is in the future: {report_id}"
                )
            if completed_at < created_at:
                raise CrewChiefError(
                    f"retention report completion precedes creation: {report_id}"
                )
            required = (
                ("crew-chief-report.json", "run-record.json")
                if value["report_kind"] == "audit"
                else ("pool-report.json",)
            )
            for name in required:
                artifact = bundle / name
                if artifact.is_symlink() or not artifact.is_file():
                    raise CrewChiefError(
                        f"completed report bundle is missing {name}: {report_id}"
                    )
        elif value["completed_at"] is not None:
            raise CrewChiefError(
                f"active retention report has a completion timestamp: {report_id}"
            )
        records.append(
            RetainedReport(
                report_id=report_id,
                report_kind=value["report_kind"],
                state=value["state"],
                bundle=bundle,
                completed_at=completed_at,
            )
        )
    return records


def prune_reports(
    root: Path,
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    max_retained_reports: int = DEFAULT_MAX_RETAINED_REPORTS,
    dry_run: bool = False,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Prune eligible bundles deterministically, or report a dry run."""
    validate_retention_limits(retention_days, max_retained_reports)
    root = validate_retention_root(root)
    now = clock_value(clock)
    records = _load_reports(root, now=now)
    completed = [record for record in records if record.state == "completed"]
    cutoff = now - timedelta(days=retention_days)
    reasons: dict[str, set[str]] = {}
    for record in completed:
        if record.completed_at is not None and record.completed_at < cutoff:
            reasons.setdefault(record.report_id, set()).add("age")

    remaining = [record for record in completed if record.report_id not in reasons]
    excess = max(0, len(remaining) - max_retained_reports)
    ordered = sorted(
        remaining,
        key=lambda item: (item.completed_at, item.report_id),
    )
    for record in ordered[:excess]:
        reasons.setdefault(record.report_id, set()).add("count")

    by_identifier = {record.report_id: record for record in completed}
    candidates = []
    for report_id in sorted(
        reasons,
        key=lambda item: (
            by_identifier[item].completed_at,
            item,
        ),
    ):
        record = by_identifier[report_id]
        candidates.append(
            {
                "report_id": report_id,
                "report_kind": record.report_kind,
                "bundle_path": str(record.bundle),
                "completed_at": isoformat(record.completed_at),
                "reasons": sorted(reasons[report_id]),
            }
        )

    if not dry_run:
        for candidate in candidates:
            bundle, _relative = _bundle_within_root(
                root, Path(candidate["bundle_path"])
            )
            if bundle.is_symlink() or not bundle.is_dir():
                raise CrewChiefError(
                    f"retention candidate changed before deletion: {bundle}"
                )
            shutil.rmtree(bundle)
        retained_count = len(completed) - len(candidates)
        state = {
            "schema_version": "1.0",
            "retention_days": retention_days,
            "max_retained_reports": max_retained_reports,
            "current_retained_count": retained_count,
            "last_cleanup_time": isoformat(now),
            "removed_during_last_cleanup": len(candidates),
        }
        validate_instance("retention-state-v1.schema.json", state)
        write_canonical_json(root / RETENTION_STATE, state)
    else:
        retained_count = len(completed) - len(candidates)

    return {
        "schema_version": "1.0",
        "output_root": str(root),
        "dry_run": dry_run,
        "retention_days": retention_days,
        "max_retained_reports": max_retained_reports,
        "completed_report_count": len(completed),
        "active_report_count": len(records) - len(completed),
        "retained_report_count": retained_count,
        "remove_count": len(candidates),
        "candidates": candidates,
    }
