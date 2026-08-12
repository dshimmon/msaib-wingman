"""Tamper-evident package binding for an externally authorized bootstrap."""

from __future__ import annotations

import os
import subprocess
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from tools.authorization import (
    AuthorityContextError,
    AuthorizationContext,
    authority_record,
    validate_authority_record,
)
from tools.crew_chief.core import (
    CANARY,
    CrewChiefError,
    atomic_write,
    canonical_json_bytes,
    clock_value,
    copy_bound_file,
    new_external_directory,
    parse_time,
    read_json,
    redact_text,
    sha256_bytes,
    sha256_file,
    utc_now,
    validate_sha256,
    write_canonical_json,
)
from tools.crew_chief.runner import (
    CodexCapabilities,
    build_ordinary_bootstrap_launch_command,
    detect_codex_capabilities,
)
from tools.crew_chief.validation import validate_instance


_CONTROL_NAME = "authorization-receipt.json"
_PACKAGE_NAME = "bootstrap-package.md"
_SCHEMA_NAME = "bootstrap-report.schema.json"
_PROMPT_NAME = "bootstrap-review-input.md"
_BOOTSTRAP_ROLE = "ordinary_codex_bootstrap_reviewer"
_COMMAND_CONTRACT_VERSION = "1.0"


@dataclass(frozen=True)
class AuthorizationExpectation:
    """Exact subject and scope supplied by the trusted local caller."""

    subject_head: str
    package_size: int
    package_sha256: str
    service_schema_size: int
    service_schema_sha256: str
    audit_id: str
    envelope_id: str
    package_expires_at: str
    authorization_text_sha256: str
    ordinary_bootstrap_invocations: int
    conditional_crew_chief_fixture_audits: int
    automatic_retries_permitted: bool
    authorization_text_size: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AuthorizationExpectation:
        current_fields = set(cls.__annotations__)
        legacy_fields = current_fields - {"authorization_text_size"}
        if not isinstance(value, dict):
            raise CrewChiefError("bootstrap authorization expectation is malformed")
        supplied_fields = set(value)
        if supplied_fields != current_fields and supplied_fields != legacy_fields:
            raise CrewChiefError("bootstrap authorization expectation is malformed")
        normalized = dict(value)
        normalized.setdefault("authorization_text_size", None)
        try:
            expectation = cls(**normalized)
        except TypeError as error:
            raise CrewChiefError(
                "bootstrap authorization expectation is malformed"
            ) from error
        _validate_expectation(expectation)
        return expectation


