"""Deterministic Crew Chief envelope and reconciliation controller."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable

from tools.crew_chief.core import (
    AGENT_PATH,
    CANARY,
    RISK_PROFILES,
    SCHEMA_NAMES,
    SCHEMA_VERSION,
    CrewChiefError,
    atomic_write,
    bind_file,
    canonical_json_bytes,
    clock_value,
    copy_bound_file,
    ensure_within_repository,
    isoformat,
    is_live_data_path,
    is_secret_path,
    new_external_directory,
    normalize_repo_path,
    parse_time,
    read_json,
    sha256_bytes,
    sha256_file,
    utc_now,
    write_canonical_json,
)
from tools.crew_chief.git_evidence import (
    capture_subject,
    git_state,
    is_ancestor,
    repository_identity,
    resolve_commit,
    resolve_repository,
)
from tools.crew_chief.validation import (
    validate_instance,
    validate_reconciliation,
    validate_report,
)


_PROFILE_FOCUS = {
    "standard": [
        "scope",
        "correctness",
        "tests",
        "documentation",
        "unrequested_changes",
        "completion_claims",
        "maintainability",
    ],
    "deep": [
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
    ],
    "exempt": [
        "recorded_exemption_justification",
        "deterministic_governance_validation",
        "status_claim_accuracy",
    ],
}


def _input_file(path: Path, label: str) -> Path:
    if path.is_symlink():
        raise CrewChiefError(f"{label} must not be a symlink: {path}")
    resolved = path.resolve()
    if not resolved.is_file():
        raise CrewChiefError(f"{label} must be a regular file: {resolved}")
    if is_secret_path(resolved.as_posix()):
        raise CrewChiefError(f"{label} is a secret-bearing path: {resolved}")
    if is_live_data_path(resolved.as_posix()):
        raise CrewChiefError(f"{label} is a live-data path: {resolved}")
    return resolved


def _risk_profile(
    name: str,
    justification: str | None,
    test_claims: dict[str, Any],
) -> dict[str, Any]:
    if name not in RISK_PROFILES:
        raise CrewChiefError(f"unsupported audit risk profile: {name}")
    if name == "exempt":
        if not justification or not justification.strip():
            raise CrewChiefError("exempt profile requires a recorded justification")
        if not test_claims.get("governance_validation"):
            raise CrewChiefError(
                "exempt profile requires deterministic governance validation evidence"
            )
    return {
        "name": name,
        "justification": (justification or "").strip(),
        "required_focus": _PROFILE_FOCUS[name],
    }


def _copy_controls(repository: Path, output: Path) -> dict[str, Any]:
    instructions_source = ensure_within_repository(
        repository, repository / "AGENTS.md", "repository instructions"
    )
    instructions_binding = copy_bound_file(
        instructions_source,
        output / "controls" / "AGENTS.md",
        "controls/AGENTS.md",
    )
    agent_source = ensure_within_repository(
        repository, repository / AGENT_PATH, "Crew Chief agent"
    )
    agent_target = output / "controls" / AGENT_PATH
    agent_binding = copy_bound_file(
        agent_source, agent_target, f"controls/{AGENT_PATH.as_posix()}"
    )
    schemas = []
    for name in SCHEMA_NAMES:
        source = ensure_within_repository(
            repository,
            repository / "tools" / "crew_chief" / "schemas" / name,
            "Crew Chief schema",
        )
        target = output / "controls" / "schemas" / name
        schemas.append(
            {
                "name": name,
                "frozen": copy_bound_file(
                    source, target, f"controls/schemas/{name}"
                ),
            }
        )
    return {
        "repository_instructions": instructions_binding,
        "agent": agent_binding,
        "schemas": schemas,
    }


def _artifact_target(index: int, source: Path) -> str:
    suffix = source.suffix if source.suffix else ".bin"
    return f"evidence/artifact-{index:03d}{suffix}"


def prepare_audit(
    repository: Path,
    *,
    mission_record: Path,
    base: str,
    head: str,
    engineer_report: Path,
    evidence_artifacts: Iterable[Path],
    test_claims: dict[str, Any],
    profile: str = "standard",
    profile_justification: str | None = None,
    output_root: Path | None = None,
    include_worktree: bool = False,
    authorized_untracked: Iterable[str] = (),
    expires_in_seconds: int = 86400,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Freeze one committed range or explicitly bound working-tree subject."""
    repository = resolve_repository(repository)
    if expires_in_seconds < 1 or expires_in_seconds > 86400:
        raise CrewChiefError("audit envelope expiry must be between 1 and 86400 seconds")
    if not isinstance(test_claims, dict) or not test_claims:
        raise CrewChiefError("test and validation claims must be a non-empty object")

    mission_source = ensure_within_repository(
        repository, mission_record, "mission record"
    )
    mission_source = _input_file(mission_source, "mission record")
    mission_relative = mission_source.relative_to(repository).as_posix()
    engineer_source = _input_file(engineer_report, "engineer report")
    evidence_sources = sorted(
        (_input_file(path, "evidence artifact") for path in evidence_artifacts),
        key=lambda item: str(item),
    )
    if not evidence_sources:
        raise CrewChiefError("at least one engineer evidence artifact is required")
    risk_profile = _risk_profile(profile, profile_justification, test_claims)

    base_commit = resolve_commit(repository, base)
    head_commit = resolve_commit(repository, head)
    current_head = resolve_commit(repository, "HEAD")
    if head_commit != current_head:
        raise CrewChiefError("audit head must equal the repository's current HEAD")
    if not is_ancestor(repository, base_commit, head_commit):
        raise CrewChiefError("audit base is not an ancestor of audit head")

    subject, diff_payloads, untracked_payloads = capture_subject(
        repository,
        base_commit,
        head_commit,
        include_worktree=include_worktree,
        authorized_untracked=list(authorized_untracked),
    )
    starting_git_state = git_state(repository)
    identity = repository_identity(repository)
    created = clock_value(clock)
    expires = created + timedelta(seconds=expires_in_seconds)
    output = new_external_directory(
        repository, output_root, prefix="wingman-crew-chief-envelope-"
    )

    mission_binding = copy_bound_file(
        mission_source,
        output / "evidence" / "mission-record.md",
        "evidence/mission-record.md",
    )
    engineer_suffix = engineer_source.suffix or ".bin"
    engineer_relative = f"evidence/engineer-report{engineer_suffix}"
    engineer_binding = copy_bound_file(
        engineer_source, output / engineer_relative, engineer_relative
    )
    test_claims_relative = "evidence/test-claims.json"
    write_canonical_json(output / test_claims_relative, test_claims)
    test_claims_binding = bind_file(
        output / test_claims_relative, test_claims_relative
    )

    evidence_bindings = []
    for index, source in enumerate(evidence_sources, start=1):
        relative = _artifact_target(index, source)
        evidence_bindings.append(
            {
                "label": source.name,
                "frozen": copy_bound_file(source, output / relative, relative),
            }
        )

    diff_bindings = []
    for name, payload in sorted(diff_payloads.items()):
        relative = f"diffs/{name}"
        atomic_write(output / relative, payload)
        diff_bindings.append({"name": name, "frozen": bind_file(output / relative, relative)})

    untracked_bindings = []
    for path, payload in sorted(untracked_payloads.items()):
        relative = f"untracked/{path}"
        atomic_write(output / relative, payload)
        untracked_bindings.append(
            {
                "repository_path": path,
                "frozen": bind_file(output / relative, relative),
            }
        )

    controls = _copy_controls(repository, output)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "repository_id": identity["repository_id"],
        "mission": {
            "repository_path": mission_relative,
            "frozen": mission_binding,
        },
        "subject": subject,
        "git_state": starting_git_state,
        "risk_profile": risk_profile,
        "diffs": diff_bindings,
        "untracked_files": untracked_bindings,
        "engineer_report": engineer_binding,
        "evidence_artifacts": evidence_bindings,
        "test_claims": test_claims_binding,
        "controls": controls,
    }
    manifest_path = output / "evidence-manifest.json"
    write_canonical_json(manifest_path, manifest)
    manifest_binding = bind_file(manifest_path, "evidence-manifest.json")
    audit_id = sha256_bytes(canonical_json_bytes(manifest))
    envelope_id = sha256_bytes(
        canonical_json_bytes(
            {
                "audit_id": audit_id,
                "created_at": isoformat(created),
                "expires_at": isoformat(expires),
            }
        )
    )
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "canary": CANARY,
        "audit_id": audit_id,
        "envelope_id": envelope_id,
        "repository": identity,
        "mission": {
            "repository_path": mission_relative,
            "frozen": mission_binding,
        },
        "subject": {
            "mode": subject["mode"],
            "base_commit": base_commit,
            "head_commit": head_commit,
            "authorized_untracked": subject["authorized_untracked"],
        },
        "git_state": starting_git_state,
        "risk_profile": risk_profile,
        "manifest": manifest_binding,
        "created_at": isoformat(created),
        "expires_at": isoformat(expires),
    }
    envelope["envelope_hash"] = sha256_bytes(canonical_json_bytes(envelope))
    validate_instance("audit-envelope-v1.schema.json", envelope)
    envelope_path = output / "audit-envelope.json"
    write_canonical_json(envelope_path, envelope)
    return {
        "audit_id": audit_id,
        "envelope_id": envelope_id,
        "envelope_path": str(envelope_path),
        "manifest_path": str(manifest_path),
        "output_root": str(output),
    }


