#!/usr/bin/env python3
"""Deterministic Development Flightline controller.

This module manages development-plane Codex runs. It is deliberately separate
from Wingman OS runtime code and never stages, commits, pushes, merges, or
cleans a worktree.
"""

import argparse
import hashlib
import io
import json
import os
import re
import secrets
import selectors
import shlex
import signal
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


CANARY = "CANOPY-7C2F-ATLAS"
SCHEMA_VERSION = "1.1"
ROLES = {"development-engineer", "independent-auditor"}
SAFE_AUXILIARY_TOOLS = {"update_plan"}
LAUNCHABLE_STATES = {"PREFLIGHTED"}
PREFLIGHT_STATES = {"APPROVED", "PREFLIGHTED"}
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAX_UNTRACKED_EVIDENCE_BYTES = 10 * 1024 * 1024
MAX_AUDITOR_AUTHORIZATION_SECONDS = 24 * 60 * 60
MAX_AUDITOR_SCHEMA_PREFLIGHT_SECONDS = 24 * 60 * 60
AUDITOR_ISSUANCE_CONFIRMATION = "ISSUE_FRESH_INDEPENDENT_AUDITOR"
AUDITOR_ISSUER = "flightline-controller"
AUDITOR_AUTHORIZATION_PARENT = Path("/private/tmp/wingman-flightline-authorizations")
AUDITOR_WORKSPACE_PARENT = Path("/private/tmp/wingman-flightline-audits")
AUDITOR_SCHEMA_PREFLIGHT_PARENT = Path("/private/tmp/wingman-flightline-schema-preflights")
IGNORED_GIT_REF_PREFIXES = ("refs/codex/turn-diffs/",)
PREFLIGHT_COMPARISON_FIELDS = (
    "baseline_commit",
    "branch",
    "upstream",
    "cached_upstream_divergence",
    "status_porcelain_v2",
    "remote_names",
    "metadata",
    "codex_version",
)


class FlightlineError(RuntimeError):
    """A fail-closed Flightline validation or control error."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FlightlineError(message)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlightlineError("cannot read JSON {}: {}".format(path, exc)) from exc
    _require(isinstance(value, dict), "{} must contain a JSON object".format(path))
    return value


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise FlightlineError("cannot hash {}: {}".format(path, exc)) from exc
    return digest.hexdigest()


def _installed_codex_version() -> str:
    result = subprocess.run(
        ["codex", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
    )
    _require(result.returncode == 0, "installed Codex CLI is unavailable")
    version = result.stdout.strip()
    _require(bool(version), "installed Codex CLI version is empty")
    return version


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _absolute_path(value: Any, label: str) -> Path:
    _require(isinstance(value, str) and value, "{} must be a non-empty string".format(label))
    path = Path(value).expanduser()
    _require(path.is_absolute(), "{} must be absolute".format(label))
    return path.resolve(strict=False)


def _string_list(value: Any, label: str, nonempty: bool = True) -> List[str]:
    _require(isinstance(value, list), "{} must be an array".format(label))
    if nonempty:
        _require(bool(value), "{} must not be empty".format(label))
    _require(all(isinstance(item, str) and item for item in value), "{} must contain strings".format(label))
    return list(value)


def _command_prefixes(value: Any) -> List[List[str]]:
    _require(isinstance(value, list) and value, "approved_command_prefixes must be a non-empty array")
    result: List[List[str]] = []
    for index, prefix in enumerate(value):
        _require(isinstance(prefix, list) and prefix, "approved command prefix {} must be a non-empty array".format(index))
        _require(all(isinstance(token, str) and token for token in prefix), "approved command prefix {} contains an invalid token".format(index))
        result.append(list(prefix))
    return result


def _resolve_worktree_entry(worktree: Path, entry: str, label: str) -> Path:
    _require(not Path(entry).is_absolute(), "{} entries must be relative to the worktree".format(label))
    _require(entry not in {".", "./"}, "{} may not grant the entire worktree".format(label))
    resolved = (worktree / entry).resolve(strict=False)
    _require(_is_within(resolved, worktree), "{} entry escapes the worktree: {}".format(label, entry))
    _require(".git" not in resolved.relative_to(worktree).parts, "{} may not include .git".format(label))
    return resolved


def _sha256_value(value: Any, label: str) -> str:
    _require(
        isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None,
        "{} must be a lowercase SHA-256".format(label),
    )
    return value


def _artifact_binding(value: Any, label: str) -> Dict[str, Any]:
    _require(isinstance(value, dict), "{} must be an object".format(label))
    _require(set(value) == {"path", "sha256"}, "{} must contain only path and sha256".format(label))
    return {
        "path": str(_absolute_path(value["path"], "{}.path".format(label))),
        "sha256": _sha256_value(value["sha256"], "{}.sha256".format(label)),
    }


def _auditor_authorization(value: Any) -> Dict[str, Any]:
    label = "controller_authorization"
    _require(isinstance(value, dict), "{} must be an object".format(label))
    required = {
        "issuer",
        "authorization_id",
        "issued_at_epoch_seconds",
        "expires_at_epoch_seconds",
        "use_policy",
        "issuance_record",
        "consumption_record",
    }
    _require(set(value) == required, "{} fields are incomplete or unsupported".format(label))
    _require(value["issuer"] == AUDITOR_ISSUER, "Auditor authorization issuer is invalid")
    _sha256_value(value["authorization_id"], "controller_authorization.authorization_id")
    issued = value["issued_at_epoch_seconds"]
    expires = value["expires_at_epoch_seconds"]
    _require(isinstance(issued, int) and issued > 0, "controller authorization issue time is invalid")
    _require(isinstance(expires, int) and expires > issued, "controller authorization expiry is invalid")
    _require(expires - issued <= MAX_AUDITOR_AUTHORIZATION_SECONDS, "controller authorization lifetime exceeds the maximum")
    _require(value["use_policy"] == "single-use", "Auditor authorization must be single-use")
    normalized = dict(value)
    normalized["issuance_record"] = str(_absolute_path(value["issuance_record"], "controller_authorization.issuance_record"))
    normalized["consumption_record"] = str(_absolute_path(value["consumption_record"], "controller_authorization.consumption_record"))
    _require(
        normalized["issuance_record"] != normalized["consumption_record"],
        "issuance and consumption records must be distinct",
    )
    return normalized


def _frozen_subject(value: Any) -> Dict[str, Any]:
    label = "frozen_subject"
    _require(isinstance(value, dict), "{} must be an object".format(label))
    required = {
        "frozen_manifest",
        "frozen_diff",
        "evidence_package",
        "audit_workspace_manifest",
        "foreground_preflight",
    }
    _require(set(value) == required, "{} fields are incomplete or unsupported".format(label))
    return {key: _artifact_binding(value[key], "{}.{}".format(label, key)) for key in sorted(required)}


def validate_envelope(envelope: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate and normalize a version-1 Flightline authorization envelope."""

    required = {
        "schema_version",
        "mission",
        "role",
        "state",
        "canary",
        "baseline_commit",
        "repository_root",
        "worktree_path",
        "allowed_write_paths",
        "protected_data_paths",
        "credential_paths",
        "approved_command_prefixes",
        "allowed_tools",
        "network_policy",
        "credential_policy",
        "budgets",
        "allowed_temp_paths",
        "acceptance_criteria",
        "explicit_exclusions",
        "stop_conditions",
        "authorities",
        "report_schema",
        "output_root",
        "allow_deletions",
    }
    missing = sorted(required.difference(envelope))
    _require(not missing, "envelope is missing required fields: {}".format(", ".join(missing)))
    optional = {
        "prompt_file",
        "prompt_sha256",
        "model",
        "runtime_paths",
        "controller_authorization",
        "frozen_subject",
    }
    unexpected = sorted(set(envelope).difference(required | optional))
    _require(not unexpected, "envelope contains unsupported fields: {}".format(", ".join(unexpected)))
    _require(envelope["schema_version"] == SCHEMA_VERSION, "unsupported envelope schema version")
    _require(envelope["canary"] == CANARY, "canary mismatch")
    _require(envelope["role"] in ROLES, "unsupported role")
    _require(envelope["state"] in PREFLIGHT_STATES, "unsupported Flightline state")
    _require(isinstance(envelope["baseline_commit"], str) and SHA_PATTERN.fullmatch(envelope["baseline_commit"]) is not None, "baseline_commit must be a full lowercase SHA-1")

    mission = envelope["mission"]
    _require(isinstance(mission, dict), "mission must be an object")
    for key in ("number", "name", "call_sign", "objective"):
        _require(isinstance(mission.get(key), str) and mission[key], "mission.{} is required".format(key))

    repository_root = _absolute_path(envelope["repository_root"], "repository_root")
    worktree_path = _absolute_path(envelope["worktree_path"], "worktree_path")
    output_root = _absolute_path(envelope["output_root"], "output_root")
    _require(repository_root != worktree_path, "the foreground checkout cannot be the role worktree")
    _require(not _is_within(worktree_path, repository_root), "the role worktree must be outside the foreground checkout")
    _require(not _is_within(repository_root, worktree_path), "the foreground checkout must not be nested in the role worktree")
    _require(not _is_within(output_root, repository_root), "evidence output must remain outside the foreground checkout")

    allowed_write_entries = _string_list(envelope["allowed_write_paths"], "allowed_write_paths", nonempty=False)
    allowed_write_paths = [
        _resolve_worktree_entry(worktree_path, entry, "allowed_write_paths")
        for entry in allowed_write_entries
    ]
    if envelope["role"] == "development-engineer":
        _require(bool(allowed_write_paths), "the Engineer requires at least one scoped writable path")
        _require("controller_authorization" not in envelope, "the Engineer cannot receive Auditor authorization")
        _require("frozen_subject" not in envelope, "the Engineer cannot receive an Auditor frozen subject")
        _require("runtime_paths" not in envelope, "the Engineer cannot receive Auditor runtime paths")
    else:
        _require(not allowed_write_paths, "the Auditor may not receive production writable paths")
        _require(envelope["state"] == "PREFLIGHTED", "a controller-issued Auditor envelope must be PREFLIGHTED")
        _require("controller_authorization" in envelope, "the Auditor requires controller-issued authorization")
        _require("frozen_subject" in envelope, "the Auditor requires a frozen subject binding")
        _require("runtime_paths" in envelope, "the Auditor requires a bound read-only runtime")

    protected_data_paths = [
        _absolute_path(value, "protected_data_paths")
        for value in _string_list(envelope["protected_data_paths"], "protected_data_paths")
    ]
    credential_paths = [
        _absolute_path(value, "credential_paths")
        for value in _string_list(envelope["credential_paths"], "credential_paths")
    ]
    allowed_temp_paths = [
        _absolute_path(value, "allowed_temp_paths")
        for value in _string_list(envelope["allowed_temp_paths"], "allowed_temp_paths")
    ]
    _require(any(_is_within(output_root, root) or output_root == root for root in allowed_temp_paths), "output_root must be inside an allowed temporary path")
    _require(all(not _is_within(path, repository_root) for path in allowed_temp_paths), "temporary output paths must be outside the foreground checkout")
    _require(
        all(not _is_within(worktree_path, path) and not _is_within(path, worktree_path) for path in allowed_temp_paths),
        "temporary output paths and the isolated worktree must be disjoint",
    )

    _require(envelope["network_policy"] == "off", "network policy must be off")
    _require(envelope["credential_policy"] == "none-mounted", "credential policy must be none-mounted")
    _require(envelope["allow_deletions"] is False, "Flightline v1 does not authorize deletions")

    authorities = envelope["authorities"]
    _require(isinstance(authorities, dict), "authorities must be an object")
    for action in ("stage", "commit", "push", "merge", "rebase", "tag", "release", "deploy", "destructive"):
        _require(authorities.get(action) is False, "{} authority must be false".format(action))

    budgets = envelope["budgets"]
    _require(isinstance(budgets, dict), "budgets must be an object")
    for field in ("time_seconds", "token_budget", "command_budget", "max_changed_files"):
        _require(isinstance(budgets.get(field), int) and budgets[field] > 0, "budgets.{} must be a positive integer".format(field))

    report_schema = _absolute_path(envelope["report_schema"], "report_schema")
    expected_schema_name = "engineer-report.schema.json" if envelope["role"] == "development-engineer" else "auditor-report.schema.json"
    expected_schema = (Path(__file__).resolve().parent / "schemas" / expected_schema_name).resolve()
    _require(report_schema == expected_schema, "report_schema must be the canonical schema for the selected role")
    _require(report_schema.is_file(), "canonical report schema is missing")
    _command_prefixes(envelope["approved_command_prefixes"])
    allowed_tools = _string_list(envelope["allowed_tools"], "allowed_tools")
    _require(set(allowed_tools).issubset(SAFE_AUXILIARY_TOOLS), "allowed_tools contains an unsupported auxiliary tool")
    _string_list(envelope["acceptance_criteria"], "acceptance_criteria")
    _string_list(envelope["explicit_exclusions"], "explicit_exclusions")
    _string_list(envelope["stop_conditions"], "stop_conditions")
    prompt_present = "prompt_file" in envelope or "prompt_sha256" in envelope
    _require(("prompt_file" in envelope) == ("prompt_sha256" in envelope), "prompt_file and prompt_sha256 must appear together")
    if envelope["role"] == "independent-auditor":
        _require(prompt_present, "the Auditor requires a controller-generated prompt binding")
    prompt_path: Optional[Path] = None
    if prompt_present:
        prompt_path = _absolute_path(envelope["prompt_file"], "prompt_file")
        prompt_hash = envelope["prompt_sha256"]
        _sha256_value(prompt_hash, "prompt_sha256")
        denied_roots = protected_data_paths + credential_paths + allowed_temp_paths + allowed_write_paths
        _require(not any(_is_within(prompt_path, root) or prompt_path == root for root in denied_roots), "prompt_file overlaps protected or mutable scope")
        _require(not _is_within(prompt_path, worktree_path), "prompt_file must be outside the role worktree")

    runtime_paths: List[Path] = []
    controller_authorization: Optional[Dict[str, Any]] = None
    frozen_subject: Optional[Dict[str, Any]] = None
    if envelope["role"] == "independent-auditor":
        assert prompt_path is not None
        runtime_paths = [
            _absolute_path(value, "runtime_paths")
            for value in _string_list(envelope["runtime_paths"], "runtime_paths")
        ]
        expected_runtime = (repository_root / ".venv" / "flightline-py312").resolve(strict=False)
        _require(runtime_paths == [expected_runtime], "the Auditor runtime must be the repository Flightline Python 3.12 environment")
        _require(
            all(not _is_within(path, root) and path != root for path in runtime_paths for root in protected_data_paths + credential_paths),
            "the Auditor runtime overlaps a protected path",
        )
        controller_authorization = _auditor_authorization(envelope["controller_authorization"])
        frozen_subject = _frozen_subject(envelope["frozen_subject"])
        immutable_paths = [Path(item["path"]) for item in frozen_subject.values()]
        immutable_paths.extend(
            [
                Path(controller_authorization["issuance_record"]),
                Path(controller_authorization["consumption_record"]),
                prompt_path,
            ]
        )
        for path in immutable_paths:
            _require(not _is_within(path, worktree_path), "Auditor control and evidence paths must remain outside the audit workspace")
            _require(
                not any(_is_within(path, root) or path == root for root in allowed_temp_paths),
                "Auditor control and evidence paths must remain outside writable audit output",
            )

    normalized = dict(envelope)
    normalized.update(
        repository_root=str(repository_root),
        worktree_path=str(worktree_path),
        output_root=str(output_root),
        report_schema=str(report_schema),
        allowed_write_paths=[str(path) for path in allowed_write_paths],
        protected_data_paths=[str(path) for path in protected_data_paths],
        credential_paths=[str(path) for path in credential_paths],
        allowed_temp_paths=[str(path) for path in allowed_temp_paths],
    )
    if runtime_paths:
        normalized["runtime_paths"] = [str(path) for path in runtime_paths]
    if controller_authorization is not None:
        normalized["controller_authorization"] = controller_authorization
    if frozen_subject is not None:
        normalized["frozen_subject"] = frozen_subject
    return normalized


