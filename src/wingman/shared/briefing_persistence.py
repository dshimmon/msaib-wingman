"""Persist complete generated briefing snapshots outside the Ledger layer."""

import hashlib
import json
import uuid
from dataclasses import dataclass

from wingman.core.ledger.briefing_repository import (
    create_briefing,
    create_briefing_version,
    get_briefing,
    next_briefing_version_number,
)
from wingman.core.ledger.database import transaction
from wingman.core.ledger.models import serialize_json
from wingman.core.ledger.source_repository import resolve_current_source_versions
from wingman.shared.source_registry import open_registry_database


@dataclass(frozen=True)
class BriefingPersistenceResult:
    """Typed metadata returned after an immutable version is saved."""

    briefing_id: str
    briefing_version_id: str
    version_number: int
    trace_id: str
    unresolved_source_ids: tuple[str, ...] = ()


def canonical_hash(value):
    """Return a deterministic SHA-256 digest for a JSON-safe value."""
    canonical = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def source_fingerprint(evidence_items):
    """Fingerprint the ordered identities of evidence used by a version."""
    identities = [
        {
            "source_id": item.get("source_id"),
            "source_version_id": item.get("source_version_id"),
            "location": item.get("location"),
            "evidence_content_hash": item["evidence_content_hash"],
        }
        for item in evidence_items
    ]
    return canonical_hash(identities)


def validate_evidence_relationship(reference_map, evidence):
    """Require E1..En to describe the generator's evidence order exactly."""
    expected_references = [
        f"E{index}" for index in range(1, len(evidence) + 1)
    ]
    if list(reference_map) != expected_references:
        raise ValueError(
            "Evidence references must align with ordered evidence."
        )
    for reference, item in zip(expected_references, evidence):
        expected_identity = {
            "source": item.get("source"),
            "location": item.get("location"),
            "heading": item.get("heading"),
        }
        if reference_map[reference] != expected_identity:
            raise ValueError(
                f"{reference} does not match its ordered evidence item."
            )


def _snapshot_item(item, source_version, friendly_metadata):
    snapshot = dict(item)
    snapshot.update(
        {
            "source_id": item.get("source"),
            "source_version_id": (
                source_version.entity_id
                if source_version is not None
                else None
            ),
            "location": item.get("location"),
            "heading": item.get("heading"),
            "domain": item.get("domain"),
            "section": item.get("section"),
            "text": item.get("text"),
            "structured_records": item.get("structured_records", []),
            "concepts": item.get("concepts", []),
            "source_metadata": friendly_metadata or {},
        }
    )
    snapshot["evidence_content_hash"] = canonical_hash(item)
    return snapshot


def persist_generated_briefing(
    result,
    *,
    trace_id,
    briefing_id=None,
):
    """Persist a briefing entity and its next version atomically."""
    briefing = result["briefing"]
    retrieval_results = result["retrieval_results"]
    evidence = result["evidence"]
    reference_map = result["evidence_reference_map"]
    planner_type = result["planner_type"]

    # Validate all caller-owned JSON before opening the write transaction.
    serialize_json(briefing, "briefing", dict)
    serialize_json(retrieval_results, "retrieval_results", list)
    serialize_json(evidence, "evidence", list)
    serialize_json(reference_map, "evidence_reference_map", dict)
    validate_evidence_relationship(reference_map, evidence)

    connection = open_registry_database()
    try:
        existing = (
            get_briefing(connection, briefing_id)
            if briefing_id is not None
            else None
        )
        if briefing_id is not None and existing is None:
            raise KeyError(f"Unknown briefing: {briefing_id}")

        source_ids = list(
            dict.fromkeys(
                item.get("source")
                for item in evidence
                if item.get("source")
            )
        )
        versions = resolve_current_source_versions(connection, source_ids)
        snapshot_items = []
        for item in evidence:
            source_id = item.get("source")
            snapshot_items.append(
                _snapshot_item(
                    item,
                    versions.get(source_id),
                    item.get("source_metadata"),
                )
            )
        evidence_snapshot = {
            "evidence_reference_map": reference_map,
            "ordered_evidence": snapshot_items,
        }
        serialize_json(evidence_snapshot, "evidence_snapshot", dict)
        fingerprint = source_fingerprint(snapshot_items)

        durable_id = briefing_id or f"briefing_{uuid.uuid4()}"
        version_id = f"briefing_version_{uuid.uuid4()}"
        with transaction(connection):
            if existing is None:
                create_briefing(
                    connection,
                    entity_id=durable_id,
                    topic=result["topic"],
                    title=briefing["title"],
                )
                version_number = 1
            else:
                version_number = next_briefing_version_number(
                    connection, durable_id
                )
            create_briefing_version(
                connection,
                entity_id=version_id,
                briefing_id=durable_id,
                version_number=version_number,
                request_text=result["topic"],
                planner_type=planner_type,
                briefing=briefing,
                retrieval_results=retrieval_results,
                evidence_snapshot=evidence_snapshot,
                source_fingerprint=fingerprint,
            )

        unresolved = tuple(
            source_id
            for source_id in source_ids
            if versions.get(source_id) is None
        )
        return BriefingPersistenceResult(
            briefing_id=durable_id,
            briefing_version_id=version_id,
            version_number=version_number,
            trace_id=trace_id,
            unresolved_source_ids=unresolved,
        )
    finally:
        connection.close()
