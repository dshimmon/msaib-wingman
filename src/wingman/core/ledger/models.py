"""
Typed domain records and JSON helpers for Ledger repositories.
"""

import json
from dataclasses import dataclass, field
from typing import Any


JsonObject = dict[str, Any]
JsonArray = list[Any]


def serialize_json(value, field_name, expected_type):
    """
    Validate and serialize a repository JSON value.
    """
    if not isinstance(value, expected_type):
        raise ValueError(
            f"{field_name} must be a "
            f"{expected_type.__name__}."
        )

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{field_name} must contain valid JSON values."
        ) from error


def deserialize_json(value):
    """
    Deserialize a stored JSON value.
    """
    return json.loads(value)


@dataclass(frozen=True)
class EntityRecord:
    entity_id: str
    entity_type: str
    product_key: str | None
    domain: str | None
    status: str
    version: int
    created_at: str
    updated_at: str
    metadata: JsonObject = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class SourceRecord(EntityRecord):
    source_kind: str = ""
    display_name: str = ""
    file_name: str | None = None
    file_type: str | None = None
    mime_type: str | None = None
    source_url: str | None = None
    original_path: str | None = None
    current_source_version_id: str | None = None


@dataclass(frozen=True)
class SourceVersionRecord(EntityRecord):
    source_id: str = ""
    version_number: int = 1
    content_hash: str | None = None
    original_path: str | None = None
    captured_at: str = ""
    change_type: str = ""
    version_metadata: JsonObject = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class BriefingRecord(EntityRecord):
    topic: str = ""
    title: str = ""
    current_briefing_version_id: str | None = None


@dataclass(frozen=True)
class BriefingVersionRecord(EntityRecord):
    briefing_id: str = ""
    version_number: int = 1
    request_text: str = ""
    planner_type: str = ""
    briefing: JsonObject = field(
        default_factory=dict
    )
    retrieval_results: JsonArray = field(
        default_factory=list
    )
    evidence_snapshot: JsonObject | JsonArray = field(default_factory=dict)
    source_fingerprint: str | None = None
    version_created_at: str = ""


@dataclass(frozen=True)
class ActionRecord(EntityRecord):
    origin_type: str | None = None
    origin_entity_id: str | None = None
    origin_item_key: str | None = None
    title: str = ""
    priority: str | None = None
    action_status: str = ""
    due_at: str | None = None
    notes: str | None = None
    approved_at: str | None = None
    completed_at: str | None = None


@dataclass(frozen=True)
class DiagnosticEventRecord(EntityRecord):
    trace_id: str | None = None
    operation: str = ""
    severity: str = ""
    recoverable: bool = False
    related_entity_id: str | None = None
    message: str = ""
    details: JsonObject = field(
        default_factory=dict
    )
    occurred_at: str = ""
