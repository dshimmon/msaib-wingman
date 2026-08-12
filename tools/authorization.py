"""Structured authority provenance for repository governance receipts."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any


MAVERICK_PRINCIPAL_ID = "Maverick"
CODEX_EXECUTOR_ID = "Codex"
MISSION_CONTROL_DISPATCHER_ID = "Mission Control"
AUTHORIZATION_EVIDENCE_TYPES = frozenset(
    {
        "caller_attested_task_interaction",
        "caller_attested_explicit_approval",
        "caller_attested_standing_delegation",
    }
)
EXECUTION_ROUTES = frozenset({"direct_codex", "mission_control"})
ACTION_SPECIFIC_APPROVAL = "action_specific_explicit"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AuthorityContextError(ValueError):
    """Authority provenance is missing, unknown, or insufficient."""


@dataclass(frozen=True)
class AuthorizationContext:
    """Authority facts asserted by the trusted local receipt caller."""

    authorizing_principal_id: str
    evidence_type: str
    evidence_reference: str
    approval_type: str
    execution_route: str
    executor_id: str


def _validate_context(context: AuthorizationContext | None) -> AuthorizationContext:
    if not isinstance(context, AuthorizationContext):
        raise AuthorityContextError("explicit authorization context is required")
    if context.authorizing_principal_id != MAVERICK_PRINCIPAL_ID:
        raise AuthorityContextError("authorizing principal is unknown")
    if (
        not isinstance(context.evidence_type, str)
        or context.evidence_type not in AUTHORIZATION_EVIDENCE_TYPES
    ):
        raise AuthorityContextError("authorization evidence type is unknown")
    if (
        not isinstance(context.evidence_reference, str)
        or not context.evidence_reference.strip()
        or len(context.evidence_reference) > 512
    ):
        raise AuthorityContextError("authorization evidence reference is required")
    if context.approval_type != ACTION_SPECIFIC_APPROVAL:
        raise AuthorityContextError(
            "action-specific explicit approval evidence is required"
        )
    if (
        not isinstance(context.execution_route, str)
        or context.execution_route not in EXECUTION_ROUTES
    ):
        raise AuthorityContextError("execution route is unknown")
    if context.executor_id != CODEX_EXECUTOR_ID:
        raise AuthorityContextError("receipt executor is unknown")
    return context


def authority_statement(context: AuthorizationContext) -> str:
    """Render receipt wording only from validated structured provenance."""
    context = _validate_context(context)
    evidence = {
        "caller_attested_task_interaction": "a task interaction",
        "caller_attested_explicit_approval": "explicit approval evidence",
        "caller_attested_standing_delegation": "a recorded standing delegation",
    }[context.evidence_type]
    prefix = (
        "Trusted local caller attests that "
        f"{MAVERICK_PRINCIPAL_ID} authorized this scope through {evidence}; "
    )
    if context.execution_route == "mission_control":
        return (
            prefix
            + f"dispatched through {MISSION_CONTROL_DISPATCHER_ID}; "
            + f"executed by {CODEX_EXECUTOR_ID}."
        )
    return prefix + f"executed directly by {CODEX_EXECUTOR_ID}."


def authority_record(
    context: AuthorizationContext | None,
    authorization_text: bytes,
) -> dict[str, Any]:
    """Bind explicit evidence bytes to an authority and execution route."""
    context = _validate_context(context)
    if not isinstance(authorization_text, bytes) or not authorization_text:
        raise AuthorityContextError("complete authorization evidence is required")
    dispatcher = (
        MISSION_CONTROL_DISPATCHER_ID
        if context.execution_route == "mission_control"
        else None
    )
    return {
        "provenance_attestation": {
            "model": "trusted_local_caller",
            "independent_origin_verification": False,
        },
        "authorizing_principal": {
            "principal_id": context.authorizing_principal_id,
        },
        "authorization_evidence": {
            "type": context.evidence_type,
            "reference": context.evidence_reference,
            "approval_type": context.approval_type,
            "asserted_authorizing_principal_id": context.authorizing_principal_id,
            "authorization_text_sha256": hashlib.sha256(authorization_text).hexdigest(),
            "authorization_text_size": len(authorization_text),
        },
        "execution_route": {
            "type": context.execution_route,
            "dispatcher": dispatcher,
        },
        "executor": {"component_id": context.executor_id},
        "statement": authority_statement(context),
    }


def validate_authority_record(
    record: Any,
    *,
    authorization_text_sha256: str | None = None,
    authorization_text_size: int | None = None,
) -> AuthorizationContext:
    """Validate cross-field provenance that JSON Schema cannot derive."""
    if not isinstance(record, dict) or set(record) != {
        "provenance_attestation",
        "authorizing_principal",
        "authorization_evidence",
        "execution_route",
        "executor",
        "statement",
    }:
        raise AuthorityContextError("authorization provenance is malformed")
    attestation = record.get("provenance_attestation")
    principal = record.get("authorizing_principal")
    evidence = record.get("authorization_evidence")
    route = record.get("execution_route")
    executor = record.get("executor")
    if not all(
        isinstance(value, dict)
        for value in (attestation, principal, evidence, route, executor)
    ):
        raise AuthorityContextError("authorization provenance is malformed")
    if attestation != {
        "model": "trusted_local_caller",
        "independent_origin_verification": False,
    }:
        raise AuthorityContextError("authorization provenance attestation is malformed")
    if set(principal) != {"principal_id"}:
        raise AuthorityContextError("authorizing principal is malformed")
    if set(evidence) != {
        "type",
        "reference",
        "approval_type",
        "asserted_authorizing_principal_id",
        "authorization_text_sha256",
        "authorization_text_size",
    }:
        raise AuthorityContextError("authorization evidence is malformed")
    if set(route) != {"type", "dispatcher"}:
        raise AuthorityContextError("execution route is malformed")
    if set(executor) != {"component_id"}:
        raise AuthorityContextError("receipt executor is malformed")
    context = _validate_context(
        AuthorizationContext(
            authorizing_principal_id=principal.get("principal_id"),
            evidence_type=evidence.get("type"),
            evidence_reference=evidence.get("reference"),
            approval_type=evidence.get("approval_type"),
            execution_route=route.get("type"),
            executor_id=executor.get("component_id"),
        )
    )
    if (
        evidence.get("asserted_authorizing_principal_id")
        != context.authorizing_principal_id
    ):
        raise AuthorityContextError(
            "authorization evidence attestation is inconsistent"
        )
    digest = evidence.get("authorization_text_sha256")
    size = evidence.get("authorization_text_size")
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise AuthorityContextError("authorization evidence hash is invalid")
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        raise AuthorityContextError("authorization evidence size is invalid")
    if authorization_text_sha256 is not None and digest != authorization_text_sha256:
        raise AuthorityContextError("authorization evidence hash is mismatched")
    if authorization_text_size is not None and size != authorization_text_size:
        raise AuthorityContextError("authorization evidence size is mismatched")
    expected_dispatcher = (
        MISSION_CONTROL_DISPATCHER_ID
        if context.execution_route == "mission_control"
        else None
    )
    if route.get("dispatcher") != expected_dispatcher:
        raise AuthorityContextError("execution dispatcher is inconsistent")
    if record.get("statement") != authority_statement(context):
        raise AuthorityContextError("authorization statement is inconsistent")
    return context
