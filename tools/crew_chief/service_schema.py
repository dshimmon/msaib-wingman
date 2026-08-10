"""Strict Structured Outputs projection and offline compatibility checks."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from tools.crew_chief.core import CrewChiefError, read_json


_SERVICE_KEYS = frozenset(
    {
        "$defs",
        "$ref",
        "additionalProperties",
        "anyOf",
        "const",
        "enum",
        "items",
        "properties",
        "required",
        "type",
    }
)
_UNSUPPORTED_COMPOSITION = frozenset(
    {
        "allOf",
        "dependentRequired",
        "dependentSchemas",
        "else",
        "if",
        "not",
        "then",
    }
)


def bundle_report_schema(schema_root: Path) -> dict[str, Any]:
    """Embed finding definitions and replace the canonical external reference."""
    report = read_json(schema_root / "report-v1.schema.json")
    finding = read_json(schema_root / "finding-v1.schema.json")
    if not isinstance(report, dict) or not isinstance(finding, dict):
        raise CrewChiefError("Crew Chief canonical report schemas are invalid")
    finding.pop("$schema", None)
    finding.pop("$id", None)
    definitions = finding.pop("$defs", None)
    if not isinstance(definitions, dict):
        raise CrewChiefError("Crew Chief finding definitions are invalid")
    report["$defs"] = {**definitions, "finding": finding}
    try:
        report["properties"]["findings"]["items"] = {
            "$ref": "#/$defs/finding"
        }
    except (KeyError, TypeError) as error:
        raise CrewChiefError("Crew Chief canonical report schema is invalid") from error
    return report


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise CrewChiefError(f"service schema contains an unsupported value: {value!r}")


def _declared_types(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list) and value and all(
        isinstance(item, str) for item in value
    ):
        return set(value)
    raise CrewChiefError("service schema has an invalid explicit type")


def _types_for_values(values: list[Any]) -> list[str]:
    observed = {_json_type(value) for value in values}
    if observed == {"integer", "number"}:
        observed = {"number"}
    return sorted(observed)


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(schema)
    if "type" in projected:
        declared = _declared_types(projected["type"])
        declared.add("null")
        projected["type"] = sorted(declared)
        if "enum" in projected and None not in projected["enum"]:
            projected["enum"] = [*projected["enum"], None]
        return projected
    alternatives = projected.get("anyOf")
    if isinstance(alternatives, list):
        return {
            "anyOf": [*copy.deepcopy(alternatives), {"type": "null"}]
        }
    return {"anyOf": [projected, {"type": "null"}]}


def _project(node: Any, path: str) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise CrewChiefError(f"canonical schema node is not an object at {path}")
    forbidden = sorted(_UNSUPPORTED_COMPOSITION.intersection(node))
    if forbidden:
        raise CrewChiefError(
            f"canonical schema uses unsupported composition at {path}: {forbidden}"
        )
    if "oneOf" in node and "anyOf" in node:
        raise CrewChiefError(f"canonical schema mixes oneOf and anyOf at {path}")
    if "$ref" in node:
        reference = node["$ref"]
        if not isinstance(reference, str):
            raise CrewChiefError(f"canonical schema reference is invalid at {path}")
        return {"$ref": reference}

    projected: dict[str, Any] = {}
    if "type" in node:
        projected["type"] = copy.deepcopy(node["type"])
    if "const" in node:
        projected.setdefault("type", _json_type(node["const"]))
        projected["const"] = copy.deepcopy(node["const"])
    if "enum" in node:
        values = node["enum"]
        if not isinstance(values, list) or not values:
            raise CrewChiefError(f"canonical schema enum is invalid at {path}")
        inferred = _types_for_values(values)
        projected.setdefault("type", inferred[0] if len(inferred) == 1 else inferred)
        projected["enum"] = copy.deepcopy(values)

    alternatives = node.get("oneOf", node.get("anyOf"))
    if alternatives is not None:
        if not isinstance(alternatives, list) or len(alternatives) < 2:
            raise CrewChiefError(f"canonical schema alternatives are invalid at {path}")
        projected["anyOf"] = [
            _project(item, f"{path}.anyOf[{index}]")
            for index, item in enumerate(alternatives)
        ]

    definitions = node.get("$defs")
    if definitions is not None:
        if not isinstance(definitions, dict):
            raise CrewChiefError(f"canonical schema definitions are invalid at {path}")
        projected["$defs"] = {
            name: _project(value, f"{path}.$defs.{name}")
            for name, value in definitions.items()
        }

    if node.get("type") == "object":
        properties = node.get("properties")
        required = node.get("required")
        if not isinstance(properties, dict) or not isinstance(required, list):
            raise CrewChiefError(f"canonical object schema is incomplete at {path}")
        required_set = set(required)
        if len(required_set) != len(required) or required_set - set(properties):
            raise CrewChiefError(f"canonical required fields are invalid at {path}")
        projected_properties = {}
        for name, value in properties.items():
            child = _project(value, f"{path}.properties.{name}")
            projected_properties[name] = (
                child if name in required_set else _nullable(child)
            )
        projected["properties"] = projected_properties
        projected["required"] = list(properties)
        projected["additionalProperties"] = False
    elif node.get("type") == "array":
        if "items" not in node:
            raise CrewChiefError(f"canonical array schema lacks items at {path}")
        projected["items"] = _project(node["items"], f"{path}.items")
    return projected


def _resolve_local_reference(schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise CrewChiefError(
            f"service schema reference must be local: {reference!r}"
        )
    current: Any = schema
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise CrewChiefError(
                f"service schema reference does not resolve: {reference!r}"
            )
        current = current[part]
    if not isinstance(current, dict):
        raise CrewChiefError(
            f"service schema reference is not an object: {reference!r}"
        )
    return current


def _type_accepts(declared: set[str], value: Any) -> bool:
    observed = _json_type(value)
    return observed in declared or observed == "integer" and "number" in declared


def _check_node(root: dict[str, Any], node: Any, path: str) -> None:
    if not isinstance(node, dict):
        raise CrewChiefError(f"service schema node is not an object at {path}")
    unsupported = sorted(set(node) - _SERVICE_KEYS)
    if unsupported:
        raise CrewChiefError(
            f"service schema uses unsupported keywords at {path}: {unsupported}"
        )
    if "$ref" in node:
        if set(node) != {"$ref"} or not isinstance(node["$ref"], str):
            raise CrewChiefError(f"service schema reference is malformed at {path}")
        _resolve_local_reference(root, node["$ref"])
        return

    declared: set[str] | None = None
    if "type" in node:
        declared = _declared_types(node["type"])
    if "const" in node:
        if declared is None or not _type_accepts(declared, node["const"]):
            raise CrewChiefError(
                f"service schema const lacks an explicit matching type at {path}"
            )
    if "enum" in node:
        values = node["enum"]
        if (
            declared is None
            or not isinstance(values, list)
            or not values
            or any(not _type_accepts(declared, value) for value in values)
        ):
            raise CrewChiefError(
                f"service schema enum lacks an explicit matching type at {path}"
            )

    alternatives = node.get("anyOf")
    if alternatives is not None:
        if not isinstance(alternatives, list) or len(alternatives) < 2:
            raise CrewChiefError(f"service schema anyOf is invalid at {path}")
        for index, child in enumerate(alternatives):
            _check_node(root, child, f"{path}.anyOf[{index}]")

    if declared is not None and "object" in declared:
        properties = node.get("properties")
        required = node.get("required")
        if not isinstance(properties, dict):
            raise CrewChiefError(f"service object lacks properties at {path}")
        if node.get("additionalProperties") is not False:
            raise CrewChiefError(
                f"service object lacks additionalProperties=false at {path}"
            )
        if (
            not isinstance(required, list)
            or len(required) != len(set(required))
            or set(required) != set(properties)
        ):
            raise CrewChiefError(
                f"service object does not require every property at {path}"
            )
        for name, child in properties.items():
            _check_node(root, child, f"{path}.properties.{name}")
    elif "properties" in node or "required" in node or "additionalProperties" in node:
        raise CrewChiefError(f"service object keywords lack object type at {path}")

    if declared is not None and "array" in declared:
        if "items" not in node:
            raise CrewChiefError(f"service array lacks items at {path}")
        _check_node(root, node["items"], f"{path}.items")
    elif "items" in node:
        raise CrewChiefError(f"service array items lack array type at {path}")

    definitions = node.get("$defs")
    if definitions is not None:
        if not isinstance(definitions, dict):
            raise CrewChiefError(f"service definitions are invalid at {path}")
        for name, child in definitions.items():
            _check_node(root, child, f"{path}.$defs.{name}")


def validate_service_schema(schema: dict[str, Any]) -> None:
    """Reject any final output schema outside OpenAI's strict supported subset."""
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise CrewChiefError(f"service schema is malformed: {error.message}") from error
    if schema.get("type") != "object" or "anyOf" in schema:
        raise CrewChiefError("service schema root must be one object")
    _check_node(schema, schema, "<root>")


