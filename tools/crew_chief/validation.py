"""JSON Schema and policy validation for Crew Chief outputs."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from tools.crew_chief.core import (
    CrewChiefError,
    SCHEMA_NAMES,
    canonical_json_bytes,
    sha256_bytes,
)


SCHEMA_ROOT = Path(__file__).resolve().parent / "schemas"


def load_schemas() -> dict[str, dict[str, Any]]:
    schemas = {}
    for name in SCHEMA_NAMES:
        path = SCHEMA_ROOT / name
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CrewChiefError(
                f"Crew Chief schema is unreadable: {path}: {error}"
            ) from error
        Draft202012Validator.check_schema(value)
        schemas[name] = value
    return schemas


def _validator(name: str) -> Draft202012Validator:
    schemas = load_schemas()
    registry = Registry()
    for schema in schemas.values():
        registry = registry.with_resource(
            schema["$id"], Resource.from_contents(schema)
        )
    return Draft202012Validator(
        schemas[name], registry=registry, format_checker=FormatChecker()
    )


def validate_instance(name: str, value: Any) -> None:
    errors = sorted(
        _validator(name).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        details = []
        for error in errors:
            location = (
                ".".join(str(part) for part in error.absolute_path) or "<root>"
            )
            details.append(f"{location}: {error.message}")
        raise CrewChiefError("schema validation failed: " + "; ".join(details))


def _expected_verdict(report: dict[str, Any]) -> str:
    if report["blocked_reasons"]:
        return "BLOCKED"
    findings = report["findings"]
    if not findings:
        return "PASS"
    if any(
        finding["severity"] in {"critical", "high", "medium"}
        or finding["blocking"]
        for finding in findings
    ):
        return "FAIL"
    return "PASS_WITH_ADVISORIES"


def validate_report(envelope: dict[str, Any], report: dict[str, Any]) -> None:
    validate_instance("report-v1.schema.json", report)
    if report["audit_id"] != envelope["audit_id"]:
        raise CrewChiefError("report audit_id does not match the envelope")
    if report["envelope_id"] != envelope["envelope_id"]:
        raise CrewChiefError("report envelope_id does not match the envelope")
    finding_ids = [finding["finding_id"] for finding in report["findings"]]
    if len(finding_ids) != len(set(finding_ids)):
        raise CrewChiefError("finding IDs must be unique")
    for finding in report["findings"]:
        severity = finding["severity"]
        blocking = finding["blocking"]
        if severity in {"critical", "high"} and not blocking:
            raise CrewChiefError(f"{severity} findings must be blocking")
        if severity in {"low", "advisory"} and blocking:
            raise CrewChiefError(f"{severity} findings must not be blocking")
        if severity == "medium" and not finding.get("blocking_rationale"):
            raise CrewChiefError("medium findings require a blocking rationale")
        for evidence in finding["evidence"]:
            if (
                evidence["kind"] == "source"
                and evidence["line_end"] < evidence["line_start"]
            ):
                raise CrewChiefError("source evidence line range is invalid")
    expected = _expected_verdict(report)
    if report["verdict"] != expected:
        raise CrewChiefError(
            f"report verdict must be {expected}, observed {report['verdict']}"
        )


def validate_reconciliation(
    package: dict[str, Any], report: dict[str, Any]
) -> None:
    validate_instance("reconciliation-v1.schema.json", package)
    expected_hash = package["package_hash"]
    payload = copy.deepcopy(package)
    payload.pop("package_hash")
    if sha256_bytes(canonical_json_bytes(payload)) != expected_hash:
        raise CrewChiefError("reconciliation package hash is invalid")
    report_hash = sha256_bytes(canonical_json_bytes(report))
    if package["report_hash"] != report_hash:
        raise CrewChiefError("reconciliation report hash is invalid")
    findings = {item["finding_id"]: item for item in report["findings"]}
    dispositions = package["dispositions"]
    ids = [item["finding_id"] for item in dispositions]
    if len(ids) != len(set(ids)):
        raise CrewChiefError("each finding must receive exactly one disposition")
    if set(ids) != set(findings):
        raise CrewChiefError("reconciliation must cover every finding exactly once")
    for item in dispositions:
        disposition = item["disposition"]
        if disposition == "resolved":
            if not item.get("correction_evidence") or not item.get(
                "validation_results"
            ):
                raise CrewChiefError(
                    "resolved dispositions require correction evidence and "
                    "validation results"
                )
        elif disposition == "disputed_with_evidence":
            if not item.get("counter_evidence") or not item.get("reasoning"):
                raise CrewChiefError(
                    "disputed dispositions require exact counter-evidence and "
                    "reasoning"
                )
        elif disposition == "escalated_to_maverick":
            required = ("unresolved_issue", "impact", "decision_requested")
            if any(not item.get(field) for field in required):
                raise CrewChiefError(
                    "escalated dispositions require issue, impact, and decision "
                    "requested"
                )
    expected_ready = all(
        not findings[item["finding_id"]]["blocking"]
        or item["disposition"] == "resolved"
        for item in dispositions
    )
    if package["reconciliation_complete"] is not True:
        raise CrewChiefError(
            "complete finding coverage must set reconciliation_complete"
        )
    if package["approval_ready"] != expected_ready:
        raise CrewChiefError(
            "approval_ready disagrees with blocking dispositions"
        )