def _sanitized_environment() -> Dict[str, str]:
    """Return the minimal non-secret environment inherited by an agent run."""

    allowed_names = {
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "LOGNAME",
        "NO_COLOR",
        "PATH",
        "SHELL",
        "TERM",
        "TMPDIR",
        "USER",
    }
    environment = {key: value for key, value in os.environ.items() if key in allowed_names}
    environment["GIT_ASKPASS"] = "/usr/bin/false"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _require_immutable_control_path(path: Path, envelope: Mapping[str, Any], label: str) -> None:
    mutable_roots = [Path(str(value)).resolve(strict=False) for value in envelope["allowed_write_paths"]]
    mutable_roots.extend(Path(str(value)).resolve(strict=False) for value in envelope["allowed_temp_paths"])
    resolved = path.resolve(strict=False)
    _require(not _is_within(resolved, Path(str(envelope["worktree_path"])).resolve(strict=False)), "{} must be outside the role worktree".format(label))
    _require(not any(_is_within(resolved, root) or resolved == root for root in mutable_roots), "{} overlaps role-writable scope".format(label))


def _require_output_path(path: Path, envelope: Mapping[str, Any], label: str) -> Path:
    resolved = path.resolve(strict=False)
    output_root = Path(str(envelope["output_root"])).resolve(strict=False)
    _require(_is_within(resolved, output_root), "{} must be inside output_root".format(label))
    return resolved


def load_envelope(path: Path) -> Dict[str, Any]:
    return validate_envelope(_load_json(path.resolve()))


def _toml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def _profile_id(role: str) -> str:
    return "wingman-engineer" if role == "development-engineer" else "wingman-auditor"


def build_permission_profile(envelope: Mapping[str, Any]) -> Tuple[str, str]:
    """Return the profile id and an inline TOML profile override."""

    profile_id = _profile_id(str(envelope["role"]))
    repository_root = Path(str(envelope["repository_root"]))
    worktree_path = Path(str(envelope["worktree_path"]))
    filesystem: Dict[str, str] = {
        str(repository_root): "deny",
        str(repository_root / ".git"): "read",
        str(worktree_path / ".git"): "read",
    }
    for path in envelope["protected_data_paths"]:
        filesystem[str(path)] = "deny"
    for path in envelope["credential_paths"]:
        filesystem[str(path)] = "deny"
    if envelope["role"] == "development-engineer":
        for path in envelope["allowed_write_paths"]:
            filesystem[str(path)] = "write"
    else:
        for path in envelope.get("runtime_paths", []):
            filesystem[str(path)] = "read"
        for binding in envelope.get("frozen_subject", {}).values():
            filesystem[str(binding["path"])] = "read"
        authorization = envelope.get("controller_authorization", {})
        for key in ("issuance_record", "consumption_record"):
            value = authorization.get(key)
            if value:
                filesystem[str(value)] = "read"
        prompt_file = envelope.get("prompt_file")
        if prompt_file:
            filesystem[str(prompt_file)] = "read"
    for path in envelope["allowed_temp_paths"]:
        filesystem[str(path)] = "write"

    entries = ",".join(
        "{}={}".format(_toml_quote(path), _toml_quote(access))
        for path, access in sorted(filesystem.items())
    )
    override = "permissions.{}={{extends=\":read-only\",filesystem={{{}}}}}".format(profile_id, entries)
    return profile_id, override


def _hook_override(event_name: str, hook_command: str) -> str:
    handler = "{type=\"command\",command=%s,async=false,timeout=5}" % _toml_quote(hook_command)
    return "hooks.{}=[{{hooks=[{}]}}]".format(event_name, handler)


def build_launch_command(envelope: Mapping[str, Any], envelope_path: Path) -> List[str]:
    """Build the exact non-interactive Codex command without executing it."""

    profile_id, profile_override = build_permission_profile(envelope)
    controller_dir = Path(__file__).resolve().parent
    hook_path = controller_dir / "guard.py"
    python_path = Path(sys.executable).resolve()
    hook_command = "{} {}".format(shlex.quote(str(python_path)), shlex.quote(str(hook_path)))
    output_root = Path(str(envelope["output_root"]))
    role = str(envelope["role"])
    last_message = output_root / (role + "-last-message.json")

    command = ["codex", "exec"]
    if role == "independent-auditor":
        command.append("--skip-git-repo-check")
    command.extend([
        "--strict-config",
        "--ephemeral",
        "--ignore-user-config",
        "--json",
        "-C",
        str(envelope["worktree_path"]),
        "-c",
        'approval_policy="never"',
        "-c",
        'web_search="disabled"',
        "-c",
        'apps._default={enabled=false,open_world_enabled=false,destructive_enabled=false}',
        "-c",
        "default_permissions={}".format(_toml_quote(profile_id)),
        "-c",
        profile_override,
        "-c",
        _hook_override("PreToolUse", hook_command),
        "-c",
        _hook_override("PermissionRequest", hook_command),
        "--disable",
        "apps",
        "--disable",
        "browser_use",
        "--disable",
        "computer_use",
        "--disable",
        "image_generation",
        "--disable",
        "multi_agent",
        "--output-schema",
        str(envelope["report_schema"]),
        "-o",
        str(last_message),
    ])
    model = envelope.get("model")
    if model:
        _require(isinstance(model, str), "model must be a string")
        command.extend(["-m", model])
    command.append("-")
    return command


