"""Fresh read-only Codex execution preparation for Crew Chief."""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from tools.crew_chief.controller import verify_envelope
from tools.crew_chief.core import (
    CrewChiefError,
    atomic_write,
    bind_file,
    canonical_json_bytes,
    ensure_external_path,
    new_external_directory,
    normalize_repo_path,
    payload_encoding,
    read_json,
    redact_text,
    sha256_bytes,
    sha256_file,
    utc_now,
    write_canonical_json,
)
from tools.crew_chief.git_evidence import git_state
from tools.crew_chief.service_schema import (
    bundle_report_schema,
    normalize_service_output,
    project_service_schema,
    validate_service_instance,
    validate_service_schema,
)
from tools.crew_chief.validation import validate_report


_DISABLED_REVIEW_FEATURES = (
    "apps",
    "auth_elicitation",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "code_mode_host",
    "collaboration_modes",
    "computer_use",
    "enable_request_compression",
    "fast_mode",
    "goals",
    "guardian_approval",
    "image_generation",
    "in_app_browser",
    "in_app_updates",
    "hooks",
    "item_ids",
    "mentions_v2",
    "multi_agent",
    "multi_agent_v2",
    "personality",
    "plugins",
    "plugin_sharing",
    "recommended_plugins",
    "remote_compaction_v2",
    "remote_plugin",
    "resize_all_images",
    "shell_snapshot",
    "shell_tool",
    "skill_mcp_dependency_install",
    "skill_search",
    "sqlite",
    "standalone_web_search",
    "steer",
    "terminal_resize_reflow",
    "web_search_cached",
    "web_search_request",
    "tool_call_mcp_elicitation",
    "tool_search_always_defer_mcp_tools",
    "tool_suggest",
    "tui_app_server",
    "unified_exec",
    "workspace_dependencies",
)
_PERMITTED_REVIEW_FEATURES: tuple[str, ...] = ()
_ACCEPTED_ENABLED_FEATURES = frozenset(
    (*_DISABLED_REVIEW_FEATURES, *_PERMITTED_REVIEW_FEATURES)
)
_REQUIRED_EXEC_FLAGS = frozenset(
    {
        "--config",
        "--cd",
        "--color",
        "--disable",
        "--ephemeral",
        "--ignore-rules",
        "--ignore-user-config",
        "--output-last-message",
        "--output-schema",
        "--sandbox",
        "--strict-config",
    }
)
_MAX_EMBEDDED_EVIDENCE_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class CodexCapabilities:
    executable: str
    version: str
    exec_flags: tuple[str, ...]
    features: tuple[str, ...]
    shell_tool_control: bool
    custom_agent_selector: bool


def _validate_enabled_features(features: tuple[str, ...]) -> None:
    if len(features) != len(set(features)):
        raise CrewChiefError("Codex enabled-feature evidence is duplicated")
    unsupported = sorted(set(features) - _ACCEPTED_ENABLED_FEATURES)
    if unsupported:
        raise CrewChiefError(
            "Codex has unsupported enabled features: " + ", ".join(unsupported)
        )


def _validate_capabilities(capabilities: CodexCapabilities) -> None:
    _validate_enabled_features(capabilities.features)
    missing = sorted(_REQUIRED_EXEC_FLAGS - set(capabilities.exec_flags))
    if missing:
        raise CrewChiefError(
            f"installed Codex exec lacks required controls: {missing}"
        )
    if not capabilities.shell_tool_control:
        raise CrewChiefError("Codex shell-tool disable control is unavailable")


def _completed(
    runner: Callable[..., subprocess.CompletedProcess[str]],
    arguments: list[str],
) -> subprocess.CompletedProcess[str]:
    return runner(
        arguments,
        check=False,
        capture_output=True,
        text=True,
    )