def project_service_schema(canonical_schema: dict[str, Any]) -> dict[str, Any]:
    """Project a canonical schema to the strict service subset, then validate it."""
    try:
        Draft202012Validator.check_schema(canonical_schema)
    except SchemaError as error:
        raise CrewChiefError(f"canonical schema is malformed: {error.message}") from error
    projected = _project(canonical_schema, "<root>")
    validate_service_schema(projected)
    return projected


def bind_bootstrap_service_schema(
    canonical_schema: dict[str, Any],
    *,
    audit_id: str,
    envelope_id: str,
    reviewed_commit: str,
) -> dict[str, Any]:
    """Bind one ordinary-bootstrap schema to its exact frozen subject."""
    bound = copy.deepcopy(canonical_schema)
    properties = bound.get("properties", {})
    for name, value in (
        ("audit_id", audit_id),
        ("envelope_id", envelope_id),
        ("reviewed_commit", reviewed_commit),
    ):
        if name not in properties:
            raise CrewChiefError(f"bootstrap canonical schema lacks {name}")
        properties[name]["const"] = value
    return project_service_schema(bound)


def validate_service_instance(schema: dict[str, Any], value: Any) -> None:
    validate_service_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        details = [
            f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: "
            f"{error.message}"
            for error in errors
        ]
        raise CrewChiefError(
            "service output schema validation failed: " + "; ".join(details)
        )