def build_launch_environment(envelope: Mapping[str, Any], envelope_path: Path) -> Dict[str, str]:
    """Build the minimal child environment and bind it to the active envelope."""

    environment = _sanitized_environment()
    environment["WINGMAN_FLIGHTLINE_ENVELOPE"] = str(envelope_path.resolve())
    environment["WINGMAN_FLIGHTLINE_ROLE"] = str(envelope["role"])
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONHASHSEED"] = "0"
    environment["TMPDIR"] = str(Path(str(envelope["output_root"])).resolve())
    if envelope["role"] == "independent-auditor":
        authorization = envelope["controller_authorization"]
        frozen = envelope["frozen_subject"]
        environment["WINGMAN_FLIGHTLINE_AUTHORIZATION_ID"] = str(authorization["authorization_id"])
        environment["WINGMAN_FLIGHTLINE_FROZEN_MANIFEST"] = str(frozen["frozen_manifest"]["path"])
        environment["WINGMAN_FLIGHTLINE_EVIDENCE_PACKAGE"] = str(frozen["evidence_package"]["path"])
        environment["WINGMAN_FLIGHTLINE_AUDIT_OUTPUT"] = str(envelope["output_root"])
        environment["WINGMAN_FLIGHTLINE_PYTHON"] = str(
            Path(str(envelope["runtime_paths"][0])) / "bin" / "python"
        )
    return environment


def _git(repository: Path, args: Sequence[str], check: bool = True) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "-C", str(repository)] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
        check=False,
    )
    if check and result.returncode != 0:
        raise FlightlineError("git {} failed: {}".format(" ".join(args), result.stderr.strip()))
    return result


def _git_bytes(repository: Path, args: Sequence[str]) -> bytes:
    environment = dict(os.environ)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "-C", str(repository)] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        check=False,
    )
    if result.returncode != 0:
        raise FlightlineError(
            "git {} failed: {}".format(" ".join(args), result.stderr.decode("utf-8", errors="replace").strip())
        )
    return result.stdout


def _security_relevant_refs(show_ref_output: str) -> Dict[str, str]:
    refs: Dict[str, str] = {}
    for line in show_ref_output.splitlines():
        object_id, separator, ref_name = line.partition(" ")
        _require(bool(separator) and bool(ref_name), "git show-ref returned malformed output")
        _require(SHA_PATTERN.fullmatch(object_id) is not None, "git show-ref returned an invalid object id")
        _require(ref_name.startswith("refs/"), "git show-ref returned an invalid reference name")
        if any(ref_name.startswith(prefix) for prefix in IGNORED_GIT_REF_PREFIXES):
            continue
        _require(ref_name not in refs, "git show-ref returned a duplicate reference")
        refs[ref_name] = object_id
    return {name: refs[name] for name in sorted(refs)}


def _git_metadata_snapshot(repository: Path) -> Dict[str, Any]:
    git_dir_text = _git(repository, ["rev-parse", "--absolute-git-dir"]).stdout.strip()
    git_dir = Path(git_dir_text).resolve()
    index_text = _git(repository, ["rev-parse", "--git-path", "index"]).stdout.strip()
    index_path = Path(index_text)
    if not index_path.is_absolute():
        index_path = (repository / index_path).resolve()
    refs = _security_relevant_refs(_git(repository, ["show-ref"], check=False).stdout)
    canonical_refs = "".join("{} {}\n".format(object_id, name) for name, object_id in refs.items()).encode("utf-8")
    config_text = _git(repository, ["config", "--local", "--list", "--show-origin"], check=False).stdout.encode("utf-8")
    remotes_text = _git(repository, ["remote"]).stdout.encode("utf-8")
    return {
        "git_dir": str(git_dir),
        "index_path": str(index_path),
        "index_sha256": sha256_file(index_path) if index_path.exists() else None,
        "refs_sha256": _sha256_bytes(canonical_refs),
        "security_relevant_refs": refs,
        "ignored_ref_prefixes": list(IGNORED_GIT_REF_PREFIXES),
        "local_config_sha256": _sha256_bytes(config_text),
        "remote_names_sha256": _sha256_bytes(remotes_text),
        "head": _git(repository, ["rev-parse", "HEAD"]).stdout.strip(),
    }


def collect_preflight(envelope: Mapping[str, Any]) -> Dict[str, Any]:
    _require(envelope["state"] in PREFLIGHT_STATES, "preflight requires APPROVED or PREFLIGHTED state")
    repository = Path(str(envelope["repository_root"]))
    _require(repository.is_dir(), "repository_root does not exist")
    actual_root = Path(_git(repository, ["rev-parse", "--show-toplevel"]).stdout.strip()).resolve()
    _require(actual_root == repository.resolve(), "repository_root is not the Git root")
    head = _git(repository, ["rev-parse", "HEAD"]).stdout.strip()
    _require(head == envelope["baseline_commit"], "HEAD does not match the approved baseline")
    upstream = _git(repository, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], check=False)
    divergence: Optional[List[int]] = None
    if upstream.returncode == 0:
        counts = _git(repository, ["rev-list", "--left-right", "--count", "{}...HEAD".format(upstream.stdout.strip())]).stdout.split()
        divergence = [int(counts[0]), int(counts[1])]
    return {
        "canary": CANARY,
        "role": envelope["role"],
        "mission": envelope["mission"],
        "state": "PREFLIGHTED",
        "baseline_commit": head,
        "branch": _git(repository, ["branch", "--show-current"]).stdout.strip(),
        "upstream": upstream.stdout.strip() if upstream.returncode == 0 else None,
        "cached_upstream_divergence": divergence,
        "status_porcelain_v2": _git(repository, ["status", "--porcelain=v2", "--branch"]).stdout.splitlines(),
        "remote_names": _git(repository, ["remote"]).stdout.splitlines(),
        "metadata": _git_metadata_snapshot(repository),
        "codex_version": _installed_codex_version(),
        "network_state": "off",
        "commit_authority": "NONE",
        "captured_at_epoch_seconds": int(time.time()),
    }


def prepare_worktree(envelope: Mapping[str, Any], confirmation: str) -> Dict[str, Any]:
    """Create one detached isolated worktree at the approved baseline.

    The controller never creates a branch and never removes a worktree. Removal
    remains a separate, explicitly authorized and recoverable operation.
    """

    _require(confirmation == "CREATE_APPROVED_ISOLATED_WORKTREE", "exact worktree confirmation is required")
    _require(envelope["state"] == "APPROVED", "worktree creation requires APPROVED state")
    repository = Path(str(envelope["repository_root"]))
    worktree = Path(str(envelope["worktree_path"]))
    _require(not worktree.exists(), "worktree path already exists")
    preflight = collect_preflight(envelope)
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(repository, ["worktree", "add", "--detach", str(worktree), str(envelope["baseline_commit"])])
    _require(_git(worktree, ["rev-parse", "HEAD"]).stdout.strip() == envelope["baseline_commit"], "created worktree has the wrong baseline")
    result = {
        "canary": CANARY,
        "state": "PREFLIGHTED",
        "baseline_commit": envelope["baseline_commit"],
        "worktree_path": str(worktree),
        "branch_mode": "detached",
        "preflight": preflight,
        "commit_authority": "NONE",
    }
    return result


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(path))


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(value, encoding="utf-8")
    os.replace(str(temporary), str(path))


def _binding(path: Path) -> Dict[str, str]:
    resolved = path.resolve()
    return {"path": str(resolved), "sha256": sha256_file(resolved)}


def _manifest_diff_binding(manifest: Mapping[str, Any]) -> Dict[str, str]:
    if isinstance(manifest.get("diff"), dict):
        value = manifest["diff"]
        path = _absolute_path(value.get("path"), "frozen manifest diff.path")
        expected = _sha256_value(value.get("sha256"), "frozen manifest diff.sha256")
    else:
        path = _absolute_path(manifest.get("diff_path"), "frozen manifest diff_path")
        expected = _sha256_value(manifest.get("diff_sha256"), "frozen manifest diff_sha256")
    _require(path.is_file(), "frozen diff is missing")
    _require(sha256_file(path) == expected, "frozen diff checksum mismatch")
    return {"path": str(path), "sha256": expected}


def _proposal_entry_paths(manifest: Mapping[str, Any], repository: Path) -> List[Path]:
    entries = manifest.get("entries")
    _require(isinstance(entries, list) and entries, "frozen manifest entries are missing")
    result: List[Path] = []
    for index, entry in enumerate(entries):
        _require(isinstance(entry, dict), "frozen manifest entry {} is invalid".format(index))
        value = entry.get("path")
        _require(isinstance(value, str) and value, "frozen manifest entry {} has no path".format(index))
        status = str(entry.get("status", ""))
        _require("D" not in status and status != "deleted", "Auditor snapshots do not accept deleted proposal files")
        path = Path(value)
        if path.is_absolute():
            try:
                path = path.resolve(strict=False).relative_to(repository.resolve())
            except ValueError as exc:
                raise FlightlineError("frozen manifest path is outside the repository: {}".format(value)) from exc
        _require(path.parts and ".." not in path.parts and ".git" not in path.parts, "unsafe frozen manifest path: {}".format(value))
        result.append(path)
    _require(len(result) == len(set(result)), "frozen manifest contains duplicate paths")
    return sorted(result, key=lambda item: item.as_posix())


def _relative_denied_roots(envelope: Mapping[str, Any]) -> List[Path]:
    repository = Path(str(envelope["repository_root"])).resolve()
    result: List[Path] = []
    for value in list(envelope["protected_data_paths"]) + list(envelope["credential_paths"]):
        path = Path(str(value)).resolve(strict=False)
        try:
            relative = path.relative_to(repository)
        except ValueError:
            continue
        if relative.parts:
            result.append(relative)
    return sorted(set(result), key=lambda item: item.as_posix())


def _path_is_denied(relative: Path, denied_roots: Sequence[Path]) -> bool:
    return any(relative == root or _is_within(relative, root) for root in denied_roots)


def _workspace_tree(workspace: Path) -> Dict[str, Any]:
    digest = hashlib.sha256()
    file_count = 0
    total_bytes = 0
    for path in sorted(workspace.rglob("*"), key=lambda item: item.relative_to(workspace).as_posix()):
        relative = path.relative_to(workspace)
        _require(not path.is_symlink(), "audit workspace contains a symbolic link: {}".format(relative))
        if path.is_dir():
            continue
        _require(path.is_file(), "audit workspace contains an unsupported file type: {}".format(relative))
        file_hash = sha256_file(path)
        size = path.stat().st_size
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
        file_count += 1
        total_bytes += size
    return {"tree_sha256": digest.hexdigest(), "file_count": file_count, "total_bytes": total_bytes}