def _validate_expectation(expectation: AuthorizationExpectation) -> None:
    if (
        not isinstance(expectation.subject_head, str)
        or len(expectation.subject_head) != 40
        or any(
            character not in "0123456789abcdef"
            for character in expectation.subject_head
        )
    ):
        raise CrewChiefError("authorized subject HEAD must be a lowercase Git hash")
    for label, value in (
        ("package", expectation.package_sha256),
        ("service schema", expectation.service_schema_sha256),
        ("audit ID", expectation.audit_id),
        ("envelope ID", expectation.envelope_id),
        ("authorization text", expectation.authorization_text_sha256),
    ):
        validate_sha256(value, label)
    for label, value in (
        ("package size", expectation.package_size),
        ("service schema size", expectation.service_schema_size),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise CrewChiefError(f"{label} must be a positive integer")
    if expectation.authorization_text_size is not None and (
        not isinstance(expectation.authorization_text_size, int)
        or isinstance(expectation.authorization_text_size, bool)
        or expectation.authorization_text_size < 1
    ):
        raise CrewChiefError(
            "authorization text size must be a positive integer when supplied"
        )
    parse_time(expectation.package_expires_at)
    if expectation.ordinary_bootstrap_invocations != 1:
        raise CrewChiefError("a receipt authorizes exactly one bootstrap invocation")
    if (
        not isinstance(expectation.conditional_crew_chief_fixture_audits, int)
        or isinstance(expectation.conditional_crew_chief_fixture_audits, bool)
        or not 0 <= expectation.conditional_crew_chief_fixture_audits <= 2
    ):
        raise CrewChiefError(
            "a receipt authorizes at most two conditional fixture audits"
        )
    if expectation.automatic_retries_permitted is not False:
        raise CrewChiefError("bootstrap authorization cannot permit automatic retries")


def _required_authorization_text_size(
    expectation: AuthorizationExpectation,
) -> int:
    size = expectation.authorization_text_size
    if size is None:
        raise CrewChiefError(
            "version-2 authorization requires an expected authorization text size"
        )
    return size


def _expected_subject(expectation: AuthorizationExpectation) -> dict[str, Any]:
    return {
        "head_commit": expectation.subject_head,
        "package": {
            "size": expectation.package_size,
            "sha256": expectation.package_sha256,
        },
        "service_schema": {
            "size": expectation.service_schema_size,
            "sha256": expectation.service_schema_sha256,
        },
        "audit_id": expectation.audit_id,
        "envelope_id": expectation.envelope_id,
        "package_expires_at": expectation.package_expires_at,
    }


def _expected_authorization(
    expectation: AuthorizationExpectation,
) -> dict[str, Any]:
    return {
        "ordinary_bootstrap_invocations": (expectation.ordinary_bootstrap_invocations),
        "conditional_crew_chief_fixture_audits": (
            expectation.conditional_crew_chief_fixture_audits
        ),
        "automatic_retries_permitted": expectation.automatic_retries_permitted,
    }


def create_authorization_receipt(
    expectation: AuthorizationExpectation,
    *,
    authorization_text: str,
    authorized_at: datetime,
    expires_at: datetime,
    authority_context: AuthorizationContext | None = None,
) -> dict[str, Any]:
    """Record an explicit approval; calling this function does not grant it."""
    _validate_expectation(expectation)
    if not isinstance(authorization_text, str) or not authorization_text:
        raise CrewChiefError("complete Maverick authorization text is required")
    authorization_bytes = authorization_text.encode("utf-8")
    if len(authorization_bytes) != _required_authorization_text_size(expectation):
        raise CrewChiefError("authorization text does not match its approved size")
    if sha256_bytes(authorization_bytes) != (expectation.authorization_text_sha256):
        raise CrewChiefError("authorization text does not match its approved hash")
    authorized = clock_value(lambda: authorized_at)
    expiration = clock_value(lambda: expires_at)
    package_expiration = parse_time(expectation.package_expires_at)
    if expiration <= authorized:
        raise CrewChiefError("authorization receipt must expire after authorization")
    if expiration > package_expiration:
        raise CrewChiefError("authorization receipt cannot outlive the package")
    try:
        authority = authority_record(authority_context, authorization_bytes)
    except AuthorityContextError as error:
        raise CrewChiefError(str(error)) from error
    receipt: dict[str, Any] = {
        "schema_version": "2.0",
        "receipt_type": "maverick_package_authorization",
        "canary": CANARY,
        "authority": authority,
        "subject": _expected_subject(expectation),
        "authorized_scope": _expected_authorization(expectation),
        "authorized_at": authorized.isoformat().replace("+00:00", "Z"),
        "expires_at": expiration.isoformat().replace("+00:00", "Z"),
    }
    receipt["receipt_id"] = sha256_bytes(canonical_json_bytes(receipt))
    validate_authorization_receipt(
        receipt,
        expectation,
        clock=lambda: authorized,
    )
    return receipt


def validate_authorization_receipt(
    receipt: dict[str, Any],
    expectation: AuthorizationExpectation,
    *,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Validate integrity and binding after an external authorization decision."""
    _validate_expectation(expectation)
    if not isinstance(receipt, dict):
        raise CrewChiefError("authorization receipt must be a JSON object")
    schema_version = receipt.get("schema_version")
    if schema_version == "1.0":
        validate_instance("authorization-receipt-v1.schema.json", receipt)
    elif schema_version == "2.0":
        validate_instance("authorization-receipt-v2.schema.json", receipt)
    else:
        raise CrewChiefError("authorization receipt schema version is unsupported")
    unsigned = dict(receipt)
    receipt_id = unsigned.pop("receipt_id")
    if sha256_bytes(canonical_json_bytes(unsigned)) != receipt_id:
        raise CrewChiefError("authorization receipt ID does not match its content")
    if schema_version == "1.0":
        if receipt["authority"] != {
            "identity": "Maverick",
            "authorization_text_sha256": expectation.authorization_text_sha256,
        }:
            raise CrewChiefError("authorization receipt authority is mismatched")
        authorized_scope = receipt["authorization"]
    else:
        authorization_text_size = _required_authorization_text_size(expectation)
        try:
            validate_authority_record(
                receipt["authority"],
                authorization_text_sha256=expectation.authorization_text_sha256,
                authorization_text_size=authorization_text_size,
            )
        except AuthorityContextError as error:
            raise CrewChiefError(str(error)) from error
        authorized_scope = receipt["authorized_scope"]
    if receipt["subject"] != _expected_subject(expectation):
        raise CrewChiefError("authorization receipt subject is mismatched")
    if authorized_scope != _expected_authorization(expectation):
        raise CrewChiefError("authorization receipt invocation scope is mismatched")
    authorized_at = parse_time(receipt["authorized_at"])
    expires_at = parse_time(receipt["expires_at"])
    if expires_at <= authorized_at:
        raise CrewChiefError("authorization receipt expiration is invalid")
    if expires_at > parse_time(expectation.package_expires_at):
        raise CrewChiefError("authorization receipt outlives its package")
    current = clock_value(clock)
    if current < authorized_at:
        raise CrewChiefError("authorization receipt is not yet valid")
    if current >= expires_at:
        raise CrewChiefError("authorization receipt expired")
    return receipt


def _absolute_binding(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_file():
        raise CrewChiefError(f"bootstrap control must be a regular file: {path}")
    return {
        "path": str(resolved),
        "size": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def _verify_binding(binding: dict[str, Any], label: str) -> Path:
    if not isinstance(binding, dict) or set(binding) != {"path", "size", "sha256"}:
        raise CrewChiefError(f"{label} binding is malformed")
    path = Path(binding["path"])
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise CrewChiefError(f"{label} binding is missing")
    if path.stat().st_size != binding["size"]:
        raise CrewChiefError(f"{label} binding size changed")
    if sha256_file(path) != binding["sha256"]:
        raise CrewChiefError(f"{label} binding hash changed")
    return path


def _validate_subject_files(
    package_path: Path,
    schema_path: Path,
    expectation: AuthorizationExpectation,
) -> None:
    package = _absolute_binding(package_path)
    schema = _absolute_binding(schema_path)
    if (package["size"], package["sha256"]) != (
        expectation.package_size,
        expectation.package_sha256,
    ):
        raise CrewChiefError("approved bootstrap package binding is mismatched")
    if (schema["size"], schema["sha256"]) != (
        expectation.service_schema_size,
        expectation.service_schema_sha256,
    ):
        raise CrewChiefError("approved service-schema binding is mismatched")


def _detect_bootstrap_capabilities() -> CodexCapabilities:
    capabilities = detect_codex_capabilities()
    executable = Path(capabilities.executable).resolve()
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise CrewChiefError("approved Codex executable is unavailable")
    return replace(capabilities, executable=str(executable))


def _capabilities_from_record(value: Any) -> CodexCapabilities:
    expected = {
        "executable",
        "version",
        "exec_flags",
        "features",
        "shell_tool_control",
        "custom_agent_selector",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise CrewChiefError("bootstrap capability evidence is malformed")
    if (
        not isinstance(value["executable"], str)
        or not value["executable"]
        or not isinstance(value["version"], str)
        or not value["version"]
        or not isinstance(value["exec_flags"], list)
        or any(not isinstance(item, str) or not item for item in value["exec_flags"])
        or not isinstance(value["features"], list)
        or any(not isinstance(item, str) or not item for item in value["features"])
        or not isinstance(value["shell_tool_control"], bool)
        or not isinstance(value["custom_agent_selector"], bool)
    ):
        raise CrewChiefError("bootstrap capability evidence is malformed")
    return CodexCapabilities(
        executable=value["executable"],
        version=value["version"],
        exec_flags=tuple(value["exec_flags"]),
        features=tuple(value["features"]),
        shell_tool_control=value["shell_tool_control"],
        custom_agent_selector=value["custom_agent_selector"],
    )


def _command_sha256(argv: list[str]) -> str:
    return sha256_bytes(canonical_json_bytes(argv))


def _validate_bootstrap_command_contract(
    invocation: dict[str, Any],
    workspace: Path,
    schema_path: Path,
) -> list[str]:
    contract = invocation.get("command_contract")
    if not isinstance(contract, dict) or set(contract) != {
        "schema_version",
        "role",
        "capabilities",
        "approved_executable",
        "argv_sha256",
    }:
        raise CrewChiefError("bootstrap command contract is malformed")
    if contract["schema_version"] != _COMMAND_CONTRACT_VERSION:
        raise CrewChiefError("bootstrap command contract version is unsupported")
    if contract["role"] != _BOOTSTRAP_ROLE:
        raise CrewChiefError("bootstrap command role is mismatched")
    prepared_capabilities = _capabilities_from_record(contract["capabilities"])
    current_capabilities = _detect_bootstrap_capabilities()
    if asdict(current_capabilities) != asdict(prepared_capabilities):
        raise CrewChiefError("bootstrap capability evidence changed before launch")
    executable = _verify_binding(
        contract["approved_executable"], "approved Codex executable"
    )
    if executable != Path(current_capabilities.executable):
        raise CrewChiefError("approved Codex executable binding is mismatched")
    report_output = workspace / "output" / "bootstrap-report.json"
    expected_argv = build_ordinary_bootstrap_launch_command(
        current_capabilities,
        workspace,
        schema_path,
        report_output,
    )
    argv = invocation.get("argv")
    if argv != expected_argv:
        raise CrewChiefError("bootstrap command differs from the canonical contract")
    if contract["argv_sha256"] != _command_sha256(expected_argv):
        raise CrewChiefError("bootstrap command binding is mismatched")
    if "--agent" in expected_argv or "crew_chief" in expected_argv:
        raise CrewChiefError("ordinary bootstrap command selected Crew Chief")
    return expected_argv


def _composite_payload(package: bytes, receipt: bytes) -> bytes:
    try:
        package_text = package.decode("utf-8")
        receipt_text = receipt.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CrewChiefError("bootstrap package and receipt must be UTF-8") from error
    receipt_sha = sha256_bytes(receipt)
    package_sha = sha256_bytes(package)
    rendered = "\n".join(
        [
            CANARY,
            "",
            "FROZEN PACKAGE-BOUND INVOCATION CONTROL",
            "Validate the authorization receipt before reviewing the package.",
            "Return BLOCKED if it is absent, malformed, expired, altered,",
            "or mismatched. A valid receipt records the exact-package approval",
            "gate even when the older frozen mission snapshot says approval was",
            "pending. This is an ordinary Codex review, not a Crew Chief audit.",
            "The trusted local wrapper supplies a provenance attestation; the",
            "receipt is tamper-evident and does not independently prove identity.",
            "",
            (
                f"=== BEGIN FROZEN {_CONTROL_NAME} size={len(receipt)} "
                f"sha256={receipt_sha} ==="
            ),
            receipt_text.rstrip("\n"),
            f"=== END FROZEN {_CONTROL_NAME} ===",
            "",
            (
                f"=== BEGIN APPROVED {_PACKAGE_NAME} size={len(package)} "
                f"sha256={package_sha} ==="
            ),
            package_text.rstrip("\n"),
            f"=== END APPROVED {_PACKAGE_NAME} ===",
            "",
        ]
    )
    return rendered.encode("utf-8")


def prepare_authorized_bootstrap_invocation(
    repository: Path,
    package_path: Path,
    service_schema_path: Path,
    receipt_path: Path,
    workspace: Path,
    *,
    expectation: AuthorizationExpectation,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Freeze one receipt-bound composite without invoking a process."""
    _validate_expectation(expectation)
    _validate_subject_files(package_path, service_schema_path, expectation)
    receipt = read_json(receipt_path)
    validate_authorization_receipt(receipt, expectation, clock=clock)
    source_bindings = {
        "package": _absolute_binding(package_path),
        "service_schema": _absolute_binding(service_schema_path),
        "authorization_receipt": _absolute_binding(receipt_path),
    }
    target = new_external_directory(
        repository, workspace, prefix="wingman-bootstrap-review-"
    )
    frozen = target / "frozen"
    package_copy = frozen / _PACKAGE_NAME
    schema_copy = frozen / _SCHEMA_NAME
    receipt_copy = frozen / _CONTROL_NAME
    workspace_bindings = [
        copy_bound_file(package_path, package_copy, f"frozen/{_PACKAGE_NAME}"),
        copy_bound_file(service_schema_path, schema_copy, f"frozen/{_SCHEMA_NAME}"),
        copy_bound_file(receipt_path, receipt_copy, f"frozen/{_CONTROL_NAME}"),
    ]
    prompt_path = target / _PROMPT_NAME
    atomic_write(
        prompt_path,
        _composite_payload(package_copy.read_bytes(), receipt_copy.read_bytes()),
    )
    workspace_bindings.append(
        {
            "path": _PROMPT_NAME,
            "size": prompt_path.stat().st_size,
            "sha256": sha256_file(prompt_path),
        }
    )
    _validate_subject_files(package_path, service_schema_path, expectation)
    capabilities = _detect_bootstrap_capabilities()
    executable_binding = _absolute_binding(Path(capabilities.executable))
    argv = build_ordinary_bootstrap_launch_command(
        capabilities,
        target,
        schema_copy,
        target / "output" / "bootstrap-report.json",
    )
    invocation = {
        "schema_version": "1.0",
        "audit_id": expectation.audit_id,
        "envelope_id": expectation.envelope_id,
        "subject_head": expectation.subject_head,
        "workspace": str(target),
        "argv": argv,
        "command_contract": {
            "schema_version": _COMMAND_CONTRACT_VERSION,
            "role": _BOOTSTRAP_ROLE,
            "capabilities": asdict(capabilities),
            "approved_executable": executable_binding,
            "argv_sha256": _command_sha256(argv),
        },
        "authorization_expectation": asdict(expectation),
        "source_bindings": source_bindings,
        "workspace_bindings": workspace_bindings,
        "prompt_path": str(prompt_path),
        "run_record_path": str(target / "output" / "bootstrap-run-record.json"),
        "authorized_invocation_counts": _expected_authorization(expectation),
        "model_invocation_attempted": False,
    }
    write_canonical_json(target / "invocation.json", invocation)
    return invocation


def _verify_workspace_binding(workspace: Path, binding: dict[str, Any]) -> Path:
    if not isinstance(binding, dict) or set(binding) != {"path", "size", "sha256"}:
        raise CrewChiefError("bootstrap workspace binding is malformed")
    relative = Path(binding["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise CrewChiefError("bootstrap workspace binding escapes its root")
    path = workspace / relative
    resolved = path.resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as error:
        raise CrewChiefError("bootstrap workspace binding escapes its root") from error
    _verify_binding({**binding, "path": str(resolved)}, "bootstrap workspace")
    return resolved


def _consume_receipt(receipt_path: Path, receipt_id: str) -> Path:
    marker = receipt_path.with_name(f".{receipt_path.name}.{receipt_id}.consumed.json")
    try:
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise CrewChiefError("authorization receipt was already consumed") from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(
            canonical_json_bytes(
                {"receipt_id": receipt_id, "automatic_retries_permitted": False}
            )
            + b"\n"
        )
        handle.flush()
        os.fsync(handle.fileno())
    return marker


def execute_authorized_bootstrap(
    invocation_path: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    timeout_seconds: int = 3600,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Execute exactly once after all deterministic receipt checks pass."""
    invocation = read_json(invocation_path)
    if not isinstance(invocation, dict):
        raise CrewChiefError("bootstrap invocation must be a JSON object")
    if invocation.get("model_invocation_attempted") is not False:
        raise CrewChiefError("bootstrap invocation has an invalid execution state")
    expectation = AuthorizationExpectation.from_dict(
        invocation.get("authorization_expectation")
    )
    if (
        invocation.get("audit_id") != expectation.audit_id
        or invocation.get("envelope_id") != expectation.envelope_id
    ):
        raise CrewChiefError("bootstrap invocation identifiers are mismatched")
    if invocation.get("subject_head") != expectation.subject_head:
        raise CrewChiefError("bootstrap invocation HEAD is mismatched")
    if invocation.get("authorized_invocation_counts") != _expected_authorization(
        expectation
    ):
        raise CrewChiefError("bootstrap invocation count control is mismatched")
    workspace = Path(invocation.get("workspace", "")).resolve()
    if invocation_path.resolve() != workspace / "invocation.json":
        raise CrewChiefError("bootstrap invocation path is mismatched")
    source_bindings = invocation.get("source_bindings")
    if not isinstance(source_bindings, dict) or set(source_bindings) != {
        "package",
        "service_schema",
        "authorization_receipt",
    }:
        raise CrewChiefError("bootstrap source bindings are malformed")
    package_path = _verify_binding(source_bindings["package"], "bootstrap package")
    schema_path = _verify_binding(
        source_bindings["service_schema"], "bootstrap service schema"
    )
    receipt_path = _verify_binding(
        source_bindings["authorization_receipt"], "authorization receipt"
    )
    _validate_subject_files(package_path, schema_path, expectation)
    receipt = read_json(receipt_path)
    validate_authorization_receipt(receipt, expectation, clock=clock)
    bindings = invocation.get("workspace_bindings")
    if not isinstance(bindings, list) or len(bindings) != 4:
        raise CrewChiefError("bootstrap workspace bindings are malformed")
    resolved = {
        binding["path"]: _verify_workspace_binding(workspace, binding)
        for binding in bindings
    }
    receipt_copy = resolved[f"frozen/{_CONTROL_NAME}"]
    if receipt_copy.read_bytes() != receipt_path.read_bytes():
        raise CrewChiefError("frozen authorization receipt differs from its source")
    package_copy = resolved[f"frozen/{_PACKAGE_NAME}"]
    if package_copy.read_bytes() != package_path.read_bytes():
        raise CrewChiefError("frozen bootstrap package differs from its source")
    schema_copy = resolved[f"frozen/{_SCHEMA_NAME}"]
    if schema_copy.read_bytes() != schema_path.read_bytes():
        raise CrewChiefError("frozen service schema differs from its source")
    prompt_path = resolved[_PROMPT_NAME]
    if Path(invocation.get("prompt_path", "")).resolve() != prompt_path:
        raise CrewChiefError("bootstrap prompt path is mismatched")
    run_record_path = Path(invocation.get("run_record_path", "")).resolve()
    if run_record_path != workspace / "output" / "bootstrap-run-record.json":
        raise CrewChiefError("bootstrap run-record path is mismatched")
    expected_prompt = _composite_payload(
        package_copy.read_bytes(), receipt_copy.read_bytes()
    )
    if prompt_path.read_bytes() != expected_prompt:
        raise CrewChiefError("bootstrap composite payload is mismatched")
    argv = _validate_bootstrap_command_contract(
        invocation,
        workspace,
        schema_copy,
    )
    _consume_receipt(receipt_path, receipt["receipt_id"])
    result = runner(
        list(argv),
        input=prompt_path.read_text(encoding="utf-8"),
        cwd=workspace,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    stdout_path = workspace / "output" / "codex-stdout.log"
    stderr_path = workspace / "output" / "codex-stderr.log"
    atomic_write(stdout_path, result.stdout.encode("utf-8"))
    atomic_write(stderr_path, redact_text(result.stderr).encode("utf-8"))
    run_record = {
        "schema_version": "1.0",
        "audit_id": expectation.audit_id,
        "envelope_id": expectation.envelope_id,
        "subject_head": expectation.subject_head,
        "authorization_receipt": source_bindings["authorization_receipt"],
        "frozen_authorization_receipt": _absolute_binding(receipt_copy),
        "composite_payload": _absolute_binding(prompt_path),
        "authorized_invocation_counts": _expected_authorization(expectation),
        "command_contract": invocation["command_contract"],
        "invocation_attempted": True,
        "invocation_completed": True,
        "returncode": result.returncode,
        "automatic_retry_attempts": 0,
        "stdout": _absolute_binding(stdout_path),
        "stderr": _absolute_binding(stderr_path),
    }
    write_canonical_json(run_record_path, run_record)
    return run_record