def _schema_for_value(
    root: dict[str, Any], schema: dict[str, Any], value: Any
) -> dict[str, Any]:
    if "$ref" in schema:
        return _resolve_local_reference(root, schema["$ref"])
    alternatives = schema.get("oneOf", schema.get("anyOf"))
    if not isinstance(alternatives, list):
        return schema
    if value is None:
        for candidate in alternatives:
            if candidate.get("type") == "null":
                return candidate
    if isinstance(value, dict):
        for candidate in alternatives:
            candidate = _schema_for_value(root, candidate, value)
            kind = candidate.get("properties", {}).get("kind", {}).get("const")
            if kind is not None and value.get("kind") == kind:
                return candidate
    return alternatives[0]


def _normalize(
    value: Any, root: dict[str, Any], schema: dict[str, Any]
) -> Any:
    schema = _schema_for_value(root, schema, value)
    if value is None:
        return None
    if schema.get("type") == "object" and isinstance(value, dict):
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        normalized = {}
        for name, child in value.items():
            if name not in properties:
                normalized[name] = child
            elif child is None and name not in required:
                continue
            else:
                normalized[name] = _normalize(child, root, properties[name])
        return normalized
    if schema.get("type") == "array" and isinstance(value, list):
        return [_normalize(item, root, schema["items"]) for item in value]
    return value


def normalize_service_output(value: Any, canonical_schema: dict[str, Any]) -> Any:
    """Remove service-only null placeholders before canonical validation."""
    return _normalize(copy.deepcopy(value), canonical_schema, canonical_schema)


def _to_service(
    value: Any, root: dict[str, Any], schema: dict[str, Any]
) -> Any:
    schema = _schema_for_value(root, schema, value)
    if schema.get("type") == "object" and isinstance(value, dict):
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        rendered = {}
        for name, child_schema in properties.items():
            if name in value:
                rendered[name] = _to_service(value[name], root, child_schema)
            elif name not in required:
                rendered[name] = None
        return rendered
    if schema.get("type") == "array" and isinstance(value, list):
        return [_to_service(item, root, schema["items"]) for item in value]
    return copy.deepcopy(value)


def canonical_to_service_output(
    value: Any, canonical_schema: dict[str, Any]
) -> Any:
    """Render canonical fixture data in the service-required nullable shape."""
    return _to_service(value, canonical_schema, canonical_schema)