def _bound_path(root: Path, binding: dict[str, Any], label: str) -> Path:
    relative = normalize_repo_path(binding["path"])
    candidate = root.joinpath(*Path(relative).parts)
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise CrewChiefError(f"{label} escapes its frozen root: {relative}") from error
    if candidate.is_symlink() or not candidate.is_file():
        raise CrewChiefError(f"{label} is missing or not a regular file: {relative}")
    if candidate.stat().st_size != binding["size"]:
        raise CrewChiefError(f"{label} size changed: {relative}")
    if sha256_file(candidate) != binding["sha256"]:
        raise CrewChiefError(f"{label} hash changed: {relative}")
    return candidate


def _manifest_bindings(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if set(("path", "sha256", "size")).issubset(value):
            yield value
            return
        for child in value.values():
            yield from _manifest_bindings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _manifest_bindings(child)


def load_envelope(path: Path) -> tuple[Path, dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise CrewChiefError(f"audit envelope is missing: {path}")
    envelope_path = path.resolve()
    envelope = read_json(envelope_path)
    if not isinstance(envelope, dict):
        raise CrewChiefError("audit envelope must be a JSON object")
    validate_instance("audit-envelope-v1.schema.json", envelope)
    return envelope_path, envelope


def verify_envelope(
    path: Path,
    *,
    clock: Callable[[], datetime] = utc_now,
    require_current_state: bool = True,
) -> dict[str, Any]:
    """Verify frozen bytes, current Git state, repository identity, and expiry."""
    envelope_path, envelope = load_envelope(path)
    envelope_root = envelope_path.parent
    expected_hash = envelope["envelope_hash"]
    unhashed = copy.deepcopy(envelope)
    unhashed.pop("envelope_hash")
    if sha256_bytes(canonical_json_bytes(unhashed)) != expected_hash:
        raise CrewChiefError("audit envelope hash is invalid")
    now = clock_value(clock)
    created = parse_time(envelope["created_at"])
    expires = parse_time(envelope["expires_at"])
    if expires <= created or expires - created > timedelta(hours=24):
        raise CrewChiefError("audit envelope has an invalid validity window")
    expected_envelope_id = sha256_bytes(
        canonical_json_bytes(
            {
                "audit_id": envelope["audit_id"],
                "created_at": isoformat(created),
                "expires_at": isoformat(expires),
            }
        )
    )
    if envelope["envelope_id"] != expected_envelope_id:
        raise CrewChiefError("envelope identifier does not bind its audit and time window")
    if now >= expires:
        raise CrewChiefError("audit envelope has expired")

    repository = resolve_repository(Path(envelope["repository"]["repository_root"]))
    if repository_identity(repository) != envelope["repository"]:
        raise CrewChiefError("canonical repository identity changed")
    if require_current_state and git_state(repository) != envelope["git_state"]:
        raise CrewChiefError("Git state drifted after evidence freezing")

    mission_relative = normalize_repo_path(envelope["mission"]["repository_path"])
    mission_path = ensure_within_repository(
        repository,
        repository.joinpath(*Path(mission_relative).parts),
        "mission record",
    )
    frozen_mission = _bound_path(
        envelope_root, envelope["mission"]["frozen"], "frozen mission record"
    )
    if require_current_state and (
        not mission_path.is_file()
        or sha256_file(mission_path) != sha256_file(frozen_mission)
    ):
        raise CrewChiefError("mission record is missing or changed after freezing")

    manifest_path = _bound_path(
        envelope_root, envelope["manifest"], "evidence manifest"
    )
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise CrewChiefError("evidence manifest must be a JSON object")
    required_manifest = {
        "schema_version",
        "repository_id",
        "mission",
        "subject",
        "git_state",
        "risk_profile",
        "diffs",
        "untracked_files",
        "engineer_report",
        "evidence_artifacts",
        "test_claims",
        "controls",
    }
    if required_manifest - set(manifest):
        raise CrewChiefError("evidence manifest is incomplete")
    if not isinstance(manifest["subject"], dict):
        raise CrewChiefError("evidence manifest subject is invalid")
    if sha256_bytes(canonical_json_bytes(manifest)) != envelope["audit_id"]:
        raise CrewChiefError("audit identifier does not bind the manifest")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise CrewChiefError("evidence manifest schema version is unsupported")
    if manifest["repository_id"] != envelope["repository"]["repository_id"]:
        raise CrewChiefError("manifest and envelope repository identity disagree")
    if manifest["mission"] != envelope["mission"]:
        raise CrewChiefError("manifest and envelope mission binding disagree")
    if manifest["risk_profile"] != envelope["risk_profile"]:
        raise CrewChiefError("manifest and envelope risk profile disagree")
    subject_fields = ("mode", "base_commit", "head_commit", "authorized_untracked")
    if any(
        manifest["subject"].get(field) != envelope["subject"][field]
        for field in subject_fields
    ):
        raise CrewChiefError("manifest and envelope subject disagree")
    for binding in _manifest_bindings(manifest):
        _bound_path(envelope_root, binding, "frozen evidence")

    if require_current_state:
        subject, _, _ = capture_subject(
            repository,
            envelope["subject"]["base_commit"],
            envelope["subject"]["head_commit"],
            include_worktree=envelope["subject"]["mode"] == "working-tree",
            authorized_untracked=envelope["subject"]["authorized_untracked"],
        )
        if subject != manifest["subject"]:
            raise CrewChiefError("changed-file evidence drifted after freezing")
    if manifest["git_state"] != envelope["git_state"]:
        raise CrewChiefError("manifest and envelope Git state disagree")
    return envelope


def reconcile_report(
    envelope: dict[str, Any],
    report: dict[str, Any],
    dispositions: list[dict[str, Any]],
    *,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    validate_report(envelope, report)
    ordered = sorted((copy.deepcopy(item) for item in dispositions), key=lambda item: item.get("finding_id", ""))
    findings = {item["finding_id"]: item for item in report["findings"]}
    ids = [item.get("finding_id") for item in ordered]
    if len(ids) != len(set(ids)) or set(ids) != set(findings):
        raise CrewChiefError("every finding requires exactly one disposition")
    approval_ready = all(
        not findings[item["finding_id"]]["blocking"]
        or item.get("disposition") == "resolved"
        for item in ordered
    )
    package = {
        "schema_version": SCHEMA_VERSION,
        "canary": CANARY,
        "audit_id": report["audit_id"],
        "envelope_id": report["envelope_id"],
        "report_hash": sha256_bytes(canonical_json_bytes(report)),
        "dispositions": ordered,
        "reconciliation_complete": True,
        "approval_ready": approval_ready,
        "generated_at": isoformat(clock_value(clock)),
        "authority_statement": (
            "Maverick retains final approval and mission-completion authority."
        ),
    }
    package["package_hash"] = sha256_bytes(canonical_json_bytes(package))
    validate_reconciliation(package, report)
    return package


def render_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Crew Chief Report — Non-Canonical View",
        "",
        "> Generated from validated structured JSON. The JSON report is canonical.",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Audit ID: `{report['audit_id']}`",
        f"- Findings: {len(report['findings'])}",
        "",
    ]
    for finding in report["findings"]:
        lines.extend(
            [
                f"## {finding['finding_id']} — {finding['severity']}",
                "",
                finding["why_it_matters"],
                "",
                f"Action ({finding['action_kind']}): {finding['action']}",
                "",
            ]
        )
    return "\n".join(lines)


def render_reconciliation_markdown(package: dict[str, Any]) -> str:
    lines = [
        "# Crew Chief Reconciliation — Non-Canonical View",
        "",
        "> Generated from validated structured JSON. The JSON package is canonical.",
        "",
        f"- Reconciliation complete: `{str(package['reconciliation_complete']).lower()}`",
        f"- Approval ready: `{str(package['approval_ready']).lower()}`",
        "",
    ]
    for item in package["dispositions"]:
        lines.extend(
            [
                f"## {item['finding_id']} — {item['disposition']}",
                "",
                item["summary"],
                "",
            ]
        )
    return "\n".join(lines)