def _materialize_audit_workspace(
    source_envelope: Mapping[str, Any],
    manifest: Mapping[str, Any],
    diff_binding: Mapping[str, str],
    workspace: Path,
) -> Dict[str, Any]:
    repository = Path(str(source_envelope["repository_root"])).resolve()
    denied_roots = _relative_denied_roots(source_envelope)
    proposal_paths = _proposal_entry_paths(manifest, repository)
    for path in proposal_paths:
        _require(not _path_is_denied(path, denied_roots), "frozen proposal overlaps protected data: {}".format(path))

    _require(not workspace.exists(), "audit workspace already exists")
    workspace.mkdir(parents=True)
    archive_bytes = _git_bytes(repository, ["archive", "--format=tar", str(source_envelope["baseline_commit"])])
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
        for member in archive:
            relative = Path(member.name)
            _require(
                not relative.is_absolute() and relative.parts and ".." not in relative.parts and ".git" not in relative.parts,
                "unsafe path in baseline archive: {}".format(member.name),
            )
            if _path_is_denied(relative, denied_roots):
                continue
            target = (workspace / relative).resolve(strict=False)
            _require(_is_within(target, workspace), "baseline archive path escapes the audit workspace")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            _require(member.isfile(), "baseline archive contains an unsupported non-regular entry: {}".format(member.name))
            source = archive.extractfile(member)
            _require(source is not None, "cannot read baseline archive member: {}".format(member.name))
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                handle.write(source.read())
            target.chmod(member.mode & 0o777)

    apply_base = ["git", "-C", str(workspace), "apply", "--no-index", "--binary", "--whitespace=error"]
    check = subprocess.run(
        apply_base + ["--check", str(diff_binding["path"])],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    _require(check.returncode == 0, "frozen diff does not apply to the audit snapshot: {}".format(check.stderr.strip()))
    applied = subprocess.run(
        apply_base + [str(diff_binding["path"])],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    _require(applied.returncode == 0, "cannot materialize frozen diff: {}".format(applied.stderr.strip()))

    proposal_inventory: List[Dict[str, Any]] = []
    for relative in proposal_paths:
        path = workspace / relative
        _require(path.is_file() and not path.is_symlink(), "materialized proposal file is missing: {}".format(relative))
        proposal_inventory.append(
            {"path": relative.as_posix(), "sha256": sha256_file(path), "size": path.stat().st_size}
        )
    for entry in manifest["entries"]:
        expected = entry.get("sha256")
        if expected is None:
            continue
        value = Path(str(entry["path"]))
        if value.is_absolute():
            value = value.resolve(strict=False).relative_to(repository)
        actual = next(item for item in proposal_inventory if item["path"] == value.as_posix())
        _require(actual["sha256"] == expected, "materialized proposal checksum mismatch: {}".format(value))

    for root in denied_roots:
        _require(not (workspace / root).exists(), "protected repository data was copied into the audit workspace")
    tree = _workspace_tree(workspace)
    return {
        "canary": CANARY,
        "state": "PREFLIGHTED",
        "baseline_commit": source_envelope["baseline_commit"],
        "workspace_path": str(workspace),
        "frozen_diff_sha256": diff_binding["sha256"],
        "excluded_repository_paths": [path.as_posix() for path in denied_roots],
        "proposal_entries": proposal_inventory,
        **tree,
    }


def _auditor_command_prefixes(source_envelope: Mapping[str, Any], runtime_python: Path) -> List[List[str]]:
    prefixes: List[List[str]] = []
    for prefix in source_envelope["approved_command_prefixes"]:
        updated = list(prefix)
        if updated and Path(updated[0]).name.startswith("python") and ".venv" in updated[0]:
            updated[0] = str(runtime_python)
        prefixes.append(updated)
    return prefixes


def _auditor_prompt_text(
    source_envelope: Mapping[str, Any],
    manifest_binding: Mapping[str, str],
    diff_binding: Mapping[str, str],
    package_binding: Mapping[str, str],
    workspace_manifest_binding: Mapping[str, str],
) -> str:
    return """# Controller-authorized Independent Auditor task

Independently audit the frozen Development Flightline proposal identified by
the exact controller bindings below. This is a fresh development-plane Auditor
session, not the Engineer session and not Crew Chief. Mission 028 remains
unauthorized.

Do not modify source or repository state. Write only the schema-conforming
Auditor report and declared audit outputs. First verify the active Flightline
environment variables, controller authorization, hashes, baseline, and sandbox
denials. Record the authorization ID and every required `activation_proof`
field in the Auditor report. If any binding or denial cannot be proven, return
BLOCKED.

Frozen manifest: {manifest_path}
Frozen manifest SHA-256: {manifest_hash}
Frozen diff: {diff_path}
Frozen diff SHA-256: {diff_hash}
Evidence package: {package_path}
Evidence package SHA-256: {package_hash}
Audit workspace manifest: {workspace_path}
Audit workspace manifest SHA-256: {workspace_hash}

Acceptance criteria:
{criteria}

Explicit exclusions:
{exclusions}
""".format(
        manifest_path=manifest_binding["path"],
        manifest_hash=manifest_binding["sha256"],
        diff_path=diff_binding["path"],
        diff_hash=diff_binding["sha256"],
        package_path=package_binding["path"],
        package_hash=package_binding["sha256"],
        workspace_path=workspace_manifest_binding["path"],
        workspace_hash=workspace_manifest_binding["sha256"],
        criteria="\n".join("- " + value for value in source_envelope["acceptance_criteria"]),
        exclusions="\n".join("- " + value for value in source_envelope["explicit_exclusions"]),
    )


def _schema_preflight_event_summary(path: Path) -> Dict[str, Any]:
    thread_ids: List[str] = []
    turn_completed = 0
    turn_failed = 0
    invalid_jsonl_lines = 0
    command_count = 0
    tool_event_count = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise FlightlineError("cannot read schema-preflight event log {}: {}".format(path, exc)) from exc
    for line in lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            invalid_jsonl_lines += 1
            continue
        if not isinstance(payload, dict):
            continue
        event_type = str(payload.get("type", ""))
        if event_type == "thread.started" and isinstance(payload.get("thread_id"), str):
            thread_ids.append(payload["thread_id"])
        elif event_type == "turn.completed":
            turn_completed += 1
        elif event_type == "turn.failed":
            turn_failed += 1
        observed_commands, _ = _event_counts(payload)
        command_count += observed_commands
        item = payload.get("item")
        item_type = str(item.get("type", "")) if isinstance(item, dict) else ""
        kind = "{} {}".format(event_type, item_type).lower()
        if any(
            marker in kind
            for marker in (
                "command_execution",
                "computer_use",
                "image_generation",
                "mcp_tool",
                "tool_call",
                "web_search",
            )
        ):
            tool_event_count += 1
    return {
        "thread_ids": thread_ids,
        "turn_completed": turn_completed,
        "turn_failed": turn_failed,
        "invalid_jsonl_lines": invalid_jsonl_lines,
        "command_count": command_count,
        "tool_event_count": tool_event_count,
    }


def _auditor_schema_preflight_command(
    source_envelope: Mapping[str, Any], output_root: Path
) -> List[str]:
    repository = Path(str(source_envelope["repository_root"])).resolve()
    profile_id = "wingman-auditor-schema-preflight"
    filesystem: Dict[str, str] = {str(repository): "deny"}
    for value in list(source_envelope["protected_data_paths"]) + list(source_envelope["credential_paths"]):
        filesystem[str(Path(str(value)).resolve(strict=False))] = "deny"
    home = os.environ.get("HOME")
    if home:
        filesystem[str((Path(home).resolve(strict=False) / ".codex"))] = "deny"
    entries = ",".join(
        "{}={}".format(_toml_quote(path), _toml_quote(access))
        for path, access in sorted(filesystem.items())
    )
    profile_override = "permissions.{}={{extends=\":read-only\",filesystem={{{}}}}}".format(
        profile_id, entries
    )
    controller_dir = Path(__file__).resolve().parent
    hook_path = controller_dir / "guard.py"
    hook_command = "{} {}".format(
        shlex.quote(str(Path(sys.executable).resolve())), shlex.quote(str(hook_path))
    )
    schema_path = controller_dir / "schemas" / "auditor-report.schema.json"
    command = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--strict-config",
        "--ephemeral",
        "--ignore-user-config",
        "--json",
        "-C",
        str(output_root),
        "-c",
        'approval_policy="never"',
        "-c",
        'web_search="disabled"',
        "-c",
        'apps._default={enabled=false,open_world_enabled=false,destructive_enabled=false}',
        "-c",
        "default_permissions={}".format(_toml_quote(profile_id)),
        "-c",
        profile_override,
        "-c",
        _hook_override("PreToolUse", hook_command),
        "-c",
        _hook_override("PermissionRequest", hook_command),
        "--disable",
        "apps",
        "--disable",
        "browser_use",
        "--disable",
        "computer_use",
        "--disable",
        "image_generation",
        "--disable",
        "multi_agent",
        "--output-schema",
        str(schema_path),
        "-o",
        str(output_root / "schema-fixture-last-message.json"),
    ]
    model = source_envelope.get("model")
    if model:
        _require(isinstance(model, str), "model must be a string")
        command.extend(["-m", model])
    command.append("-")
    return command


def run_auditor_schema_preflight(
    source_envelope: Mapping[str, Any], output_root: Path
) -> Dict[str, Any]:
    """Obtain model acceptance of the Auditor schema without issuing authorization."""

    _require(
        not os.environ.get("WINGMAN_FLIGHTLINE_ROLE") and not os.environ.get("WINGMAN_FLIGHTLINE_ENVELOPE"),
        "a Flightline role session cannot run the Auditor schema preflight",
    )
    _require(source_envelope["role"] == "development-engineer", "schema preflight requires an Engineer envelope")
    repository = Path(str(source_envelope["repository_root"])).resolve()
    runtime = (repository / ".venv" / "flightline-py312").resolve(strict=False)
    _require(Path(sys.prefix).resolve() == runtime, "Auditor schema preflight must use .venv/flightline-py312")
    codex_version = _installed_codex_version()
    output_root = output_root.resolve(strict=False)
    _require(
        _is_within(output_root, AUDITOR_SCHEMA_PREFLIGHT_PARENT.resolve(strict=False)),
        "Auditor schema preflight must be under the controller schema-preflight root",
    )
    _require(output_root != Path(output_root.anchor), "schema-preflight output cannot be a filesystem root")
    _require(not _is_within(output_root, repository), "schema-preflight output must be outside the repository")
    _require(not output_root.exists(), "schema-preflight output already exists")
    for mutable in list(source_envelope["allowed_write_paths"]) + list(source_envelope["allowed_temp_paths"]):
        mutable_root = Path(str(mutable)).resolve(strict=False)
        _require(
            not _is_within(output_root, mutable_root) and not _is_within(mutable_root, output_root),
            "schema-preflight output overlaps role-writable scope",
        )
    output_root.mkdir(parents=True, mode=0o700)
    output_root.chmod(0o700)

    schema_path = Path(__file__).resolve().parent / "schemas" / "auditor-report.schema.json"
    schema_binding = _binding(schema_path)
    event_path = output_root / "schema-preflight-events.jsonl"
    stderr_path = output_root / "schema-preflight-stderr.log"
    last_message_path = output_root / "schema-fixture-last-message.json"
    record_path = output_root / "schema-preflight.json"
    command = _auditor_schema_preflight_command(source_envelope, output_root)
    started_at = int(time.time())
    prompt = """Validate model-service acceptance of the supplied JSON output schema.
Do not call tools and do not inspect any files. Return one minimal JSON fixture
that conforms to the schema. This is only a non-authorized compatibility probe:
it is not an audit, is not evidence of Flightline activation, and grants no
authorization. Use baseline_commit {baseline} and authorization_id {authorization}.
Use empty arrays where permitted and label free-text values as schema compatibility
fixtures.
""".format(
        baseline=source_envelope["baseline_commit"], authorization="0" * 64
    )
    exit_code: Optional[int] = None
    timed_out = False
    launch_error: Optional[str] = None
    with event_path.open("w", encoding="utf-8") as event_log, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_log:
        try:
            result = subprocess.run(
                command,
                input=prompt,
                stdout=event_log,
                stderr=stderr_log,
                text=True,
                env=_sanitized_environment(),
                cwd=str(output_root),
                timeout=min(int(source_envelope["budgets"]["time_seconds"]), 300),
                check=False,
            )
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            stderr_log.write("schema compatibility preflight timed out\n")
        except OSError as exc:
            launch_error = "{}: {}".format(type(exc).__name__, exc)
            stderr_log.write("schema compatibility preflight child was not created: {}\n".format(exc))

    event_summary = _schema_preflight_event_summary(event_path)
    last_message_is_json_object = False
    if last_message_path.is_file():
        try:
            last_message_is_json_object = isinstance(
                json.loads(last_message_path.read_text(encoding="utf-8")), dict
            )
        except (OSError, json.JSONDecodeError):
            last_message_is_json_object = False
    accepted = (
        exit_code == 0
        and not timed_out
        and launch_error is None
        and len(event_summary["thread_ids"]) == 1
        and event_summary["turn_completed"] == 1
        and event_summary["turn_failed"] == 0
        and event_summary["invalid_jsonl_lines"] == 0
        and event_summary["command_count"] == 0
        and event_summary["tool_event_count"] == 0
        and last_message_is_json_object
    )
    completed_at = int(time.time())
    artifacts: Dict[str, Dict[str, str]] = {
        "events": _binding(event_path),
        "stderr": _binding(stderr_path),
    }
    if last_message_path.is_file():
        artifacts["last_message"] = _binding(last_message_path)
    record: Dict[str, Any] = {
        "canary": CANARY,
        "issuer": AUDITOR_ISSUER,
        "role": "auditor-schema-compatibility-preflight",
        "state": "MODEL_ACCEPTED" if accepted else "REJECTED",
        "authorization_issued": False,
        "authorization_consumed": False,
        "baseline_commit": source_envelope["baseline_commit"],
        "requested_model": source_envelope.get("model"),
        "codex_version": codex_version,
        "schema": schema_binding,
        "started_at_epoch_seconds": started_at,
        "completed_at_epoch_seconds": completed_at,
        "expires_at_epoch_seconds": started_at + MAX_AUDITOR_SCHEMA_PREFLIGHT_SECONDS,
        "acceptance": {
            "exit_code": exit_code,
            "timed_out": timed_out,
            "launch_error": launch_error,
            "last_message_is_json_object": last_message_is_json_object,
            **event_summary,
        },
        "artifacts": artifacts,
        "redacted_argv": _redact_command(command),
    }
    _atomic_json(record_path, record)
    if not accepted:
        raise FlightlineError(
            "Auditor schema compatibility preflight failed; no authorization was issued (record: {})".format(
                record_path
            )
        )
    return record


def _verify_auditor_schema_preflight_record(
    expected_baseline: str, requested_model: Any, path: Path
) -> Dict[str, Any]:
    resolved = path.resolve()
    _require(
        _is_within(resolved, AUDITOR_SCHEMA_PREFLIGHT_PARENT.resolve(strict=False)),
        "schema-preflight record is outside the controller schema-preflight root",
    )
    record = _load_json(resolved)
    _require(record.get("canary") == CANARY, "schema-preflight canary mismatch")
    _require(record.get("issuer") == AUDITOR_ISSUER, "schema-preflight issuer mismatch")
    _require(
        record.get("role") == "auditor-schema-compatibility-preflight",
        "schema-preflight role mismatch",
    )
    _require(record.get("state") == "MODEL_ACCEPTED", "Auditor schema was not accepted by the model service")
    _require(record.get("authorization_issued") is False, "schema preflight must not issue authorization")
    _require(record.get("authorization_consumed") is False, "schema preflight must not consume authorization")
    _require(record.get("baseline_commit") == expected_baseline, "schema-preflight baseline mismatch")
    _require(record.get("requested_model") == requested_model, "schema-preflight model mismatch")
    _require(record.get("codex_version") == _installed_codex_version(), "Codex version changed after schema preflight")
    started = record.get("started_at_epoch_seconds")
    expires = record.get("expires_at_epoch_seconds")
    _require(isinstance(started, int) and started > 0, "schema-preflight start time is invalid")
    _require(
        isinstance(expires, int) and started < expires <= started + MAX_AUDITOR_SCHEMA_PREFLIGHT_SECONDS,
        "schema-preflight expiry is invalid",
    )
    _require(int(time.time()) <= expires, "Auditor schema preflight expired")
    schema = _artifact_binding(record.get("schema"), "schema-preflight schema")
    canonical_schema = Path(__file__).resolve().parent / "schemas" / "auditor-report.schema.json"
    _require(Path(schema["path"]).resolve() == canonical_schema.resolve(), "schema-preflight used a non-canonical schema")
    _require(sha256_file(canonical_schema) == schema["sha256"], "Auditor report schema changed after preflight")
    artifacts = record.get("artifacts")
    _require(isinstance(artifacts, dict), "schema-preflight artifacts are incomplete")
    _require(set(artifacts) == {"events", "stderr", "last_message"}, "schema-preflight artifacts are incomplete")
    normalized_artifacts = {
        label: _artifact_binding(binding, "schema-preflight artifacts.{}".format(label))
        for label, binding in artifacts.items()
    }
    for label, binding in normalized_artifacts.items():
        artifact_path = Path(binding["path"])
        _require(artifact_path.is_file(), "schema-preflight {} artifact is missing".format(label))
        _require(sha256_file(artifact_path) == binding["sha256"], "schema-preflight {} checksum mismatch".format(label))
    event_summary = _schema_preflight_event_summary(Path(normalized_artifacts["events"]["path"]))
    acceptance = record.get("acceptance")
    _require(isinstance(acceptance, dict), "schema-preflight acceptance evidence is missing")
    for key, value in event_summary.items():
        _require(acceptance.get(key) == value, "schema-preflight event evidence mismatch: {}".format(key))
    _require(acceptance.get("exit_code") == 0, "schema-preflight model call did not complete")
    _require(acceptance.get("timed_out") is False, "schema-preflight model call timed out")
    _require(acceptance.get("launch_error") is None, "schema-preflight child was not created")
    _require(acceptance.get("last_message_is_json_object") is True, "schema-preflight output is not JSON")
    _require(len(event_summary["thread_ids"]) == 1, "schema-preflight startup handshake is invalid")
    _require(event_summary["turn_completed"] == 1, "schema-preflight turn did not complete exactly once")
    _require(event_summary["turn_failed"] == 0, "schema-preflight turn failed")
    _require(event_summary["invalid_jsonl_lines"] == 0, "schema-preflight event log is invalid")
    _require(event_summary["command_count"] == 0, "schema-preflight invoked a command")
    _require(event_summary["tool_event_count"] == 0, "schema-preflight invoked a tool")
    try:
        fixture = json.loads(Path(normalized_artifacts["last_message"]["path"]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlightlineError("cannot read schema-preflight fixture: {}".format(exc)) from exc
    _require(isinstance(fixture, dict), "schema-preflight fixture must be a JSON object")
    return record


def verify_auditor_schema_preflight(
    source_envelope: Mapping[str, Any], path: Path
) -> Dict[str, Any]:
    _require(source_envelope["role"] == "development-engineer", "schema preflight requires an Engineer envelope")
    return _verify_auditor_schema_preflight_record(
        str(source_envelope["baseline_commit"]), source_envelope.get("model"), path
    )


def issue_auditor_envelope(
    source_envelope: Mapping[str, Any],
    schema_preflight_path: Path,
    frozen_manifest_path: Path,
    evidence_package_path: Path,
    audit_workspace: Path,
    audit_output: Path,
    authorization_root: Path,
    expires_in_seconds: int,
    confirmation: str,
) -> Dict[str, Any]:
    """Issue a sealed, expiring, single-use Independent Auditor envelope."""

    _require(
        not os.environ.get("WINGMAN_FLIGHTLINE_ROLE") and not os.environ.get("WINGMAN_FLIGHTLINE_ENVELOPE"),
        "a Flightline role session cannot issue Auditor authorization",
    )
    _require(confirmation == AUDITOR_ISSUANCE_CONFIRMATION, "exact Auditor issuance confirmation is required")
    _require(source_envelope["role"] == "development-engineer", "Auditor authorization must derive from an Engineer envelope")
    _require(
        isinstance(expires_in_seconds, int) and 0 < expires_in_seconds <= MAX_AUDITOR_AUTHORIZATION_SECONDS,
        "Auditor authorization lifetime is invalid",
    )
    repository = Path(str(source_envelope["repository_root"])).resolve()
    runtime = (repository / ".venv" / "flightline-py312").resolve(strict=False)
    runtime_python = runtime / "bin" / "python"
    _require(Path(sys.prefix).resolve() == runtime, "Auditor issuance must use .venv/flightline-py312")
    _require(runtime_python.is_file(), "Flightline Python 3.12 runtime is missing")
    schema_preflight_path = schema_preflight_path.resolve()
    schema_preflight = verify_auditor_schema_preflight(source_envelope, schema_preflight_path)

    audit_workspace = audit_workspace.resolve(strict=False)
    audit_output = audit_output.resolve(strict=False)
    authorization_root = authorization_root.resolve(strict=False)
    for label, path in (
        ("audit workspace", audit_workspace),
        ("audit output", audit_output),
        ("authorization root", authorization_root),
    ):
        _require(path != Path(path.anchor), "{} cannot be a filesystem root".format(label))
        _require(not _is_within(path, repository), "{} must be outside the foreground repository".format(label))
    _require(
        _is_within(audit_workspace, AUDITOR_WORKSPACE_PARENT)
        and _is_within(audit_output, AUDITOR_WORKSPACE_PARENT),
        "Auditor workspace and output must be under the controller audit root",
    )
    _require(
        _is_within(authorization_root, AUDITOR_AUTHORIZATION_PARENT),
        "Auditor authorization must be under the controller authorization root",
    )
    _require(not audit_workspace.exists(), "audit workspace already exists")
    _require(not audit_output.exists(), "audit output already exists")
    _require(not authorization_root.exists(), "authorization root already exists")
    roots = [audit_workspace, audit_output, authorization_root]
    for index, root in enumerate(roots):
        _require(
            all(index == other or (not _is_within(root, value) and not _is_within(value, root)) for other, value in enumerate(roots)),
            "Auditor workspace, output, and authorization roots must be disjoint",
        )
    for mutable in list(source_envelope["allowed_write_paths"]) + list(source_envelope["allowed_temp_paths"]):
        mutable_root = Path(str(mutable)).resolve(strict=False)
        _require(
            not _is_within(authorization_root, mutable_root) and not _is_within(mutable_root, authorization_root),
            "controller authorization root overlaps Engineer-writable scope",
        )

    manifest_path = frozen_manifest_path.resolve()
    package_path = evidence_package_path.resolve()
    manifest = _load_json(manifest_path)
    _require(manifest.get("baseline_commit") == source_envelope["baseline_commit"], "frozen manifest baseline mismatch")
    _require(
        manifest.get("state") in {"READY_FOR_AUDIT", "READY_FOR_FRESH_INDEPENDENT_AUDITOR"},
        "frozen manifest is not ready for audit",
    )
    manifest_binding = _binding(manifest_path)
    diff_binding = _manifest_diff_binding(manifest)
    package = _load_json(package_path)
    package_manifest = package.get("frozen_manifest")
    _require(isinstance(package_manifest, dict), "evidence package does not bind the frozen manifest")
    _require(
        Path(str(package_manifest.get("path"))).resolve() == manifest_path
        and package_manifest.get("sha256") == manifest_binding["sha256"],
        "evidence package frozen-manifest binding mismatch",
    )
    package_binding = _binding(package_path)

    foreground_preflight = collect_preflight(source_envelope)
    authorization_root.mkdir(parents=True)
    preflight_path = authorization_root / "foreground-preflight.json"
    _atomic_json(preflight_path, foreground_preflight)
    preflight_binding = _binding(preflight_path)

    workspace_manifest = _materialize_audit_workspace(source_envelope, manifest, diff_binding, audit_workspace)
    workspace_manifest_path = authorization_root / "audit-workspace-manifest.json"
    _atomic_json(workspace_manifest_path, workspace_manifest)
    workspace_manifest_binding = _binding(workspace_manifest_path)

    issued_at = int(time.time())
    expires_at = issued_at + expires_in_seconds
    _require(
        expires_at <= schema_preflight["expires_at_epoch_seconds"],
        "Auditor authorization cannot outlive its schema-compatibility preflight",
    )
    authorization_id = _sha256_bytes(
        secrets.token_bytes(32)
        + manifest_binding["sha256"].encode("ascii")
        + package_binding["sha256"].encode("ascii")
        + str(issued_at).encode("ascii")
    )
    envelope_path = authorization_root / "auditor-envelope.json"
    prompt_path = authorization_root / "auditor-prompt.md"
    issuance_record_path = authorization_root / "controller-issuance.json"
    consumption_record_path = authorization_root / "controller-consumed.json"
    prompt = _auditor_prompt_text(
        source_envelope,
        manifest_binding,
        diff_binding,
        package_binding,
        workspace_manifest_binding,
    )
    _atomic_text(prompt_path, prompt)

    auditor_envelope: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "mission": dict(source_envelope["mission"]),
        "role": "independent-auditor",
        "state": "PREFLIGHTED",
        "canary": CANARY,
        "baseline_commit": source_envelope["baseline_commit"],
        "repository_root": str(repository),
        "worktree_path": str(audit_workspace),
        "allowed_write_paths": [],
        "protected_data_paths": list(source_envelope["protected_data_paths"]),
        "credential_paths": list(source_envelope["credential_paths"]),
        "approved_command_prefixes": _auditor_command_prefixes(source_envelope, runtime_python),
        "allowed_tools": list(source_envelope["allowed_tools"]),
        "network_policy": "off",
        "credential_policy": "none-mounted",
        "budgets": dict(source_envelope["budgets"]),
        "allowed_temp_paths": [str(audit_output)],
        "acceptance_criteria": list(source_envelope["acceptance_criteria"]),
        "explicit_exclusions": list(source_envelope["explicit_exclusions"]),
        "stop_conditions": list(source_envelope["stop_conditions"]),
        "authorities": dict(source_envelope["authorities"]),
        "report_schema": str(Path(__file__).resolve().parent / "schemas" / "auditor-report.schema.json"),
        "output_root": str(audit_output),
        "allow_deletions": False,
        "prompt_file": str(prompt_path),
        "prompt_sha256": sha256_file(prompt_path),
        "runtime_paths": [str(runtime)],
        "controller_authorization": {
            "issuer": AUDITOR_ISSUER,
            "authorization_id": authorization_id,
            "issued_at_epoch_seconds": issued_at,
            "expires_at_epoch_seconds": expires_at,
            "use_policy": "single-use",
            "issuance_record": str(issuance_record_path),
            "consumption_record": str(consumption_record_path),
        },
        "frozen_subject": {
            "frozen_manifest": manifest_binding,
            "frozen_diff": diff_binding,
            "evidence_package": package_binding,
            "audit_workspace_manifest": workspace_manifest_binding,
            "foreground_preflight": preflight_binding,
        },
    }
    if "model" in source_envelope:
        auditor_envelope["model"] = source_envelope["model"]
    validated = validate_envelope(auditor_envelope)
    _atomic_json(envelope_path, validated)
    envelope_hash = sha256_file(envelope_path)
    issuance_record = {
        "canary": CANARY,
        "issuer": AUDITOR_ISSUER,
        "state": "ISSUED",
        "role": "independent-auditor",
        "authorization_id": authorization_id,
        "envelope_path": str(envelope_path),
        "envelope_sha256": envelope_hash,
        "issued_at_epoch_seconds": issued_at,
        "expires_at_epoch_seconds": expires_at,
        "use_policy": "single-use",
        "consumption_record": str(consumption_record_path),
        "frozen_manifest_sha256": manifest_binding["sha256"],
        "evidence_package_sha256": package_binding["sha256"],
        "audit_workspace_tree_sha256": workspace_manifest["tree_sha256"],
        "schema_preflight": _binding(schema_preflight_path),
        "auditor_report_schema": _binding(Path(validated["report_schema"])),
    }
    _atomic_json(issuance_record_path, issuance_record)
    return {
        "canary": CANARY,
        "status": "ISSUED",
        "role": "independent-auditor",
        "state": "PREFLIGHTED",
        "authorization_id": authorization_id,
        "expires_at_epoch_seconds": expires_at,
        "single_use": True,
        "envelope": {"path": str(envelope_path), "sha256": envelope_hash},
        "issuance_record": _binding(issuance_record_path),
        "schema_preflight": _binding(schema_preflight_path),
        "audit_workspace": str(audit_workspace),
        "audit_output": str(audit_output),
    }


def _verify_workspace_binding(envelope: Mapping[str, Any]) -> None:
    binding = envelope["frozen_subject"]["audit_workspace_manifest"]
    manifest = _load_json(Path(str(binding["path"])))
    workspace = Path(str(envelope["worktree_path"])).resolve()
    _require(manifest.get("workspace_path") == str(workspace), "audit workspace path binding mismatch")
    _require(manifest.get("baseline_commit") == envelope["baseline_commit"], "audit workspace baseline binding mismatch")
    current = _workspace_tree(workspace)
    for key in ("tree_sha256", "file_count", "total_bytes"):
        _require(current[key] == manifest.get(key), "audit workspace changed after controller issuance")


def verify_controller_authorization(
    envelope: Mapping[str, Any], envelope_path: Path, require_unused: bool = True
) -> Dict[str, Any]:
    _require(envelope["role"] == "independent-auditor", "controller authorization applies only to the Auditor")
    authorization = envelope["controller_authorization"]
    record_path = Path(str(authorization["issuance_record"]))
    _require(record_path.is_file(), "controller issuance record is missing")
    record = _load_json(record_path)
    _require(record.get("issuer") == AUDITOR_ISSUER, "controller issuance record has the wrong issuer")
    _require(record.get("state") == "ISSUED", "controller issuance record is not active")
    _require(record.get("role") == "independent-auditor", "controller issuance record has the wrong role")
    _require(record.get("authorization_id") == authorization["authorization_id"], "authorization id mismatch")
    _require(Path(str(record.get("envelope_path"))).resolve() == envelope_path.resolve(), "issued envelope path mismatch")
    _require(record.get("envelope_sha256") == sha256_file(envelope_path), "issued envelope checksum mismatch")
    _require(record.get("issued_at_epoch_seconds") == authorization["issued_at_epoch_seconds"], "authorization issue time mismatch")
    _require(record.get("expires_at_epoch_seconds") == authorization["expires_at_epoch_seconds"], "authorization expiry mismatch")
    _require(int(time.time()) <= authorization["expires_at_epoch_seconds"], "Auditor authorization expired")
    schema_preflight_binding = _artifact_binding(
        record.get("schema_preflight"), "controller issuance schema_preflight"
    )
    schema_preflight_path = Path(schema_preflight_binding["path"])
    _require(schema_preflight_path.is_file(), "controller-bound schema preflight is missing")
    _require(
        sha256_file(schema_preflight_path) == schema_preflight_binding["sha256"],
        "controller-bound schema preflight checksum mismatch",
    )
    _verify_auditor_schema_preflight_record(
        str(envelope["baseline_commit"]), envelope.get("model"), schema_preflight_path
    )
    report_schema_binding = _artifact_binding(
        record.get("auditor_report_schema"), "controller issuance auditor_report_schema"
    )
    _require(
        Path(report_schema_binding["path"]).resolve() == Path(str(envelope["report_schema"])).resolve(),
        "controller-bound Auditor report schema path mismatch",
    )
    _require(
        sha256_file(Path(report_schema_binding["path"])) == report_schema_binding["sha256"],
        "controller-bound Auditor report schema checksum mismatch",
    )
    consumption_path = Path(str(authorization["consumption_record"]))
    _require(Path(str(record.get("consumption_record"))).resolve() == consumption_path.resolve(), "consumption record path mismatch")
    if require_unused:
        _require(not consumption_path.exists(), "Auditor authorization was already consumed")
    for label, binding in envelope["frozen_subject"].items():
        path = Path(str(binding["path"]))
        _require(path.is_file(), "{} binding is missing".format(label))
        _require(sha256_file(path) == binding["sha256"], "{} binding checksum mismatch".format(label))
    _require(sha256_file(Path(str(envelope["prompt_file"]))) == envelope["prompt_sha256"], "Auditor prompt checksum mismatch")
    _verify_workspace_binding(envelope)
    return record


def _claim_auditor_authorization(envelope: Mapping[str, Any]) -> Path:
    authorization = envelope["controller_authorization"]
    path = Path(str(authorization["consumption_record"]))
    value = {
        "canary": CANARY,
        "issuer": AUDITOR_ISSUER,
        "authorization_id": authorization["authorization_id"],
        "state": "CONSUMED",
        "consumed_at_epoch_seconds": int(time.time()),
    }
    try:
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise FlightlineError("Auditor authorization was already consumed") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return path


def _preflight_comparison(expected: Mapping[str, Any], current: Mapping[str, Any]) -> Dict[str, Any]:
    mismatches: Dict[str, Dict[str, Any]] = {}
    for key in PREFLIGHT_COMPARISON_FIELDS:
        expected_value = expected.get(key)
        current_value = current.get(key)
        if expected_value == current_value:
            continue
        if key != "metadata" or not isinstance(expected_value, dict) or not isinstance(current_value, dict):
            mismatches[key] = {"authorization": expected_value, "launch": current_value}
            continue
        for metadata_key in sorted(set(expected_value) | set(current_value)):
            expected_metadata_value = expected_value.get(metadata_key)
            current_metadata_value = current_value.get(metadata_key)
            if expected_metadata_value != current_metadata_value:
                mismatches["metadata." + metadata_key] = {
                    "authorization": expected_metadata_value,
                    "launch": current_metadata_value,
                }

    expected_metadata = expected.get("metadata")
    current_metadata = current.get("metadata")
    expected_refs = expected_metadata.get("security_relevant_refs", {}) if isinstance(expected_metadata, dict) else {}
    current_refs = current_metadata.get("security_relevant_refs", {}) if isinstance(current_metadata, dict) else {}
    ref_changes: Dict[str, Dict[str, Optional[str]]] = {}
    if isinstance(expected_refs, dict) and isinstance(current_refs, dict):
        for ref_name in sorted(set(expected_refs) | set(current_refs)):
            if expected_refs.get(ref_name) != current_refs.get(ref_name):
                ref_changes[ref_name] = {
                    "authorization": expected_refs.get(ref_name),
                    "launch": current_refs.get(ref_name),
                }
    return {
        "matched": not mismatches,
        "mismatches": mismatches,
        "security_relevant_ref_changes": ref_changes,
    }


def _verify_foreground_preflight(envelope: Mapping[str, Any]) -> None:
    binding = envelope["frozen_subject"]["foreground_preflight"]
    expected = _load_json(Path(str(binding["path"])))
    current = collect_preflight(envelope)
    comparison = _preflight_comparison(expected, current)
    record_path = Path(str(envelope["controller_authorization"]["consumption_record"])).with_name(
        "controller-launch-preflight.json"
    )
    _require_immutable_control_path(record_path, envelope, "controller launch preflight record")
    _require(not record_path.exists(), "controller launch preflight record already exists; issue a fresh authorization")
    record = {
        "canary": CANARY,
        "issuer": AUDITOR_ISSUER,
        "authorization_id": envelope["controller_authorization"]["authorization_id"],
        "state": "MATCHED" if comparison["matched"] else "BLOCKED",
        "authorization_preflight": {
            "path": str(Path(str(binding["path"])).resolve()),
            "sha256": binding["sha256"],
            "captured_at_epoch_seconds": expected.get("captured_at_epoch_seconds"),
            "metadata": expected.get("metadata"),
        },
        "launch_preflight": {
            "captured_at_epoch_seconds": current.get("captured_at_epoch_seconds"),
            "metadata": current.get("metadata"),
        },
        "comparison": comparison,
    }
    _atomic_json(record_path, record)
    if comparison["mismatches"]:
        fields = ", ".join(sorted(comparison["mismatches"]))
        raise FlightlineError(
            "foreground preflight changed before Auditor launch: {} (comparison: {})".format(fields, record_path)
        )


def _prompt_text(envelope: Mapping[str, Any], envelope_path: Path) -> str:
    prompt_value = envelope.get("prompt_file")
    _require(isinstance(prompt_value, str) and prompt_value, "launch requires prompt_file")
    prompt_path = _absolute_path(prompt_value, "prompt_file")
    _require(prompt_path.is_file(), "prompt_file does not exist")
    expected_hash = envelope.get("prompt_sha256")
    _require(isinstance(expected_hash, str) and len(expected_hash) == 64, "launch requires prompt_sha256")
    _require(sha256_file(prompt_path) == expected_hash, "prompt checksum mismatch")
    role_file = Path(__file__).resolve().parent / "roles" / (str(envelope["role"]) + ".md")
    role_text = role_file.read_text(encoding="utf-8")
    mission_text = prompt_path.read_text(encoding="utf-8")
    handshake = {
        "CANARY": CANARY,
        "ROLE": envelope["role"],
        "MISSION": envelope["mission"],
        "BASELINE": envelope["baseline_commit"],
        "AUTHORIZED_WRITABLE_SCOPE": envelope["allowed_write_paths"],
        "NETWORK": "OFF",
        "COMMIT_AUTHORITY": "NONE",
        "STATE": envelope["state"],
        "ENVELOPE": str(envelope_path.resolve()),
    }
    if envelope["role"] == "independent-auditor":
        handshake["CONTROLLER_AUTHORIZATION"] = envelope["controller_authorization"]
        handshake["FROZEN_SUBJECT"] = envelope["frozen_subject"]
    return "{}\n\n## Required handshake\n\n```json\n{}\n```\n\n## Approved mission prompt\n\n{}".format(
        role_text.rstrip(), json.dumps(handshake, indent=2, sort_keys=True), mission_text.rstrip()
    )


def _event_counts(payload: Any) -> Tuple[int, int]:
    """Conservatively extract command starts and total-token usage from JSONL."""

    commands = 0
    tokens = 0
    if isinstance(payload, dict):
        event_type = str(payload.get("type", payload.get("event_type", ""))).lower()
        if "command" in event_type and ("start" in event_type or event_type.endswith("command_execution")):
            commands += 1
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in {"total_tokens", "totaltokens"} and isinstance(value, int):
                tokens = max(tokens, value)
            nested_commands, nested_tokens = _event_counts(value)
            commands += nested_commands
            tokens = max(tokens, nested_tokens)
    elif isinstance(payload, list):
        for value in payload:
            nested_commands, nested_tokens = _event_counts(value)
            commands += nested_commands
            tokens = max(tokens, nested_tokens)
    return commands, tokens


def _consume_event_line(
    line: str,
    log: Any,
    command_count: int,
    token_count: int,
    budgets: Mapping[str, Any],
) -> Tuple[int, int, Optional[str], Optional[Dict[str, Any]]]:
    log.write(line)
    log.flush()
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return command_count, token_count, "invalid_jsonl_event", None
    handshake = None
    if isinstance(payload, dict) and payload.get("type") == "thread.started":
        thread_id = payload.get("thread_id")
        if isinstance(thread_id, str) and thread_id:
            handshake = {
                "event_type": "thread.started",
                "thread_id": thread_id,
                "event_sha256": _sha256_bytes(line.encode("utf-8")),
            }
    new_commands, observed_tokens = _event_counts(payload)
    command_count += new_commands
    token_count = max(token_count, observed_tokens)
    if command_count > budgets["command_budget"]:
        return command_count, token_count, "command_budget_exceeded", handshake
    if token_count > budgets["token_budget"]:
        return command_count, token_count, "token_budget_exceeded", handshake
    return command_count, token_count, None, handshake


def _stop_child(child: subprocess.Popen, interrupt: bool = False) -> int:
    if child.poll() is not None:
        return int(child.returncode)
    if interrupt:
        child.send_signal(signal.SIGINT)
    else:
        child.terminate()
    try:
        return child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()
        return child.wait(timeout=5)


def _supervise_process(
    command: Sequence[str],
    prompt: str,
    environment: Mapping[str, str],
    output_root: Path,
    role: str,
    budgets: Mapping[str, Any],
    working_directory: Optional[Path] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Supervise one local child and preserve evidence on every stop path."""

    output_root.mkdir(parents=True, exist_ok=True)
    log_path = output_root / (role + "-events.jsonl")
    summary_path = output_root / (role + "-supervisor.json")
    stderr_path = output_root / (role + "-stderr.log")
    startup_path = output_root / (role + "-startup.json")
    resolved_cwd = (working_directory or Path.cwd()).resolve()
    redacted_argv = _redact_command(command)
    started = time.monotonic()
    started_epoch = int(time.time())
    command_count = 0
    token_count = 0
    stop_reason_code: Optional[str] = None
    exit_code: Optional[int] = None
    child: Optional[subprocess.Popen] = None
    activated = False
    activation_handshake: Optional[Dict[str, Any]] = None
    controller_stop = False
    startup_evidence: Dict[str, Any] = {
        "canary": CANARY,
        "role": role,
        "state": "CHILD_NOT_CREATED",
        "child_created": False,
        "environment_activated": False,
        "working_directory": str(resolved_cwd),
        "redacted_argv": redacted_argv,
        "started_at_epoch_seconds": started_epoch,
        "transitions": [
            {"state": "CHILD_NOT_CREATED", "at_epoch_seconds": started_epoch}
        ],
    }

    def transition(state: str, **fields: Any) -> None:
        timestamp = int(time.time())
        startup_evidence.update(fields)
        startup_evidence["state"] = state
        startup_evidence["updated_at_epoch_seconds"] = timestamp
        startup_evidence["transitions"].append({"state": state, "at_epoch_seconds": timestamp})
        _atomic_json(startup_path, startup_evidence)

    def consume(line: str, log: Any) -> None:
        nonlocal activated, activation_handshake, command_count, token_count, stop_reason_code
        command_count, token_count, event_stop, handshake = _consume_event_line(
            line, log, command_count, token_count, budgets
        )
        stop_reason_code = stop_reason_code or event_stop
        if handshake is not None and not activated:
            activated = True
            activation_handshake = handshake
            transition(
                "AUDITOR_ENVIRONMENT_ACTIVATED"
                if role == "independent-auditor"
                else "ENGINEER_ENVIRONMENT_ACTIVATED",
                environment_activated=True,
                activation_handshake=handshake,
            )

    _atomic_json(startup_path, startup_evidence)
    with log_path.open("w", encoding="utf-8") as log, stderr_path.open("w", encoding="utf-8") as stderr_log:
        try:
            child = subprocess.Popen(
                list(command),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr_log,
                text=True,
                bufsize=1,
                env=dict(environment),
                cwd=str(resolved_cwd),
            )
        except OSError as exc:
            stop_reason_code = "child_not_created"
            controller_stop = True
            stderr_log.write("child creation failed: {}\n".format(exc))
            stderr_log.flush()
            transition("CHILD_NOT_CREATED", creation_error=str(exc))
        if child is not None:
            transition("CHILD_CREATED", child_created=True, child_pid=child.pid)
            assert child.stdin is not None
            assert child.stdout is not None
            try:
                child.stdin.write(prompt)
                child.stdin.close()
            except BrokenPipeError:
                stop_reason_code = "startup_rejected"
            selector = selectors.DefaultSelector()
            selector.register(child.stdout, selectors.EVENT_READ)
            try:
                while child.poll() is None:
                    elapsed = time.monotonic() - started
                    if elapsed > budgets["time_seconds"]:
                        stop_reason_code = "time_budget_exceeded"
                        controller_stop = True
                        break
                    for key, _ in selector.select(timeout=0.25):
                        line = key.fileobj.readline()
                        if not line:
                            continue
                        consume(line, log)
                        if stop_reason_code:
                            controller_stop = True
                            break
                    if stop_reason_code:
                        break
                if controller_stop:
                    exit_code = _stop_child(child)
                else:
                    exit_code = child.wait(timeout=5)
                for line in child.stdout:
                    consume(line, log)
            except KeyboardInterrupt:
                stop_reason_code = "operator_cancelled"
                controller_stop = True
                exit_code = _stop_child(child, interrupt=True)
            finally:
                selector.close()
                child.stdout.close()
    diagnostic: Optional[str] = None
    if child is not None and not activated:
        if stop_reason_code is None:
            stop_reason_code = "startup_rejected" if exit_code else "startup_handshake_missing"
        controller_stop = controller_stop or exit_code == 0
        stderr_lines = [line.strip() for line in stderr_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        diagnostic = stderr_lines[-1] if stderr_lines else "child exited before the startup handshake"
        transition("STARTUP_REJECTED", stop_reason_code=stop_reason_code, diagnostic=diagnostic)
    elif child is not None and activated:
        if exit_code == 0 and stop_reason_code is None:
            transition("COMPLETED")
        else:
            if stop_reason_code is None:
                stop_reason_code = "child_exit_nonzero"
            transition("TERMINATED", stop_reason_code=stop_reason_code)
    elif child is None:
        diagnostic_lines = [
            line.strip() for line in stderr_path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        diagnostic = diagnostic_lines[-1] if diagnostic_lines else "child process was not created"

    stop_reason = None
    if stop_reason_code is not None:
        phase = "startup" if not activated else "execution"
        stop_reason = {
            "code": stop_reason_code,
            "phase": phase,
            "diagnostic": diagnostic,
            "stderr_log": str(stderr_path),
        }
    if stop_reason is not None and stop_reason["phase"] == "startup":
        print(
            "Flightline {} startup failed [{}]: {} (full stderr: {})".format(
                role, stop_reason_code, diagnostic, stderr_path
            ),
            file=sys.stderr,
        )

    lifecycle_state = str(startup_evidence["state"])
    if exit_code == 0 and activated and stop_reason is None:
        supervisor_state = "READY_FOR_AUDIT"
    elif activated and stop_reason_code == "child_exit_nonzero":
        supervisor_state = "INCOMPLETE"
    else:
        supervisor_state = "BLOCKED"
    summary = {
        "canary": CANARY,
        "role": role,
        "state": supervisor_state,
        "lifecycle_state": lifecycle_state,
        "exit_code": exit_code,
        "stop_reason": stop_reason,
        "child": {
            "created": child is not None,
            "pid": child.pid if child is not None else None,
            "working_directory": str(resolved_cwd),
            "redacted_argv": redacted_argv,
        },
        "activation": {
            "verified": activated,
            "handshake": activation_handshake,
            "startup_evidence": str(startup_path),
        },
        "command_count": command_count,
        "observed_total_tokens": token_count,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "event_log": str(log_path),
        "stderr_log": str(stderr_path),
    }
    _atomic_json(summary_path, summary)
    if child is None or controller_stop:
        return 2, summary
    return int(exit_code if exit_code is not None else 2), summary


def supervise_launch(envelope: Mapping[str, Any], envelope_path: Path) -> int:
    _require(envelope["state"] in LAUNCHABLE_STATES, "launch requires PREFLIGHTED state")
    worktree = Path(str(envelope["worktree_path"]))
    _require(worktree.is_dir(), "launch worktree does not exist")
    if envelope["role"] == "independent-auditor":
        verify_controller_authorization(envelope, envelope_path, require_unused=True)
        _verify_foreground_preflight(envelope)
    else:
        _require(_git(worktree, ["rev-parse", "HEAD"]).stdout.strip() == envelope["baseline_commit"], "worktree baseline mismatch")
    output_root = Path(str(envelope["output_root"]))
    _require_immutable_control_path(envelope_path, envelope, "authorization envelope")
    command = build_launch_command(envelope, envelope_path)
    prompt = _prompt_text(envelope, envelope_path)
    if envelope["role"] == "independent-auditor":
        _claim_auditor_authorization(envelope)
    environment = build_launch_environment(envelope, envelope_path)
    exit_code, _ = _supervise_process(
        command,
        prompt,
        environment,
        output_root,
        str(envelope["role"]),
        envelope["budgets"],
        working_directory=worktree,
    )
    return exit_code


def _status_entries(worktree: Path) -> List[Dict[str, str]]:
    output = _git(worktree, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]).stdout
    parts = output.split("\0")
    entries: List[Dict[str, str]] = []
    index = 0
    while index < len(parts) and parts[index]:
        record = parts[index]
        status = record[:2]
        path = record[3:]
        entry = {"status": status, "path": path}
        if "R" in status or "C" in status:
            index += 1
            if index < len(parts):
                entry["source_path"] = parts[index]
        entries.append(entry)
        index += 1
    return entries


def freeze_evidence(envelope: Mapping[str, Any], preflight_path: Path) -> Dict[str, Any]:
    _require(envelope["role"] == "development-engineer", "only the Engineer change is frozen")
    preflight = _load_json(preflight_path)
    repository = Path(str(envelope["repository_root"]))
    worktree = Path(str(envelope["worktree_path"]))
    _require(preflight.get("baseline_commit") == envelope["baseline_commit"], "preflight baseline mismatch")
    current_metadata = _git_metadata_snapshot(repository)
    _require(current_metadata["refs_sha256"] == preflight["metadata"]["refs_sha256"], "Git refs changed during the run")
    _require(current_metadata["index_sha256"] == preflight["metadata"]["index_sha256"], "foreground Git index changed during the run")
    _require(current_metadata["local_config_sha256"] == preflight["metadata"]["local_config_sha256"], "foreground Git configuration changed during the run")
    _require(current_metadata["remote_names_sha256"] == preflight["metadata"]["remote_names_sha256"], "foreground Git remotes changed during the run")
    _require(current_metadata["head"] == preflight["metadata"]["head"], "foreground HEAD changed during the run")
    current_status = _git(repository, ["status", "--porcelain=v2", "--branch"]).stdout.splitlines()
    _require(current_status == preflight["status_porcelain_v2"], "foreground working-tree state changed during the run")
    _require(_git(worktree, ["rev-parse", "HEAD"]).stdout.strip() == envelope["baseline_commit"], "worktree HEAD changed")
    entries = _status_entries(worktree)
    _require(len(entries) <= envelope["budgets"]["max_changed_files"], "changed-file budget exceeded")
    allowed_roots = [Path(path) for path in envelope["allowed_write_paths"]]
    for entry in entries:
        absolute = (worktree / entry["path"]).resolve(strict=False)
        _require(any(_is_within(absolute, root) or absolute == root for root in allowed_roots), "unauthorized changed path: {}".format(entry["path"]))
        _require("D" not in entry["status"], "deletion detected but not authorized: {}".format(entry["path"]))
    diff_check = _git(worktree, ["diff", "--check", "HEAD", "--"], check=False)
    _require(diff_check.returncode == 0, "git diff --check failed: {}".format(diff_check.stdout + diff_check.stderr))
    output_root = Path(str(envelope["output_root"]))
    output_root.mkdir(parents=True, exist_ok=True)
    diff_path = output_root / "frozen-change.diff"
    diff_bytes = _git(worktree, ["diff", "--binary", "--no-ext-diff", "HEAD", "--"]).stdout.encode("utf-8")
    untracked = []
    untracked_evidence_bytes = 0
    for entry in entries:
        if entry["status"] == "??":
            path = worktree / entry["path"]
            _require(not path.is_symlink(), "untracked symbolic links are not accepted as frozen evidence: {}".format(entry["path"]))
            size = path.stat().st_size
            untracked_evidence_bytes += size
            _require(untracked_evidence_bytes <= MAX_UNTRACKED_EVIDENCE_BYTES, "untracked evidence size limit exceeded")
            untracked_diff = _git(worktree, ["diff", "--binary", "--no-index", "--", "/dev/null", entry["path"]], check=False)
            _require(untracked_diff.returncode in (0, 1), "cannot freeze untracked file: {}".format(entry["path"]))
            diff_bytes += untracked_diff.stdout.encode("utf-8")
            untracked.append({"path": entry["path"], "sha256": sha256_file(path), "size": path.stat().st_size})
    diff_path.write_bytes(diff_bytes)
    manifest = {
        "canary": CANARY,
        "state": "READY_FOR_AUDIT",
        "baseline_commit": envelope["baseline_commit"],
        "entries": entries,
        "diff_path": str(diff_path),
        "diff_sha256": _sha256_bytes(diff_bytes),
        "untracked": untracked,
        "foreground_metadata_unchanged": True,
        "commit_authority": "NONE",
        "captured_at_epoch_seconds": int(time.time()),
    }
    _atomic_json(output_root / "frozen-manifest.json", manifest)
    return manifest


def _redact_command(command: Sequence[str]) -> List[str]:
    redacted = []
    for item in command:
        if item.startswith("hooks."):
            redacted.append("<HOOK_CONFIG>")
        elif item.startswith("permissions."):
            redacted.append("<PERMISSION_PROFILE>")
        else:
            redacted.append(item)
    return redacted


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "render-profile", "render-launch", "preflight", "prepare-worktree", "freeze", "launch"):
        child = subparsers.add_parser(name)
        child.add_argument("envelope", type=Path)
        if name == "preflight":
            child.add_argument("--output", type=Path, required=True)
        if name == "prepare-worktree":
            child.add_argument("--output", type=Path, required=True)
            child.add_argument("--confirm", required=True)
        if name == "freeze":
            child.add_argument("--preflight", type=Path, required=True)
    issue = subparsers.add_parser("issue-auditor")
    issue.add_argument("source_envelope", type=Path)
    issue.add_argument("--schema-preflight", type=Path, required=True)
    issue.add_argument("--frozen-manifest", type=Path, required=True)
    issue.add_argument("--evidence-package", type=Path, required=True)
    issue.add_argument("--audit-workspace", type=Path, required=True)
    issue.add_argument("--audit-output", type=Path, required=True)
    issue.add_argument("--authorization-root", type=Path, required=True)
    issue.add_argument("--expires-in-seconds", type=int, default=3600)
    issue.add_argument("--confirm", required=True)
    schema_preflight = subparsers.add_parser("preflight-auditor-schema")
    schema_preflight.add_argument("source_envelope", type=Path)
    schema_preflight.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight-auditor-schema":
            source = load_envelope(args.source_envelope)
            report = run_auditor_schema_preflight(source, args.output_root)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0
        if args.command == "issue-auditor":
            source = load_envelope(args.source_envelope)
            report = issue_auditor_envelope(
                source,
                args.schema_preflight,
                args.frozen_manifest,
                args.evidence_package,
                args.audit_workspace,
                args.audit_output,
                args.authorization_root,
                args.expires_in_seconds,
                args.confirm,
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0
        envelope = load_envelope(args.envelope)
        if envelope["role"] == "independent-auditor" and args.command != "launch":
            verify_controller_authorization(envelope, args.envelope.resolve(), require_unused=True)
        if args.command == "validate":
            print(json.dumps({"canary": CANARY, "status": "valid", "role": envelope["role"]}, sort_keys=True))
        elif args.command == "render-profile":
            profile_id, override = build_permission_profile(envelope)
            print(json.dumps({"profile_id": profile_id, "override": override}, indent=2, sort_keys=True))
        elif args.command == "render-launch":
            print(json.dumps(_redact_command(build_launch_command(envelope, args.envelope)), indent=2))
        elif args.command == "preflight":
            report = collect_preflight(envelope)
            _atomic_json(_require_output_path(args.output, envelope, "preflight output"), report)
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.command == "prepare-worktree":
            report = prepare_worktree(envelope, args.confirm)
            _atomic_json(_require_output_path(args.output, envelope, "worktree report output"), report)
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.command == "freeze":
            preflight_path = _require_output_path(args.preflight, envelope, "preflight evidence")
            print(json.dumps(freeze_evidence(envelope, preflight_path), indent=2, sort_keys=True))
        elif args.command == "launch":
            return supervise_launch(envelope, args.envelope.resolve())
        return 0
    except FlightlineError as exc:
        print("BLOCKED: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
