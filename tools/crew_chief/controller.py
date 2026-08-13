"""Deterministic Crew Chief envelope and reconciliation controller."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable

from tools.crew_chief.core import (
    AGENT_PATH,
    CANARY,
    PROFILE_FOCUS,
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


def _require_substantive_task_authority(path: Path) -> None:
    try:
        content = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CrewChiefError("task authority must be valid UTF-8 text") from error
    if not content.strip():
        raise CrewChiefError("task authority must not be empty or whitespace-only")


def _closeout_context(
    path: Path,
    *,
    legacy_mission_reference: str | None = None,
) -> dict[str, Any]:
    value = read_json(path)
    if not isinstance(value, dict):
        raise CrewChiefError("engineer report must be a JSON object")
    context = value.get("closeout")
    if not isinstance(context, dict):
        if legacy_mission_reference is None:
            raise CrewChiefError(
                "engineer report requires a structured closeout object"
            )

        def legacy_list(name: str) -> list[str]:
            items = value.get(name, [])
            if isinstance(items, str) and items.strip():
                return [items.strip()]
            if isinstance(items, list) and all(
                isinstance(item, str) and item.strip() for item in items
            ):
                return [item.strip() for item in items]
            return []

        return {
            "objective": (
                "Objective is governed by verified legacy mission record "
                f"{legacy_mission_reference}."
            ),
            "scope": legacy_list("scope")
            or [
                "Scope is governed by verified legacy mission record "
                f"{legacy_mission_reference}."
            ],
            "exclusions": legacy_list("exclusions"),
            "limitations": legacy_list("limitations"),
            "deferred_work": legacy_list("deferred_work"),
        }
    objective = context.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        raise CrewChiefError("engineer report closeout objective is required")

    def string_list(name: str, *, required: bool = False) -> list[str]:
        items = context.get(name)
        if not isinstance(items, list) or any(
            not isinstance(item, str) or not item.strip() for item in items
        ):
            raise CrewChiefError(
                f"engineer report closeout {name} must be a list of non-empty strings"
            )
        if required and not items:
            raise CrewChiefError(f"engineer report closeout {name} must not be empty")
        return [item.strip() for item in items]

    return {
        "objective": objective.strip(),
        "scope": string_list("scope", required=True),
        "exclusions": string_list("exclusions"),
        "limitations": string_list("limitations"),
        "deferred_work": string_list("deferred_work"),
    }


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
        "required_focus": list(PROFILE_FOCUS[name]),
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
                "frozen": copy_bound_file(source, target, f"controls/schemas/{name}"),
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
    task_authority: Path | None = None,
    mission_record: Path | None = None,
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
        raise CrewChiefError(
            "audit envelope expiry must be between 1 and 86400 seconds"
        )
    if not isinstance(test_claims, dict) or not test_claims:
        raise CrewChiefError("test and validation claims must be a non-empty object")

    if task_authority is None and mission_record is None:
        raise CrewChiefError(
            "audit preparation requires task authority or a mission record"
        )
    task_authority_source = (
        _input_file(task_authority, "task authority")
        if task_authority is not None
        else None
    )
    if task_authority_source is not None:
        _require_substantive_task_authority(task_authority_source)
    mission_source = None
    mission_relative = None
    if mission_record is not None:
        mission_source = ensure_within_repository(
            repository, mission_record, "mission record"
        )
        mission_source = _input_file(mission_source, "mission record")
        if mission_source.stat().st_size == 0:
            raise CrewChiefError("mission record must not be empty")
        mission_relative = mission_source.relative_to(repository).as_posix()
    engineer_source = _input_file(engineer_report, "engineer report")
    _closeout_context(
        engineer_source,
        legacy_mission_reference=(
            mission_relative if task_authority_source is None else None
        ),
    )
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

    subject, diff_payloads, content_payloads = capture_subject(
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

    task_authority_binding = None
    if task_authority_source is not None:
        task_suffix = task_authority_source.suffix or ".bin"
        task_relative = f"evidence/task-authority{task_suffix}"
        task_authority_binding = copy_bound_file(
            task_authority_source,
            output / task_relative,
            task_relative,
        )
    mission_binding = None
    if mission_source is not None:
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
    test_claims_binding = bind_file(output / test_claims_relative, test_claims_relative)

    evidence_bindings = []
    for index, source in enumerate(evidence_sources, start=1):
        relative = _artifact_target(index, source)
        evidence_bindings.append(
            {
                "artifact_id": f"evidence:{index:03d}",
                "label": source.name,
                "frozen": copy_bound_file(source, output / relative, relative),
            }
        )

    diff_bindings = []
    for name, payload in sorted(diff_payloads.items()):
        relative = f"diffs/{name}"
        atomic_write(output / relative, payload)
        diff_bindings.append(
            {
                "artifact_id": f"diff:{name}",
                "name": name,
                "frozen": bind_file(output / relative, relative),
            }
        )

    for relative, payload in sorted(content_payloads.items()):
        atomic_write(output / relative, payload)

    untracked_bindings = []
    for path in subject["authorized_untracked"]:
        material = next(
            (
                item
                for item in subject["source_material"]
                if item["repository_path"] == path
                and item["state"] == "worktree"
                and item["presence"] == "present"
            ),
            None,
        )
        if material is None or material["frozen"] is None:
            raise CrewChiefError(f"authorized untracked content was not frozen: {path}")
        untracked_bindings.append(
            {
                "repository_path": path,
                "frozen": material["frozen"],
            }
        )

    controls = _copy_controls(repository, output)
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "repository_id": identity["repository_id"],
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
    if task_authority_binding is not None:
        manifest["task_authority"] = task_authority_binding
    if mission_binding is not None:
        manifest["mission"] = {
            "repository_path": mission_relative,
            "frozen": mission_binding,
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
    envelope: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "canary": CANARY,
        "audit_id": audit_id,
        "envelope_id": envelope_id,
        "repository": identity,
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
    if task_authority_binding is not None:
        envelope["task_authority"] = task_authority_binding
    if mission_binding is not None:
        envelope["mission"] = {
            "repository_path": mission_relative,
            "frozen": mission_binding,
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


def _verified_report_evidence(
    envelope_root: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    material = manifest["subject"].get("source_material")
    if not isinstance(material, list):
        raise CrewChiefError("evidence manifest lacks frozen source material")
    sources = []
    source_keys = set()
    for item in material:
        if not isinstance(item, dict):
            raise CrewChiefError("frozen source material entry is invalid")
        try:
            path = normalize_repo_path(item["repository_path"])
            state = item["state"]
            presence = item["presence"]
        except (KeyError, TypeError) as error:
            raise CrewChiefError(
                "frozen source material entry is incomplete"
            ) from error
        if state not in {"base", "head", "index", "worktree"}:
            raise CrewChiefError(f"frozen source state is invalid: {state!r}")
        key = (path, state)
        if key in source_keys:
            raise CrewChiefError(
                f"frozen source material is duplicated: {path} ({state})"
            )
        source_keys.add(key)
        if presence == "absent":
            if item.get("frozen") is not None:
                raise CrewChiefError(
                    f"absent source material has frozen content: {path} ({state})"
                )
            continue
        if presence != "present":
            raise CrewChiefError(f"frozen source presence is invalid: {path} ({state})")
        binding = item.get("frozen")
        if binding is None:
            if item.get("file_type") == "submodule":
                continue
            raise CrewChiefError(
                f"present source material lacks frozen content: {path} ({state})"
            )
        if not isinstance(binding, dict):
            raise CrewChiefError(f"frozen source binding is invalid: {path} ({state})")
        sources.append(
            {
                "path": path,
                "state": state,
                "revision": item.get("revision"),
                "file_type": item.get("file_type"),
                "encoding": item.get("encoding"),
                "line_count": item.get("line_count"),
                "reference": binding["path"],
            }
        )

    artifacts = []

    def add_artifact(identifier: str, binding: dict[str, Any]) -> None:
        artifacts.append({"artifact": identifier, "reference": binding["path"]})

    authority_sources = []
    task_binding = manifest.get("task_authority")
    if task_binding is not None:
        add_artifact("task_authority", task_binding)
        authority_sources.append(
            {
                "kind": "task_authority",
                "artifact": "task_authority",
                "reference": task_binding["path"],
                "sha256": task_binding["sha256"],
                "size": task_binding["size"],
            }
        )
    mission = manifest.get("mission")
    if mission is not None:
        mission_binding = mission["frozen"]
        add_artifact("mission_record", mission_binding)
        authority_sources.append(
            {
                "kind": "mission_record",
                "artifact": "mission_record",
                "reference": mission_binding["path"],
                "sha256": mission_binding["sha256"],
                "size": mission_binding["size"],
                "repository_path": mission["repository_path"],
            }
        )
    add_artifact("engineer_report", manifest["engineer_report"])
    add_artifact("test_claims", manifest["test_claims"])
    for item in manifest["diffs"]:
        add_artifact(item["artifact_id"], item["frozen"])
    for item in manifest["evidence_artifacts"]:
        add_artifact(item["artifact_id"], item["frozen"])
    controls = manifest["controls"]
    add_artifact("control:repository_instructions", controls["repository_instructions"])
    add_artifact("control:agent", controls["agent"])
    for item in controls["schemas"]:
        add_artifact(f"control:schema:{item['name']}", item["frozen"])
    artifact_keys = [(item["artifact"], item["reference"]) for item in artifacts]
    if len(artifact_keys) != len(set(artifact_keys)):
        raise CrewChiefError("frozen artifact citation identifiers are duplicated")

    claims_path = _bound_path(
        envelope_root, manifest["test_claims"], "frozen test claims"
    )
    claims = read_json(claims_path)
    if not isinstance(claims, dict):
        raise CrewChiefError("frozen test claims must be a JSON object")
    engineer_path = _bound_path(
        envelope_root, manifest["engineer_report"], "frozen engineer report"
    )
    return {
        "sources": sources,
        "artifacts": artifacts,
        "authority_sources": authority_sources,
        "closeout_context": _closeout_context(
            engineer_path,
            legacy_mission_reference=(
                mission["repository_path"]
                if task_binding is None and mission is not None
                else None
            ),
        ),
        "test_claims": copy.deepcopy(claims),
        "exempt_governance_validation": bool(claims.get("governance_validation")),
    }


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
        raise CrewChiefError(
            "envelope identifier does not bind its audit and time window"
        )
    if now >= expires:
        raise CrewChiefError("audit envelope has expired")

    repository = resolve_repository(Path(envelope["repository"]["repository_root"]))
    if repository_identity(repository) != envelope["repository"]:
        raise CrewChiefError("canonical repository identity changed")
    if require_current_state and git_state(repository) != envelope["git_state"]:
        raise CrewChiefError("Git state drifted after evidence freezing")

    mission = envelope.get("mission")
    if mission is not None:
        mission_relative = normalize_repo_path(mission["repository_path"])
        mission_path = ensure_within_repository(
            repository,
            repository.joinpath(*Path(mission_relative).parts),
            "mission record",
        )
        frozen_mission = _bound_path(
            envelope_root, mission["frozen"], "frozen mission record"
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
    authority_keys = {"task_authority", "mission"}
    envelope_authority = authority_keys.intersection(envelope)
    manifest_authority = authority_keys.intersection(manifest)
    if not envelope_authority or envelope_authority != manifest_authority:
        raise CrewChiefError("envelope and manifest authority bindings disagree")
    if not isinstance(manifest["subject"], dict):
        raise CrewChiefError("evidence manifest subject is invalid")
    if sha256_bytes(canonical_json_bytes(manifest)) != envelope["audit_id"]:
        raise CrewChiefError("audit identifier does not bind the manifest")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise CrewChiefError("evidence manifest schema version is unsupported")
    if manifest["repository_id"] != envelope["repository"]["repository_id"]:
        raise CrewChiefError("manifest and envelope repository identity disagree")
    for key in sorted(envelope_authority):
        if manifest[key] != envelope[key]:
            raise CrewChiefError(
                f"manifest and envelope {key.replace('_', ' ')} binding disagree"
            )
    if manifest["risk_profile"] != envelope["risk_profile"]:
        raise CrewChiefError("manifest and envelope risk profile disagree")
    profile_name = envelope["risk_profile"]["name"]
    if envelope["risk_profile"]["required_focus"] != list(PROFILE_FOCUS[profile_name]):
        raise CrewChiefError("audit risk profile focus is not canonical")
    subject_fields = ("mode", "base_commit", "head_commit", "authorized_untracked")
    if any(
        manifest["subject"].get(field) != envelope["subject"][field]
        for field in subject_fields
    ):
        raise CrewChiefError("manifest and envelope subject disagree")
    for binding in _manifest_bindings(manifest):
        _bound_path(envelope_root, binding, "frozen evidence")
    task_authority = envelope.get("task_authority")
    if task_authority is not None:
        _require_substantive_task_authority(
            _bound_path(
                envelope_root,
                task_authority,
                "frozen task authority",
            )
        )

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
    verified_evidence = _verified_report_evidence(envelope_root, manifest)
    if profile_name == "exempt":
        if not envelope["risk_profile"]["justification"].strip():
            raise CrewChiefError("exempt profile lacks its governed justification")
        if not verified_evidence["exempt_governance_validation"]:
            raise CrewChiefError(
                "exempt profile lacks bound governance validation evidence"
            )
    envelope["_verified_evidence"] = verified_evidence
    envelope["_verified_manifest"] = manifest
    return envelope


def validate_proposed_closeout_record(record: dict[str, Any]) -> None:
    """Validate the proposal schema and its immutable audit-evidence digest."""
    validate_instance("proposed-closeout-v1.schema.json", record)
    expected = sha256_bytes(canonical_json_bytes(record["audit_evidence"]))
    if record["audit_evidence_sha256"] != expected:
        raise CrewChiefError("proposed closeout audit evidence hash is invalid")


def build_proposed_closeout_record(
    envelope: dict[str, Any],
    report: dict[str, Any],
    *,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Build an external, non-landed closeout proposal from a valid PASS."""
    validate_report(envelope, report)
    if report["verdict"] != "PASS" or report["findings"] or report["blocked_reasons"]:
        raise CrewChiefError(
            "proposed closeout requires a zero-finding Crew Chief PASS"
        )
    verified = envelope.get("_verified_evidence")
    manifest = envelope.get("_verified_manifest")
    if not isinstance(verified, dict) or not isinstance(manifest, dict):
        raise CrewChiefError("proposed closeout requires a verified audit envelope")
    context = verified.get("closeout_context")
    authority_sources = verified.get("authority_sources")
    test_claims = verified.get("test_claims")
    if (
        not isinstance(context, dict)
        or not isinstance(authority_sources, list)
        or not authority_sources
        or not isinstance(test_claims, dict)
        or not test_claims
    ):
        raise CrewChiefError("verified closeout evidence is incomplete")

    changed_files = [
        {
            "path": item["path"],
            "sources": list(item["sources"]),
            "file_type": item["file_type"],
        }
        for item in manifest["subject"]["changed_files"]
    ]
    audit_evidence = {
        "objective": context["objective"],
        "authority_sources": copy.deepcopy(authority_sources),
        "scope": {
            "included": list(context["scope"]),
            "excluded": list(context["exclusions"]),
        },
        "changed_files": changed_files,
        "tests_and_checks": copy.deepcopy(test_claims),
        "audit": {
            "audit_id": report["audit_id"],
            "envelope_id": report["envelope_id"],
            "report_sha256": sha256_bytes(canonical_json_bytes(report)),
            "verdict": report["verdict"],
            "findings_count": len(report["findings"]),
            "report_generated_at": report["generated_at"],
        },
        "limitations": list(context["limitations"]),
        "deferred_work": list(context["deferred_work"]),
        "repository": {
            "repository_id": envelope["repository"]["repository_id"],
            "repository_root": envelope["repository"]["repository_root"],
            "branch": envelope["git_state"]["branch"],
            "subject_mode": envelope["subject"]["mode"],
            "base_commit": envelope["subject"]["base_commit"],
            "head_commit": envelope["subject"]["head_commit"],
            "authorized_untracked": list(envelope["subject"]["authorized_untracked"]),
            "status_porcelain_v1": list(envelope["git_state"]["status_porcelain_v1"]),
            "candidate_state_hash": envelope["git_state"]["state_hash"],
            "manifest": copy.deepcopy(envelope["manifest"]),
        },
    }
    record = {
        "schema_version": SCHEMA_VERSION,
        "canary": CANARY,
        "record_type": "crew_chief_closeout",
        "status": "proposed_external_not_landed",
        "generated_at": isoformat(clock_value(clock)),
        "audit_evidence": audit_evidence,
        "audit_evidence_sha256": sha256_bytes(canonical_json_bytes(audit_evidence)),
        "lso_handoff": {
            "responsible_role": "LSO",
            "next_action": (
                "Validate this proposal against the unchanged audited candidate, "
                "add verified landing facts, and land both together only under "
                "Maverick's authorization."
            ),
            "required_landing_facts": [
                "implementation_commit_hashes",
                "remote_refs",
                "landing_result",
                "landing_timestamps",
                "completion_state",
            ],
            "approval_claimed": False,
            "repository_mutation_claimed": False,
            "completion_claimed": False,
        },
    }
    validate_proposed_closeout_record(record)
    return record


def reconcile_report(
    envelope: dict[str, Any],
    report: dict[str, Any],
    dispositions: list[dict[str, Any]],
    *,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    validate_report(envelope, report)
    ordered = sorted(
        (copy.deepcopy(item) for item in dispositions),
        key=lambda item: item.get("finding_id", ""),
    )
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
