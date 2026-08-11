"""Generate and validate Wingman's canonical repository records."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[2]
MISSION_ROOT = ROOT / "docs" / "missions"
DECISION_ROOT = ROOT / "docs" / "decisions"
ARCHIVE_ROOT = ROOT / "docs" / "archive"
CANONICAL_MERGE_TARGET = "refs/remotes/origin/main"
RATIFICATION_DECISION = (
    ROOT / "docs/decisions/governance/historical-mission-ratification.md"
)
FOREGROUND_PRESERVATION_MANIFEST = (
    MISSION_ROOT
    / "governance/repository-architecture/artifacts"
    / "foreground-preservation-manifest.json"
)
REPOSITORY_MAP = ROOT / "docs" / "README.md"
REPOSITORY_MAP_LOCATIONS = (
    (".codex/", "directory"),
    (".codex/agents/", "directory"),
    ("AGENTS.md", "file"),
    ("CURRENT_MISSION.md", "file"),
    ("WINGMAN_VAULT.md", "file"),
    ("README.md", "file"),
    ("src/", "directory"),
    ("src/wingman/", "directory"),
    ("src/wingman/core/", "directory"),
    ("src/wingman/core/ledger/", "directory"),
    ("src/wingman/shared/", "directory"),
    ("src/products/", "directory"),
    ("src/products/atlas/", "directory"),
    ("src/products/radar/", "directory"),
    ("src/ledger/", "directory"),
    ("docs/", "directory"),
    ("docs/wingman-os/", "directory"),
    ("docs/products/", "directory"),
    ("docs/products/atlas/", "directory"),
    ("docs/products/radar/", "directory"),
    ("docs/governance/", "directory"),
    ("docs/missions/", "directory"),
    ("docs/missions/wingman-os/", "directory"),
    ("docs/missions/atlas/", "directory"),
    ("docs/missions/operations/", "directory"),
    ("docs/missions/governance/", "directory"),
    ("docs/decisions/", "directory"),
    ("docs/decisions/architecture/", "directory"),
    ("docs/decisions/governance/", "directory"),
    ("docs/decisions/security/", "directory"),
    ("docs/runbooks/", "directory"),
    ("docs/archive/", "directory"),
    ("docs/roadmap.md", "file"),
    ("tests/", "directory"),
    ("tests/wingman/", "directory"),
    ("tests/products/", "directory"),
    ("tests/products/atlas/", "directory"),
    ("tests/products/radar/", "directory"),
    ("tests/governance/", "directory"),
    ("tools/", "directory"),
    ("tools/crew_chief/", "directory"),
    ("tools/flightline/", "directory"),
    ("tools/governance/", "directory"),
    ("data/", "directory"),
)
REPOSITORY_MAP_COMPATIBILITY_WARNING = (
    "Historical flat `src/` modules and `src/ledger/` are compatibility "
    "façades only; no new implementation belongs there."
)
MISSION_MARKER = "wingman-mission-metadata"
DECISION_MARKER = "wingman-decision-metadata"
ARCHIVE_MARKER = "wingman-archive-metadata"
MISSION_ID = re.compile(r"^[a-z0-9-]+(?:/[a-z0-9-]+)+$")
DECISION_ID = re.compile(r"^[A-Z]+-[0-9]{3}$")
COMMIT_ID = re.compile(r"^[0-9a-f]{7,40}$")
LIFECYCLES = frozenset({"draft", "active", "completed", "archived"})
DECISION_STATES = frozenset({"proposed", "accepted", "superseded"})
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
JUNK_NAMES = frozenset({".DS_Store", "Thumbs.db", "Desktop.ini"})


class GovernanceError(ValueError):
    """One or more repository-governance invariants failed."""


@dataclass(frozen=True)
class Record:
    path: Path
    metadata: dict


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _metadata(path: Path, marker: str) -> dict:
    text = path.read_text(encoding="utf-8")
    prefix = f"<!-- {marker}\n"
    try:
        payload = text.split(prefix, 1)[1].split("\n-->", 1)[0]
    except IndexError as error:
        raise GovernanceError(
            f"{_relative(path)} has no {marker} block"
        ) from error
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise GovernanceError(
            f"{_relative(path)} has invalid JSON metadata: {error}"
        ) from error
    if not isinstance(value, dict):
        raise GovernanceError(f"{_relative(path)} metadata must be an object")
    return value


def load_missions() -> list[Record]:
    return [
        Record(path, _metadata(path, MISSION_MARKER))
        for path in sorted(MISSION_ROOT.rglob("mission.md"))
    ]


def load_decisions() -> list[Record]:
    return [
        Record(path, _metadata(path, DECISION_MARKER))
        for path in sorted(DECISION_ROOT.rglob("*.md"))
        if path.name != "README.md"
    ]


def _require_fields(record: Record, required: set[str], errors: list[str]) -> None:
    missing = sorted(required - set(record.metadata))
    if missing:
        errors.append(f"{_relative(record.path)} missing fields: {missing}")


def _duplicates(values: list[str]) -> list[str]:
    return sorted({value for value in values if values.count(value) > 1})


def _schema(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(value)
    return value


def validate_record_schemas(
    missions: list[Record], decisions: list[Record]
) -> list[str]:
    """Validate embedded metadata with real Draft 2020-12 validators."""
    errors: list[str] = []
    validators = (
        (Draft202012Validator(_schema(ROOT / "docs/governance/mission.schema.json")), missions),
        (Draft202012Validator(_schema(ROOT / "docs/governance/decision.schema.json")), decisions),
    )
    for validator, records in validators:
        for record in records:
            for error in sorted(
                validator.iter_errors(record.metadata),
                key=lambda item: tuple(str(part) for part in item.absolute_path),
            ):
                location = ".".join(str(part) for part in error.absolute_path)
                suffix = f" at {location}" if location else ""
                errors.append(
                    f"{_relative(record.path)}: schema violation{suffix}: "
                    f"{error.message}"
                )
    return errors


def _git_result(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


@lru_cache(maxsize=None)
def _commit_exists(commit: str) -> bool:
    return _git_result("cat-file", "-e", f"{commit}^{{commit}}").returncode == 0


@lru_cache(maxsize=None)
def _commit_is_reachable(commit: str) -> bool:
    return _git_result("merge-base", "--is-ancestor", commit, "HEAD").returncode == 0


@lru_cache(maxsize=None)
def _remote_refs_containing(commit: str) -> tuple[str, ...]:
    result = _git_result(
        "for-each-ref", "--format=%(refname)", "--contains", commit,
        "refs/remotes/",
    )
    if result.returncode != 0:
        return ()
    return tuple(
        ref for ref in result.stdout.splitlines()
        if ref and not ref.endswith("/HEAD")
    )


@lru_cache(maxsize=None)
def _merge_target_exists() -> bool:
    return _git_result("show-ref", "--verify", "--quiet", CANONICAL_MERGE_TARGET).returncode == 0


@lru_cache(maxsize=None)
def _merge_target_contains(commit: str) -> bool:
    if not _merge_target_exists():
        return False
    return _git_result(
        "merge-base", "--is-ancestor", commit, CANONICAL_MERGE_TARGET
    ).returncode == 0


def _git_rename_destinations(baseline: str, comparison: str) -> dict[str, str]:
    """Return Git-detected source-to-destination renames for an exact range."""
    result = _git_result(
        "diff", "--name-status", "--find-renames", baseline, comparison
    )
    if result.returncode != 0:
        raise GovernanceError(
            "could not obtain foreground preservation rename evidence: "
            f"{result.stderr.strip()}"
        )
    destinations: dict[str, str] = {}
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) == 3 and re.fullmatch(r"R\d{3}", fields[0]):
            destinations[fields[1]] = fields[2]
    return destinations


def _git_blob_sha256(commit: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return hashlib.sha256(result.stdout).hexdigest()


def validate_foreground_preservation_manifest(
    manifest: dict | None = None,
) -> list[str]:
    """Bind protected foreground dispositions to exact Git and byte evidence."""
    errors: list[str] = []
    if manifest is None:
        try:
            manifest = json.loads(
                FOREGROUND_PRESERVATION_MANIFEST.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            return [f"foreground preservation manifest is unreadable: {error}"]
    if not isinstance(manifest, dict):
        return ["foreground preservation manifest must be an object"]

    entries = manifest.get("entries")
    baseline = manifest.get("foreground_head")
    comparison = manifest.get("correction_comparison_head")
    if not isinstance(entries, list) or not isinstance(baseline, str) or not isinstance(
        comparison, str
    ):
        return ["foreground preservation manifest has incomplete range evidence"]

    if manifest.get("schema_version") != 1:
        errors.append("foreground preservation manifest schema_version must be 1")
    if len(entries) != 11:
        errors.append("foreground preservation manifest must contain 11 entries")
    observed_counts = {
        disposition: sum(
            entry.get("correction_disposition") == disposition
            for entry in entries
            if isinstance(entry, dict)
        )
        for disposition in ("deleted", "moved", "unchanged")
    }
    if manifest.get("path_disposition_counts") != observed_counts:
        errors.append("foreground preservation disposition counts disagree")
    if manifest.get("protected_foreground_versions_excluded") is not True:
        errors.append("foreground preservation exclusion claim must be true")
    for commit, label in ((baseline, "baseline"), (comparison, "comparison")):
        if not _commit_exists(commit):
            errors.append(f"foreground preservation {label} commit is missing: {commit}")
        elif not _commit_is_reachable(commit):
            errors.append(
                f"foreground preservation {label} commit is unreachable: {commit}"
            )

    try:
        rename_destinations = _git_rename_destinations(baseline, comparison)
    except GovernanceError as error:
        errors.append(str(error))
        rename_destinations = {}

    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("foreground preservation entry must be an object")
            continue
        source = entry.get("path")
        disposition = entry.get("correction_disposition")
        target = entry.get("target_path")
        if not isinstance(source, str):
            errors.append("foreground preservation entry path must be a string")
            continue
        if entry.get("foreground_version_incorporated") is not False:
            errors.append(f"{source}: foreground version must remain excluded")
        if entry.get("exact_working_version_matches_in_correction") != []:
            errors.append(f"{source}: foreground exact-byte matches must be empty")
        if disposition == "deleted":
            if target is not None or entry.get("target_path_sha256") is not None:
                errors.append(f"{source}: deleted disposition must have no target")
            continue
        if not isinstance(target, str) or not target:
            errors.append(f"{source}: {disposition} disposition needs a target")
            continue
        if disposition == "moved":
            git_target = rename_destinations.get(source)
            if git_target is None:
                errors.append(f"{source}: Git records no rename destination")
            elif target != git_target:
                errors.append(
                    f"{source}: declared moved target {target} disagrees with "
                    f"Git rename destination {git_target}"
                )
        digest = _git_blob_sha256(comparison, target)
        if digest is None:
            errors.append(f"{source}: target is absent at comparison commit: {target}")
        elif entry.get("target_path_sha256") != digest:
            errors.append(
                f"{source}: target SHA-256 disagrees with comparison commit"
            )
    return errors


def validate_metadata(
    missions: list[Record], decisions: list[Record]
) -> list[str]:
    errors: list[str] = []
    mission_required = {
        "schema_version", "id", "legacy_aliases", "title", "call_sign",
        "namespace", "lifecycle", "priority", "portfolio_primary",
        "authorization_gate", "approval_evidence", "baseline_commit",
        "implementation_commits", "pushed", "merged", "official_decisions",
        "next_gate", "supersedes", "superseded_by", "paused", "cancelled",
        "capability_health",
    }
    decision_required = {
        "schema_version", "id", "title", "namespaces", "status", "date",
        "authority", "scope", "approval_evidence", "supersedes",
        "superseded_by",
    }
    for record in missions:
        _require_fields(record, mission_required, errors)
    for record in decisions:
        _require_fields(record, decision_required, errors)
    if errors:
        return errors

    mission_ids = [record.metadata["id"] for record in missions]
    decision_ids = [record.metadata["id"] for record in decisions]
    aliases = [
        alias
        for record in missions
        for alias in record.metadata["legacy_aliases"]
    ]
    for duplicate in _duplicates(mission_ids):
        errors.append(f"duplicate mission ID: {duplicate}")
    for duplicate in _duplicates(decision_ids):
        errors.append(f"duplicate decision ID: {duplicate}")
    for duplicate in _duplicates(aliases):
        errors.append(f"colliding legacy mission alias: {duplicate}")

    primary = [
        record for record in missions
        if record.metadata["lifecycle"] == "active"
        and record.metadata["portfolio_primary"] is True
    ]
    if len(primary) > 1:
        errors.append(
            "at most one active mission may be portfolio-primary; "
            f"observed {len(primary)}"
        )

    for record in missions:
        metadata = record.metadata
        mission_id = metadata["id"]
        expected_path = MISSION_ROOT.joinpath(*mission_id.split("/"), "mission.md")
        if record.path != expected_path:
            errors.append(
                f"{mission_id}: record path must be {_relative(expected_path)}"
            )
        if metadata["schema_version"] != 1:
            errors.append(f"{mission_id}: unsupported schema_version")
        if not MISSION_ID.fullmatch(mission_id):
            errors.append(f"{mission_id}: invalid namespaced mission ID")
        if metadata["lifecycle"] not in LIFECYCLES:
            errors.append(f"{mission_id}: invalid lifecycle")
        if not isinstance(metadata["pushed"], bool) or not isinstance(
            metadata["merged"], bool
        ):
            errors.append(f"{mission_id}: pushed and merged must be booleans")
        if metadata["merged"] and not metadata["pushed"]:
            errors.append(f"{mission_id}: merged cannot be true when pushed is false")
        if not metadata["approval_evidence"]:
            errors.append(f"{mission_id}: approval evidence is required")
        if metadata["lifecycle"] == "active":
            workstream = metadata.get("workstream")
            required = {
                "owner_session", "branch", "worktree", "writable_scope",
                "state", "next_gate",
            }
            if not isinstance(workstream, dict) or required - set(workstream):
                errors.append(f"{mission_id}: active workstream metadata incomplete")
            else:
                scopes = workstream["writable_scope"]
                if not isinstance(scopes, list) or not scopes:
                    errors.append(f"{mission_id}: writable_scope must be non-empty")
        if (
            metadata["lifecycle"] == "completed"
            and not metadata["implementation_commits"]
        ):
            errors.append(f"{mission_id}: completed mission needs an implementation commit")
        for commit in [metadata["baseline_commit"], *metadata["implementation_commits"]]:
            if commit is None:
                continue
            if not isinstance(commit, str) or not COMMIT_ID.fullmatch(commit):
                errors.append(f"{mission_id}: invalid commit ID {commit!r}")
            elif not _commit_exists(commit):
                errors.append(f"{mission_id}: recorded commit does not exist: {commit}")
            elif not _commit_is_reachable(commit):
                errors.append(f"{mission_id}: recorded commit not reachable from HEAD: {commit}")
        for decision_path in metadata["official_decisions"]:
            if not (ROOT / decision_path).is_file():
                errors.append(f"{mission_id}: decision link does not resolve: {decision_path}")

    known_decisions = set(decision_ids)
    for record in decisions:
        metadata = record.metadata
        decision_id = metadata["id"]
        if metadata["schema_version"] != 1:
            errors.append(f"{decision_id}: unsupported schema_version")
        if not DECISION_ID.fullmatch(decision_id):
            errors.append(f"{decision_id}: invalid decision ID")
        if metadata["status"] not in DECISION_STATES:
            errors.append(f"{decision_id}: invalid decision status")
        if metadata["status"] == "superseded" and not metadata["superseded_by"]:
            errors.append(f"{decision_id}: superseded decision needs replacement")
        references = [*metadata["supersedes"]]
        if metadata["superseded_by"]:
            references.append(metadata["superseded_by"])
        for reference in references:
            if reference not in known_decisions:
                errors.append(f"{decision_id}: unknown decision reference {reference}")
    errors.extend(validate_historical_ratification(missions, decisions))
    errors.extend(validate_publication_evidence(missions))
    return errors


def validate_historical_ratification(
    missions: list[Record], decisions: list[Record]
) -> list[str]:
    """Bind the exact retrospective ratification to canonical mission records."""
    errors: list[str] = []
    ratification = next(
        (
            record for record in decisions
            if record.metadata["id"] == "GOV-003"
        ),
        None,
    )
    if ratification is None:
        return ["GOV-003 historical mission ratification is missing"]
    entries = ratification.metadata.get("ratified_missions", [])
    ratified = {entry["id"]: entry["implementation_commits"] for entry in entries}
    if len(entries) != len(ratified):
        errors.append("GOV-003 ratified mission IDs must be unique")
    mission_by_id = {record.metadata["id"]: record for record in missions}
    body = ratification.path.read_text(encoding="utf-8")
    decision_path = _relative(RATIFICATION_DECISION)
    for mission_id, commits in ratified.items():
        record = mission_by_id.get(mission_id)
        if record is None:
            errors.append(f"{mission_id}: GOV-003 ratified mission is missing")
            continue
        if record.metadata["lifecycle"] != "completed":
            errors.append(f"{mission_id}: GOV-003 ratified mission is not completed")
            continue
        if record.metadata["implementation_commits"] != commits:
            errors.append(f"{mission_id}: GOV-003 commit inventory disagrees")
        if decision_path not in record.metadata["official_decisions"]:
            errors.append(f"{mission_id}: canonical record does not cite GOV-003")
        if not any(
            "GOV-003" in evidence["scope"]
            for evidence in record.metadata["approval_evidence"]
        ):
            errors.append(f"{mission_id}: completion evidence does not cite GOV-003")
        if f"| `{mission_id}` |" not in body:
            errors.append(f"GOV-003 readable table omits {mission_id}")
    return errors


def validate_publication_evidence(missions: list[Record]) -> list[str]:
    """Reconcile pushed/merged booleans with cached, nondestructive Git facts."""
    errors: list[str] = []
    for record in missions:
        metadata = record.metadata
        mission_id = metadata["id"]
        commits = metadata["implementation_commits"]
        published = bool(commits) and all(_remote_refs_containing(commit) for commit in commits)
        merged = bool(commits) and all(_merge_target_contains(commit) for commit in commits)
        if metadata["pushed"] != published:
            errors.append(
                f"{mission_id}: pushed={metadata['pushed']} contradicts cached "
                f"remote-tracking evidence ({published})"
            )
        if metadata["merged"] != merged:
            errors.append(
                f"{mission_id}: merged={metadata['merged']} contradicts "
                f"{CANONICAL_MERGE_TARGET} evidence ({merged})"
            )
    return errors


def _latest_completed(missions: list[Record]) -> Record:
    candidates = [
        record
        for record in missions
        if record.metadata["lifecycle"] == "completed"
        and record.metadata["implementation_commits"]
    ]

    def completion_timestamp(record: Record) -> int:
        commit = record.metadata["implementation_commits"][-1]
        value = subprocess.run(
            ["git", "show", "-s", "--format=%ct", commit],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return int(value)

    return max(
        candidates,
        key=lambda record: (
            completion_timestamp(record),
            record.metadata["id"],
        ),
    )


def render_current_mission(missions: list[Record]) -> str:
    primary = next((
        record for record in missions
        if record.metadata["lifecycle"] == "active"
        and record.metadata["portfolio_primary"]
    ), None)
    latest = _latest_completed(missions)
    latest_commit = latest.metadata["implementation_commits"][-1]
    lines = [
        "# Current Mission",
        "",
        "> Generated by `python -m tools.governance generate` from authoritative",
        "> records under `docs/missions/`. Do not edit this file directly.",
        "",
        "## Portfolio primary",
        "",
    ]
    if primary is None:
        lines.extend([
            "- Mission: **none**",
            "- Repository state: **between missions**",
            "- Implementation authority: **none**",
            "- Next gate: Maverick selects and authorizes a mission.",
        ])
    else:
        metadata = primary.metadata
        lines.extend([
            f"- Mission: **{metadata['id']} — {metadata['title']}**",
            f"- Lifecycle: **{metadata['lifecycle']}**",
            f"- Authorization gate: `{metadata['authorization_gate']}`",
            f"- Official record: [{_relative(primary.path)}]({_relative(primary.path)})",
            f"- Next gate: {metadata['next_gate']}",
        ])
    lines.extend([
        "",
        "## Last completed work",
        "",
        f"- **{latest.metadata['id']} — {latest.metadata['title']}**",
        f"- Commit: `{latest_commit}`",
        f"- Official record: [{_relative(latest.path)}]({_relative(latest.path)})",
        "",
        "## Active workstreams",
        "",
    ])
    active = sorted(
        (item for item in missions if item.metadata["lifecycle"] == "active"),
        key=lambda item: item.metadata["id"],
    )
    if not active:
        lines.append("None. The repository is between missions.")
    else:
        lines.extend([
            "| Mission | Role | Branch | Worktree | State | Next gate |",
            "|---|---|---|---|---|---|",
        ])
    for record in active:
        workstream = record.metadata["workstream"]
        role = "primary" if record.metadata["portfolio_primary"] else "secondary"
        lines.append(
            f"| `{record.metadata['id']}` | {role} | `{workstream['branch']}` | "
            f"`{workstream['worktree']}` | {workstream['state']} | {workstream['next_gate']} |"
        )
    lines.extend([
        "",
        "## Canonical homes",
        "",
        "- Operating instructions: `AGENTS.md`",
        "- Mission authority and status: `docs/missions/`",
        "- Enduring decisions: `docs/decisions/`",
        "- Current architecture: `docs/wingman-os/` and `docs/products/`",
        "- Governance policy and generated context: `docs/governance/`",
        "- Approved roadmap: `docs/roadmap.md`",
        "- Future capabilities and deferred obligations: `WINGMAN_VAULT.md`",
        "",
    ])
    return "\n".join(lines)


def render_mission_index(missions: list[Record]) -> str:
    lines = [
        "# Mission Index",
        "",
        "> Generated from authoritative `mission.md` metadata. Do not edit directly.",
        "",
        "| Mission ID | Legacy aliases | Lifecycle | Primary metadata | Commit state | Record |",
        "|---|---|---|---|---|---|",
    ]
    for record in sorted(missions, key=lambda item: item.metadata["id"]):
        metadata = record.metadata
        aliases = ", ".join(metadata["legacy_aliases"]) or "—"
        locally_committed = "locally_committed" in metadata.get(
            "workstream", {}
        ).get("state", "")
        if locally_committed and not metadata["implementation_commits"]:
            committed = "local (hash intentionally not self-recorded)"
        else:
            committed = "yes" if metadata["implementation_commits"] else "no"
        commit_state = (
            f"committed={committed}; pushed={'yes' if metadata['pushed'] else 'no'}; "
            f"merged={'yes' if metadata['merged'] else 'no'}"
        )
        lines.append(
            f"| `{metadata['id']}` | {aliases} | {metadata['lifecycle']} | "
            f"{'yes' if metadata['portfolio_primary'] else 'no'} | {commit_state} | "
            f"[{metadata['title']}]({record.path.relative_to(MISSION_ROOT).as_posix()}) |"
        )
    return "\n".join([*lines, ""])


def render_decision_index(decisions: list[Record]) -> str:
    lines = [
        "# Decision Index",
        "",
        "> Generated from authoritative decision metadata. Do not edit directly.",
        "",
        "| Decision | Namespaces | Status | Date | Record |",
        "|---|---|---|---|---|",
    ]
    for record in sorted(decisions, key=lambda item: item.metadata["id"]):
        metadata = record.metadata
        lines.append(
            f"| `{metadata['id']}` | {', '.join(metadata['namespaces'])} | "
            f"{metadata['status']} | {metadata['date']} | "
            f"[{metadata['title']}]({record.path.relative_to(DECISION_ROOT).as_posix()}) |"
        )
    return "\n".join([*lines, ""])


def render_context(missions: list[Record]) -> str:
    primary = next((
        record for record in missions
        if record.metadata["lifecycle"] == "active"
        and record.metadata["portfolio_primary"]
    ), None)
    latest = _latest_completed(missions)
    lines = [
        "# Mission Control Context",
        "",
        "> Generated from authoritative mission metadata. Refresh the external",
        "> ChatGPT Project mirror from this artifact after repository closeout.",
        "",
        "- Canary: `CANOPY-7C2F-ATLAS`",
        "- Authority: Maverick has final authority; Codex is the repository builder/operator.",
        "- First repository read: `AGENTS.md`",
    ]
    if primary is None:
        lines.extend([
            "- Portfolio-primary: `none`",
            "- Repository state: `between missions`",
            "- Implementation authority: `none`",
        ])
    else:
        lines.extend([
            f"- Portfolio-primary: `{primary.metadata['id']}` ({primary.metadata['lifecycle']})",
            f"- Authorization gate: `{primary.metadata['authorization_gate']}`",
            f"- Official record: `{_relative(primary.path)}`",
        ])
    lines.extend([
        f"- Last completed: `{latest.metadata['id']}` at `{latest.metadata['implementation_commits'][-1]}`",
        f"- Next gate: {primary.metadata['next_gate'] if primary else 'Maverick selects and authorizes a mission.'}",
        "",
    ])
    return "\n".join(lines)


GENERATED = {
    ROOT / "CURRENT_MISSION.md": render_current_mission,
    MISSION_ROOT / "README.md": render_mission_index,
    DECISION_ROOT / "README.md": render_decision_index,
    ROOT / "docs" / "governance" / "mission-control-context.md": render_context,
}


def generated_content(missions: list[Record], decisions: list[Record]) -> dict[Path, str]:
    return {
        path: renderer(decisions if renderer is render_decision_index else missions)
        for path, renderer in GENERATED.items()
    }


def generate() -> None:
    missions = load_missions()
    decisions = load_decisions()
    errors = validate_record_schemas(missions, decisions)
    if not errors:
        errors.extend(validate_metadata(missions, decisions))
    if errors:
        raise GovernanceError("\n".join(errors))
    for path, content in generated_content(missions, decisions).items():
        path.write_text(content, encoding="utf-8")


def validate_generated(missions: list[Record], decisions: list[Record]) -> list[str]:
    errors = []
    for path, expected in generated_content(missions, decisions).items():
        if not path.is_file():
            errors.append(f"missing generated file: {_relative(path)}")
        elif path.read_text(encoding="utf-8") != expected:
            errors.append(f"stale generated file: {_relative(path)}")
    return errors


def _canonical_markdown_files() -> list[Path]:
    files = [
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / "WINGMAN_VAULT.md",
        ROOT / "CURRENT_MISSION.md",
    ]
    files.extend(
        path
        for path in (ROOT / "docs").rglob("*.md")
        if "archive" not in path.relative_to(ROOT / "docs").parts
        and path.name != "journal.md"
        and "artifacts" not in path.parts
    )
    return sorted(set(files))


def validate_links_and_documents() -> list[str]:
    """Require canonical files and keep repository links root-confined."""
    errors: list[str] = []
    for path in _canonical_markdown_files():
        if not path.is_file():
            errors.append(f"missing canonical document: {_relative(path)}")
            continue
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            target = target.strip().split(maxsplit=1)[0].strip("<>")
            target = target.split("#", 1)[0]
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                continue
            resolved = (
                ROOT / target.lstrip("/")
                if target.startswith("/")
                else path.parent / target
            ).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(
                    f"{_relative(path)}: repository link escapes root: {target}"
                )
    return errors


def validate_link_target(source: Path, target: str) -> list[str]:
    """Validate one repository-relative link, including root confinement."""
    target = target.split("#", 1)[0]
    if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
        return []
    resolved = (
        ROOT / target.lstrip("/")
        if target.startswith("/")
        else source.parent / target
    ).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return [f"{_relative(source)}: repository link escapes root: {target}"]
    return []


def validate_repository_map(
    text: str | None = None,
) -> list[str]:
    """Keep the human filing map synchronized with canonical filesystem homes."""
    if text is None:
        text = REPOSITORY_MAP.read_text(encoding="utf-8")
    errors: list[str] = []
    for location, kind in REPOSITORY_MAP_LOCATIONS:
        if f"`{location}`" not in text:
            errors.append(f"repository map omits canonical location: {location}")
        path = ROOT / location.rstrip("/")
        exists = path.is_dir() if kind == "directory" else path.is_file()
        if not exists:
            errors.append(
                f"repository map canonical {kind} does not exist: {location}"
            )
    try:
        tree = text.split("### Annotated tree", 1)[1]
        tree = tree.split("```text", 1)[1].split("```", 1)[0]
    except IndexError:
        errors.append("repository map has no annotated tree")
    else:
        mapped_directories = sorted(set(re.findall(r"`([^`\n]+/)`", tree)))
        for location in mapped_directories:
            if not (ROOT / location.rstrip("/")).is_dir():
                errors.append(
                    f"repository map mapped directory does not exist: {location}"
                )
    normalized = " ".join(text.split())
    if REPOSITORY_MAP_COMPATIBILITY_WARNING not in normalized:
        errors.append(
            "repository map must identify historical flat src modules and "
            "src/ledger/ as compatibility facades only; no new implementation "
            "belongs there"
        )
    return errors


def _archive_metadata(path: Path, text: str) -> dict:
    prefix = f"<!-- {ARCHIVE_MARKER}\n"
    try:
        payload = text.split(prefix, 1)[1].split("\n-->", 1)[0]
        metadata = json.loads(payload)
    except (IndexError, json.JSONDecodeError) as error:
        raise GovernanceError(
            f"{_relative(path)} has no valid file-local archive classification"
        ) from error
    if not isinstance(metadata, dict):
        raise GovernanceError(f"{_relative(path)} archive metadata must be an object")
    return metadata


def validate_archive_document(path: Path, text: str) -> list[str]:
    """Require local classification, warning, and replacement for one archive."""
    errors: list[str] = []
    try:
        metadata = _archive_metadata(path, text)
    except GovernanceError as error:
        return [str(error)]
    expected_fields = {
        "schema_version", "classification", "canonical_replacement",
        "archived_from",
    }
    if set(metadata) != expected_fields:
        errors.append(f"{_relative(path)}: archive metadata fields are not exact")
        return errors
    if metadata["schema_version"] != 1:
        errors.append(f"{_relative(path)}: unsupported archive schema version")
    classification = metadata["classification"]
    if classification not in {"historical_noncanonical", "archive_index"}:
        errors.append(f"{_relative(path)}: invalid archive classification")
    warning = (
        r"HISTORICAL\s*/\s*NONCANONICAL"
        if classification == "historical_noncanonical"
        else r"NONCANONICAL ARCHIVE INDEX"
    )
    visible = re.search(warning, text, re.I)
    if not visible:
        errors.append(f"{_relative(path)}: missing file-local noncanonical warning")
    replacement = metadata["canonical_replacement"]
    if replacement is None:
        warning_text = re.sub(r"(?m)^>\s?", "", text)
        if not re.search(
            r"No\s+(?:single\s+)?canonical\s+replacement\s+exists",
            warning_text,
            re.I,
        ):
            errors.append(
                f"{_relative(path)}: missing explicit no-replacement statement"
            )
    elif not isinstance(replacement, str) or not replacement:
        errors.append(f"{_relative(path)}: invalid canonical replacement")
    else:
        canonical = (ROOT / replacement).resolve()
        try:
            canonical.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{_relative(path)}: archive replacement escapes root")
        else:
            if not canonical.exists():
                errors.append(
                    f"{_relative(path)}: archive replacement does not exist: "
                    f"{replacement}"
                )
            if replacement not in text:
                errors.append(
                    f"{_relative(path)}: replacement is not linked file-locally"
                )
    return errors


def validate_archive_documents() -> list[str]:
    errors: list[str] = []
    for path in sorted(item for item in ARCHIVE_ROOT.rglob("*") if item.is_file()):
        errors.extend(validate_archive_document(path, path.read_text(encoding="utf-8")))
        if path.name == "journal.md" and "mission-history" in path.parts:
            metadata = _archive_metadata(path, path.read_text(encoding="utf-8"))
            mission_id = "/".join(path.parts[path.parts.index("mission-history") + 1:-1])
            expected = f"docs/missions/{mission_id}/mission.md"
            if metadata.get("classification") != "historical_noncanonical":
                errors.append(f"{_relative(path)}: mission journal classification invalid")
            if metadata.get("canonical_replacement") != expected:
                errors.append(f"{_relative(path)}: mission journal replacement invalid")
    return errors


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def validate_repository_hygiene() -> list[str]:
    errors = []
    for path in _tracked_files():
        if path.name in JUNK_NAMES or path.name.startswith("._"):
            errors.append(f"tracked operating-system junk: {_relative(path)}")
    return errors


def _facade_path(historical: str) -> Path:
    if historical == "ledger":
        return ROOT / "src" / "ledger" / "__init__.py"
    if historical.startswith("ledger."):
        return ROOT.joinpath("src", *historical.split(".")).with_suffix(".py")
    return ROOT / "src" / f"{historical}.py"


def _canonical_module_path(canonical: str) -> Path:
    base = ROOT.joinpath("src", *canonical.split("."))
    package = base / "__init__.py"
    return package if package.is_file() else base.with_suffix(".py")


def validate_facade_source(source: str, historical: str) -> list[str]:
    """Accept only the exact three-statement compatibility-facade AST."""
    template = (
        f'"""Compatibility facade for the historical `{historical}` module."""\n\n'
        "from wingman.shared.compatibility import expose as _expose\n\n\n"
        f'_expose(__name__, "{historical}")\n'
    )
    try:
        observed = ast.parse(source)
    except SyntaxError as error:
        return [f"facade is not valid Python: {error}"]
    expected = ast.parse(template)
    if ast.dump(observed, include_attributes=False) != ast.dump(
        expected, include_attributes=False
    ):
        return ["facade does not match the permitted thin AST"]
    return []


def validate_compatibility_facades() -> list[str]:
    errors: list[str] = []
    source = str(ROOT / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    from wingman.shared.compatibility import COMPATIBILITY_FACADES

    registered = {facade.historical for facade in COMPATIBILITY_FACADES}
    physical = {path.stem for path in (ROOT / "src").glob("*.py")}
    physical.update(
        "ledger" if path.name == "__init__.py" else f"ledger.{path.stem}"
        for path in (ROOT / "src" / "ledger").glob("*.py")
    )
    for missing in sorted(physical - registered):
        errors.append(f"historical facade is not registered: {missing}")
    for stale in sorted(registered - physical):
        errors.append(f"registered facade is missing: {stale}")
    for facade in COMPATIBILITY_FACADES:
        path = _facade_path(facade.historical)
        if not path.is_file():
            continue
        facade_errors = validate_facade_source(
            path.read_text(encoding="utf-8"), facade.historical
        )
        errors.extend(f"{_relative(path)}: {error}" for error in facade_errors)
        if not _canonical_module_path(facade.canonical).is_file():
            errors.append(
                f"{facade.historical}: canonical target is missing: {facade.canonical}"
            )
        for field in (
            facade.owner,
            facade.reason,
            facade.supported_callers,
            facade.removal_condition,
        ):
            if not field:
                errors.append(f"{facade.historical}: registry metadata is incomplete")
                break
    coverage = ROOT / "tests" / "governance" / "test_compatibility_facades.py"
    if not coverage.is_file():
        errors.append("compatibility facade coverage test is missing")
    return errors


def validate_schemas_and_first_reads() -> list[str]:
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*.schema.json")):
        if ".git" in path.parts:
            continue
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (json.JSONDecodeError, SchemaError) as error:
            errors.append(f"{_relative(path)}: invalid JSON schema: {error}")
    agent_path = ROOT / ".codex" / "agents" / "crew-chief.toml"
    try:
        with agent_path.open("rb") as handle:
            agent = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        errors.append(f"{_relative(agent_path)}: invalid Crew Chief agent: {error}")
    else:
        required_agent = {
            "name": "crew_chief",
            "sandbox_mode": "read-only",
            "approval_policy": "never",
            "model_reasoning_effort": "high",
        }
        for field, expected in required_agent.items():
            if agent.get(field) != expected:
                errors.append(
                    f"{_relative(agent_path)}: {field} must be {expected!r}"
                )
        if "model" in agent:
            errors.append(
                f"{_relative(agent_path)}: model must be inherited, not pinned"
            )
        if not agent.get("description") or not agent.get("developer_instructions"):
            errors.append(
                f"{_relative(agent_path)}: description and instructions are required"
            )
    first_reads = {
        ROOT / "README.md": ("AGENTS.md", "CURRENT_MISSION.md"),
        ROOT / "docs" / "README.md": ("AGENTS.md", "CURRENT_MISSION.md"),
        ROOT / "tools" / "flightline" / "roles" / "development-engineer.md": (
            "first repository read", "AGENTS.md"
        ),
        ROOT / "tools" / "flightline" / "roles" / "independent-auditor.md": (
            "first repository read", "AGENTS.md"
        ),
        agent_path: ("first repository read", "AGENTS.md"),
    }
    for path, needles in first_reads.items():
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if any(needle not in text for needle in needles):
            errors.append(f"{_relative(path)}: first-read instructions are incomplete")
        elif len(needles) == 2 and needles == ("AGENTS.md", "CURRENT_MISSION.md"):
            if text.index(needles[0]) > text.index(needles[1]):
                errors.append(f"{_relative(path)}: AGENTS.md must be read first")
    return errors


def validate() -> list[str]:
    missions = load_missions()
    decisions = load_decisions()
    errors = validate_record_schemas(missions, decisions)
    if not errors:
        errors.extend(validate_metadata(missions, decisions))
    if not errors:
        errors.extend(validate_generated(missions, decisions))
    errors.extend(validate_links_and_documents())
    errors.extend(validate_repository_map())
    errors.extend(validate_archive_documents())
    errors.extend(validate_repository_hygiene())
    errors.extend(validate_foreground_preservation_manifest())
    errors.extend(validate_compatibility_facades())
    errors.extend(validate_schemas_and_first_reads())
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "validate"))
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            generate()
            print("Generated repository governance views.")
            return 0
        errors = validate()
    except (GovernanceError, subprocess.SubprocessError) as error:
        print(f"Governance validation failed:\n{error}")
        return 1
    if errors:
        print("Governance validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Repository governance validation passed.")
    return 0