def detect_codex_capabilities(
    executable: str = "codex",
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> CodexCapabilities:
    resolved = shutil.which(executable)
    if resolved is None:
        candidate = Path(executable)
        resolved = str(candidate.resolve()) if candidate.is_file() else None
    if resolved is None:
        raise CrewChiefError("Codex CLI is unavailable")
    version_result = _completed(runner, [resolved, "--version"])
    if version_result.returncode != 0:
        raise CrewChiefError("Codex CLI version detection failed")
    help_result = _completed(runner, [resolved, "exec", "--help"])
    if help_result.returncode != 0:
        raise CrewChiefError("Codex exec capability detection failed")
    feature_result = _completed(runner, [resolved, "features", "list"])
    if feature_result.returncode != 0:
        raise CrewChiefError(
            "Codex enabled-feature detection failed; isolation cannot be proven"
        )
    features = []
    available_features = set()
    for line in feature_result.stdout.splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("WARNING"):
            continue
        if len(fields) < 2 or fields[-1].lower() not in {"true", "false"}:
            raise CrewChiefError(
                "Codex enabled-feature evidence is malformed; isolation cannot be proven"
            )
        if fields[0] in available_features:
            raise CrewChiefError(
                "Codex enabled-feature evidence is duplicated; isolation cannot be proven"
            )
        available_features.add(fields[0])
        if fields[-1].lower() == "true":
            features.append(fields[0])
    help_text = help_result.stdout
    flags = tuple(
        sorted(flag for flag in _REQUIRED_EXEC_FLAGS if flag in help_text)
    )
    if set(flags) != set(_REQUIRED_EXEC_FLAGS):
        missing = sorted(_REQUIRED_EXEC_FLAGS - set(flags))
        raise CrewChiefError(
            f"installed Codex exec lacks required controls: {missing}"
        )
    if "shell_tool" not in available_features:
        raise CrewChiefError(
            "installed Codex CLI exposes no supported shell-tool disable control"
        )
    capabilities = CodexCapabilities(
        executable=resolved,
        version=version_result.stdout.strip().splitlines()[-1],
        exec_flags=flags,
        features=tuple(sorted(set(features))),
        shell_tool_control=True,
        custom_agent_selector="--agent" in help_text,
    )
    _validate_capabilities(capabilities)
    return capabilities


def _build_isolated_launch_command(
    capabilities: CodexCapabilities,
    workspace: Path,
    schema: Path,
    report_output: Path,
    *,
    agent: str | None,
) -> list[str]:
    _validate_capabilities(capabilities)
    command = [
        capabilities.executable,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--strict-config",
        "--config",
        'approval_policy="never"',
        "--sandbox",
        "read-only",
        "--output-schema",
        str(schema),
        "--output-last-message",
        str(report_output),
        "--color",
        "never",
        "--cd",
        str(workspace),
    ]
    for feature in _DISABLED_REVIEW_FEATURES:
        if feature in capabilities.features:
            command.extend(["--disable", feature])
    if agent is not None:
        if not capabilities.custom_agent_selector:
            raise CrewChiefError("Codex custom-agent selection is unavailable")
        command.extend(["--agent", agent])
    command.append("-")
    return command


def build_launch_command(
    capabilities: CodexCapabilities,
    workspace: Path,
    schema: Path,
    report_output: Path,
) -> list[str]:
    """Construct the canonical isolated Crew Chief command."""
    agent = "crew_chief" if capabilities.custom_agent_selector else None
    return _build_isolated_launch_command(
        capabilities,
        workspace,
        schema,
        report_output,
        agent=agent,
    )


def build_ordinary_bootstrap_launch_command(
    capabilities: CodexCapabilities,
    workspace: Path,
    schema: Path,
    report_output: Path,
) -> list[str]:
    """Construct the canonical isolated ordinary-bootstrap command."""
    return _build_isolated_launch_command(
        capabilities,
        workspace,
        schema,
        report_output,
        agent=None,
    )


def _copy_regular_tree(source: Path, target: Path) -> None:
    for item in sorted(source.rglob("*")):
        relative = item.relative_to(source)
        destination = target / relative
        if item.is_symlink():
            raise CrewChiefError(f"frozen evidence contains a symlink: {relative}")
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            atomic_write(destination, item.read_bytes())
        else:
            raise CrewChiefError(
                f"frozen evidence contains an unsupported file: {relative}"
            )


def _bundled_report_schema(frozen_root: Path) -> dict[str, Any]:
    return bundle_report_schema(frozen_root / "controls" / "schemas")


def _embedded_evidence(frozen_root: Path) -> str:
    files = [item for item in sorted(frozen_root.rglob("*")) if item.is_file()]
    total = sum(item.stat().st_size for item in files)
    if total > _MAX_EMBEDDED_EVIDENCE_BYTES:
        raise CrewChiefError(
            "frozen evidence exceeds the 16 MiB standard-input safety limit"
        )
    blocks = []
    for item in files:
        relative = item.relative_to(frozen_root).as_posix()
        payload = item.read_bytes()
        encoding, _line_count = payload_encoding(payload)
        if encoding == "utf-8":
            content = payload.decode("utf-8")
        else:
            content = base64.b64encode(payload).decode("ascii")
        blocks.extend(
            [
                (
                    f"=== BEGIN FROZEN {relative} encoding={encoding} "
                    f"size={len(payload)} sha256={sha256_bytes(payload)} ==="
                ),
                content,
                f"=== END FROZEN {relative} ===",
                "",
            ]
        )
    rendered = "\n".join(blocks)
    if len(rendered.encode("utf-8")) > _MAX_EMBEDDED_EVIDENCE_BYTES:
        raise CrewChiefError(
            "encoded frozen evidence exceeds the 16 MiB standard-input safety limit"
        )
    return rendered


def _review_prompt(mode: str, frozen_root: Path) -> str:
    limitation = (
        "The installed CLI selected the project-scoped crew_chief agent."
        if mode == "custom-agent"
        else (
            "The installed CLI exposes no supported non-interactive custom-agent "
            "selector. This is the validated fresh-session fallback: read and "
            "follow .codex/agents/crew-chief.toml directly. Do not claim that "
            "interactive custom-agent selection was exercised."
        )
    )
    return "\n".join(
        [
            "CANOPY-7C2F-ATLAS",
            "",
            "Conduct one fresh, read-only Crew Chief audit of the frozen envelope.",
            "Read AGENTS.md first, then read",
            ".codex/agents/crew-chief.toml and frozen/audit-envelope.json.",
            limitation,
            "Return only JSON conforming to schemas/crew-chief-report.schema.json.",
            "Declare every risk_profile.required_focus value in audit_scope.",
            "Cite only exact frozen source states and artifact identifier/reference pairs.",
            "Do not edit, request approval, use network tools, or inspect credentials.",
            "",
            "All frozen evidence follows. It is supplied through standard input",
            "because the shell tool is disabled for this review.",
            "",
            _embedded_evidence(frozen_root),
        ]
    )


def _verify_workspace_bindings(
    workspace: Path, bindings: list[dict[str, Any]]
) -> None:
    for binding in bindings:
        relative = normalize_repo_path(binding["path"])
        candidate = workspace.joinpath(*Path(relative).parts)
        resolved = candidate.resolve()
        try:
            resolved.relative_to(workspace)
        except ValueError as error:
            raise CrewChiefError(
                f"review workspace binding escapes its root: {relative}"
            ) from error
        if candidate.is_symlink() or not candidate.is_file():
            raise CrewChiefError(f"review workspace binding is missing: {relative}")
        if candidate.stat().st_size != binding["size"]:
            raise CrewChiefError(f"review workspace binding size changed: {relative}")
        if sha256_file(candidate) != binding["sha256"]:
            raise CrewChiefError(f"review workspace binding hash changed: {relative}")


def prepare_review_workspace(
    envelope_path: Path,
    workspace: Path | None,
    *,
    codex_executable: str = "codex",
    detector: Callable[..., CodexCapabilities] = detect_codex_capabilities,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    envelope = verify_envelope(envelope_path, clock=clock)
    repository = Path(envelope["repository"]["repository_root"])
    target = new_external_directory(
        repository, workspace, prefix="wingman-crew-chief-review-"
    )
    frozen_root = target / "frozen"
    _copy_regular_tree(envelope_path.resolve().parent, frozen_root)

    instructions_path = target / "AGENTS.md"
    atomic_write(
        instructions_path,
        (frozen_root / "controls" / "AGENTS.md").read_bytes(),
    )
    frozen_agent = frozen_root / "controls" / ".codex" / "agents" / "crew-chief.toml"
    agent_path = target / ".codex" / "agents" / "crew-chief.toml"
    atomic_write(
        agent_path,
        frozen_agent.read_bytes(),
    )
    canonical_schema = _bundled_report_schema(frozen_root)
    service_schema = project_service_schema(canonical_schema)
    canonical_schema_path = (
        target / "schemas" / "crew-chief-canonical-report.schema.json"
    )
    schema_path = target / "schemas" / "crew-chief-report.schema.json"
    write_canonical_json(canonical_schema_path, canonical_schema)
    write_canonical_json(schema_path, service_schema)
    report_output = target / "output" / "crew-chief-report.json"
    capabilities = detector(codex_executable)
    mode = (
        "custom-agent"
        if capabilities.custom_agent_selector
        else "fresh-session-fallback"
    )
    prompt_path = target / "audit-instructions.md"
    atomic_write(prompt_path, _review_prompt(mode, frozen_root).encode("utf-8"))
    command = build_launch_command(
        capabilities, target, schema_path, report_output
    )
    invocation = {
        "schema_version": "1.0",
        "audit_id": envelope["audit_id"],
        "envelope_id": envelope["envelope_id"],
        "workspace": str(target),
        "execution_mode": mode,
        "capabilities": asdict(capabilities),
        "argv": command,
        "prompt_path": str(prompt_path),
        "canonical_schema_path": str(canonical_schema_path),
        "schema_path": str(schema_path),
        "report_path": str(report_output),
        "workspace_bindings": [
            bind_file(instructions_path, "AGENTS.md"),
            bind_file(agent_path, ".codex/agents/crew-chief.toml"),
            bind_file(prompt_path, "audit-instructions.md"),
            bind_file(
                canonical_schema_path,
                "schemas/crew-chief-canonical-report.schema.json",
            ),
            bind_file(schema_path, "schemas/crew-chief-report.schema.json"),
        ],
        "live_audit_performed": False,
        "automation_limitation": (
            None
            if capabilities.custom_agent_selector
            else (
                "No supported non-interactive custom-agent selector was detected; "
                "execution requires an explicit fresh-session fallback decision."
            )
        ),
    }
    write_canonical_json(target / "invocation.json", invocation)
    return invocation


def _authentication_available(
    executable: str,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> bool:
    result = _completed(runner, [executable, "login", "status"])
    return result.returncode == 0


def _sanitized_environment() -> dict[str, str]:
    allowed = {
        "CODEX_HOME",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "TERM",
        "TMPDIR",
    }
    return {name: value for name, value in os.environ.items() if name in allowed}


def _consume(workspace: Path, envelope: dict[str, Any]) -> Path:
    marker = workspace / ".crew-chief-consumed.json"
    try:
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise CrewChiefError(
            "audit envelope was already consumed in this workspace"
        ) from error
    payload = canonical_json_bytes(
        {
            "audit_id": envelope["audit_id"],
            "envelope_id": envelope["envelope_id"],
            "consumed_at": utc_now().isoformat().replace("+00:00", "Z"),
        }
    ) + b"\n"
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return marker


def execute_prepared_review(
    envelope_path: Path,
    invocation: dict[str, Any],
    *,
    allow_fresh_session_fallback: bool = False,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    timeout_seconds: int = 3600,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Execute one explicitly authorized live audit; tests inject a fake runner."""
    envelope = verify_envelope(envelope_path, clock=clock)
    workspace = Path(invocation["workspace"]).resolve()
    repository = Path(envelope["repository"]["repository_root"])
    ensure_external_path(repository, workspace, "review workspace")
    if invocation.get("audit_id") != envelope["audit_id"] or invocation.get(
        "envelope_id"
    ) != envelope["envelope_id"]:
        raise CrewChiefError("review invocation does not match the audit envelope")
    if invocation.get("live_audit_performed") is not False:
        raise CrewChiefError("review invocation has an invalid execution state")
    capabilities_value = invocation.get("capabilities", {})
    try:
        capabilities = CodexCapabilities(
            executable=capabilities_value["executable"],
            version=capabilities_value["version"],
            exec_flags=tuple(capabilities_value["exec_flags"]),
            features=tuple(capabilities_value["features"]),
            shell_tool_control=capabilities_value["shell_tool_control"],
            custom_agent_selector=capabilities_value["custom_agent_selector"],
        )
    except (KeyError, TypeError) as error:
        raise CrewChiefError("review invocation capabilities are invalid") from error
    expected_mode = (
        "custom-agent"
        if capabilities.custom_agent_selector
        else "fresh-session-fallback"
    )
    if invocation.get("execution_mode") != expected_mode:
        raise CrewChiefError("review invocation execution mode is invalid")
    prompt_path = workspace / "audit-instructions.md"
    canonical_schema_path = (
        workspace / "schemas" / "crew-chief-canonical-report.schema.json"
    )
    schema_path = workspace / "schemas" / "crew-chief-report.schema.json"
    report_path = workspace / "output" / "crew-chief-report.json"
    if (
        Path(invocation.get("prompt_path", "")).resolve() != prompt_path
        or Path(invocation.get("canonical_schema_path", "")).resolve()
        != canonical_schema_path
        or Path(invocation.get("schema_path", "")).resolve() != schema_path
        or Path(invocation.get("report_path", "")).resolve() != report_path
    ):
        raise CrewChiefError("review invocation paths are invalid")
    expected_argv = build_launch_command(
        capabilities, workspace, schema_path, report_path
    )
    if invocation.get("argv") != expected_argv:
        raise CrewChiefError("review invocation argv changed after preparation")
    bindings = invocation.get("workspace_bindings")
    if not isinstance(bindings, list):
        raise CrewChiefError("review workspace bindings are invalid")
    _verify_workspace_bindings(workspace, bindings)
    service_schema = read_json(schema_path)
    if not isinstance(service_schema, dict):
        raise CrewChiefError("review service schema is invalid")
    validate_service_schema(service_schema)
    if invocation["execution_mode"] == "fresh-session-fallback" and not allow_fresh_session_fallback:
        raise CrewChiefError(
            "installed CLI has no custom-agent selector; fresh-session fallback "
            "requires explicit authorization"
        )
    executable = invocation["capabilities"]["executable"]
    if not _authentication_available(executable, runner):
        raise CrewChiefError("Codex authentication is unavailable")

    before = git_state(repository)
    _consume(workspace, envelope)
    prompt = prompt_path.read_text(encoding="utf-8")
    result: subprocess.CompletedProcess[str] | None = None
    execution_failure: tuple[str, BaseException] | None = None
    diagnostic = ""
    try:
        result = runner(
            list(invocation["argv"]),
            input=prompt,
            cwd=workspace,
            env=_sanitized_environment(),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        if isinstance(error.stderr, bytes):
            diagnostic = error.stderr.decode("utf-8", errors="replace")
        elif isinstance(error.stderr, str):
            diagnostic = error.stderr
        execution_failure = (
            "Crew Chief execution exceeded its time limit",
            error,
        )
    except OSError as error:
        diagnostic = str(error)
        execution_failure = ("Crew Chief process could not be started", error)
    finally:
        after = git_state(repository)
    if result is not None:
        diagnostic = result.stderr
    atomic_write(
        workspace / "output" / "codex-stderr.log",
        redact_text(diagnostic).encode("utf-8"),
    )
    if before != after:
        raise CrewChiefError("unexpected repository mutation detected during review")
    if execution_failure is not None:
        message, cause = execution_failure
        raise CrewChiefError(message) from cause
    if result is None:
        raise CrewChiefError("Crew Chief process returned no result")
    verify_envelope(envelope_path, clock=clock)
    if result.returncode != 0:
        raise CrewChiefError(f"Codex review failed with exit code {result.returncode}")
    service_report = read_json(report_path)
    if not isinstance(service_report, dict):
        raise CrewChiefError("Crew Chief report must be a JSON object")
    validate_service_instance(service_schema, service_report)
    service_report_path = workspace / "output" / "crew-chief-service-report.json"
    write_canonical_json(service_report_path, service_report)
    canonical_schema = read_json(canonical_schema_path)
    if not isinstance(canonical_schema, dict):
        raise CrewChiefError("review canonical schema is invalid")
    report = normalize_service_output(service_report, canonical_schema)
    if not isinstance(report, dict):
        raise CrewChiefError("normalized Crew Chief report must be a JSON object")
    validate_report(envelope, report)
    write_canonical_json(report_path, report)
    record = {
        "schema_version": "1.0",
        "audit_id": envelope["audit_id"],
        "envelope_id": envelope["envelope_id"],
        "cli_version": invocation["capabilities"]["version"],
        "argv": invocation["argv"],
        "execution_mode": invocation["execution_mode"],
        "repository_state_before": before,
        "repository_state_after": after,
        "report_path": str(report_path),
        "service_report_path": str(service_report_path),
        "service_schema_sha256": sha256_file(schema_path),
        "live_audit_performed": True,
    }
    write_canonical_json(workspace / "output" / "run-record.json", record)
    return record


def run_audit(
    envelope_path: Path,
    workspace: Path | None,
    *,
    execute: bool = False,
    allow_fresh_session_fallback: bool = False,
    codex_executable: str = "codex",
    detector: Callable[..., CodexCapabilities] = detect_codex_capabilities,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    invocation = prepare_review_workspace(
        envelope_path,
        workspace,
        codex_executable=codex_executable,
        detector=detector,
        clock=clock,
    )
    if not execute:
        return invocation
    return execute_prepared_review(
        envelope_path,
        invocation,
        allow_fresh_session_fallback=allow_fresh_session_fallback,
        runner=runner,
        clock=clock,
    )
