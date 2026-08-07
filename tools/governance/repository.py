"""Generate and validate Wingman's canonical repository records."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MISSION_ROOT = ROOT / "docs" / "missions"
DECISION_ROOT = ROOT / "docs" / "decisions"
MISSION_MARKER = "wingman-mission-metadata"
DECISION_MARKER = "wingman-decision-metadata"
MISSION_ID = re.compile(r"^[a-z0-9-]+(?:/[a-z0-9-]+)+$")
DECISION_ID = re.compile(r"^[A-Z]+-[0-9]{3}$")
COMMIT_ID = re.compile(r"^[0-9a-f]{7,40}$")
LIFECYCLES = frozenset({"draft", "active", "completed", "archived"})
DECISION_STATES = frozenset({"proposed", "accepted", "superseded"})


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


def _commit_is_reachable(commit: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


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
    if len(primary) != 1:
        errors.append(
            "exactly one active mission must be portfolio-primary; "
            f"observed {len(primary)}"
        )

    active_workstreams: list[tuple[Record, list[str]]] = []
    for record in missions:
        metadata = record.metadata
        mission_id = metadata["id"]
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
        if metadata["portfolio_primary"] and metadata["lifecycle"] != "active":
            errors.append(f"{mission_id}: only an active mission may be primary")
        if metadata["paused"] and metadata["cancelled"]:
            errors.append(f"{mission_id}: paused and cancelled cannot both be true")
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
                else:
                    active_workstreams.append((record, scopes))
        for commit in [metadata["baseline_commit"], *metadata["implementation_commits"]]:
            if commit is None:
                continue
            if not isinstance(commit, str) or not COMMIT_ID.fullmatch(commit):
                errors.append(f"{mission_id}: invalid commit ID {commit!r}")
            elif metadata["lifecycle"] == "completed" and not _commit_is_reachable(commit):
                errors.append(f"{mission_id}: completed commit not reachable: {commit}")
        for decision_path in metadata["official_decisions"]:
            if not (ROOT / decision_path).is_file():
                errors.append(f"{mission_id}: decision link does not resolve: {decision_path}")

    for index, (left, left_scopes) in enumerate(active_workstreams):
        for right, right_scopes in active_workstreams[index + 1:]:
            for left_scope in left_scopes:
                for right_scope in right_scopes:
                    if _scopes_overlap(left_scope, right_scope):
                        errors.append(
                            "active writable scopes overlap without an override: "
                            f"{left.metadata['id']} and {right.metadata['id']}"
                        )

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
    return errors


def _scopes_overlap(left: str, right: str) -> bool:
    left_path = Path(left)
    right_path = Path(right)
    return left_path == right_path or left_path in right_path.parents or right_path in left_path.parents


def _latest_completed(missions: list[Record]) -> Record:
    candidates = [
        record for record in missions
        if record.metadata["lifecycle"] == "completed"
        and record.metadata["implementation_commits"]
    ]
    order = subprocess.run(
        ["git", "rev-list", "--topo-order", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    positions = {commit: index for index, commit in enumerate(order)}
    return min(
        candidates,
        key=lambda record: min(
            positions.get(commit, len(positions))
            for commit in record.metadata["implementation_commits"]
        ),
    )


def render_current_mission(missions: list[Record]) -> str:
    primary = next(
        record for record in missions
        if record.metadata["lifecycle"] == "active"
        and record.metadata["portfolio_primary"]
    )
    latest = _latest_completed(missions)
    metadata = primary.metadata
    latest_commit = latest.metadata["implementation_commits"][-1]
    lines = [
        "# Current Mission",
        "",
        "> Generated by `python -m tools.governance generate` from authoritative",
        "> records under `docs/missions/`. Do not edit this file directly.",
        "",
        "## Portfolio primary",
        "",
        f"- Mission: **{metadata['id']} — {metadata['title']}**",
        f"- Lifecycle: **{metadata['lifecycle']}**",
        f"- Authorization gate: `{metadata['authorization_gate']}`",
        f"- Official record: [{_relative(primary.path)}]({_relative(primary.path)})",
        f"- Next gate: {metadata['next_gate']}",
        "",
        "## Last completed work",
        "",
        f"- **{latest.metadata['id']} — {latest.metadata['title']}**",
        f"- Commit: `{latest_commit}`",
        f"- Official record: [{_relative(latest.path)}]({_relative(latest.path)})",
        "",
        "## Active workstreams",
        "",
        "| Mission | Role | Branch | Worktree | State | Next gate |",
        "|---|---|---|---|---|---|",
    ]
    for record in sorted(
        (item for item in missions if item.metadata["lifecycle"] == "active"),
        key=lambda item: item.metadata["id"],
    ):
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
        "| Mission ID | Legacy aliases | Lifecycle | Primary | Commit state | Record |",
        "|---|---|---|---|---|---|",
    ]
    for record in sorted(missions, key=lambda item: item.metadata["id"]):
        metadata = record.metadata
        aliases = ", ".join(metadata["legacy_aliases"]) or "—"
        commit_state = (
            f"committed={'yes' if metadata['implementation_commits'] else 'no'}; "
            f"pushed={'yes' if metadata['pushed'] else 'no'}; "
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
    primary = next(
        record for record in missions
        if record.metadata["lifecycle"] == "active"
        and record.metadata["portfolio_primary"]
    )
    latest = _latest_completed(missions)
    return "\n".join([
        "# Mission Control Context",
        "",
        "> Generated from authoritative mission metadata. Refresh the external",
        "> ChatGPT Project mirror from this artifact after repository closeout.",
        "",
        "- Canary: `CANOPY-7C2F-ATLAS`",
        "- Authority: Maverick has final authority; Codex is the repository builder/operator.",
        "- First repository read: `AGENTS.md`",
        f"- Portfolio-primary: `{primary.metadata['id']}` ({primary.metadata['lifecycle']})",
        f"- Authorization gate: `{primary.metadata['authorization_gate']}`",
        f"- Official record: `{_relative(primary.path)}`",
        f"- Last completed: `{latest.metadata['id']}` at `{latest.metadata['implementation_commits'][-1]}`",
        f"- Next gate: {primary.metadata['next_gate']}",
        "- Crew Chief: required future capability; no independent Crew Chief audit has occurred.",
        "",
    ])


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
    errors = validate_metadata(missions, decisions)
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


def validate() -> list[str]:
    missions = load_missions()
    decisions = load_decisions()
    errors = validate_metadata(missions, decisions)
    if not errors:
        errors.extend(validate_generated(missions, decisions))
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
