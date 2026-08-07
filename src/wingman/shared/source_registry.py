# Loads, saves, and applies persistent source metadata.

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from wingman.core.ledger.database import connect_database, transaction
from wingman.core.ledger.legacy_import_repository import (
    get_legacy_import,
    record_legacy_import,
)
from wingman.core.ledger.migrations import apply_migrations
from wingman.core.ledger.models import serialize_json
from wingman.core.ledger.source_repository import (
    create_source,
    create_source_version,
    find_active_source_by_current_content_hash,
    find_matching_source_version,
    get_source,
    get_source_version,
    list_active_sources,
    list_sources,
    next_source_version_number,
    set_current_source_version,
    set_source_status,
    update_source,
)


SOURCE_REGISTRY_PATH = Path(
    "data/sources/source-registry.json"
)
LEGACY_IMPORT_KEY = "source-registry-json-v1"
def utc_now():
    return datetime.now(timezone.utc).isoformat()


def validate_registry(registry):
    """
    Validate a complete public registry before any writes.
    """
    if not isinstance(registry, dict):
        raise ValueError(
            "Source registry must contain a JSON object."
        )

    for source_id, metadata in registry.items():
        if not isinstance(source_id, str):
            raise ValueError(
                "Source registry IDs must be strings."
            )
        if not isinstance(metadata, dict):
            raise ValueError(
                f"Source metadata for {source_id} "
                "must contain a JSON object."
            )
        serialize_json(metadata, "source metadata", dict)


def read_legacy_registry():
    if not SOURCE_REGISTRY_PATH.exists():
        return None

    with SOURCE_REGISTRY_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        registry = json.load(file)
    validate_registry(registry)
    return registry


def normalized_arguments(source_id, metadata):
    return {
        "source_kind": metadata.get(
            "source_kind",
            "repository",
        ),
        "display_name": metadata.get(
            "display_name",
            source_id,
        ),
        "domain": metadata.get("domain"),
        "file_name": metadata.get("file_name"),
        "file_type": metadata.get("file_type"),
        "mime_type": metadata.get("mime_type"),
        "source_url": metadata.get("source_url"),
        "original_path": metadata.get("original_path"),
    }


def canonicalize_metadata(metadata):
    """
    Represent a missing hash by omitting it from public metadata.
    """
    canonical = dict(metadata)
    if not canonical.get("content_hash"):
        canonical.pop("content_hash", None)
    return canonical


def version_timestamp(metadata, fallback):
    return (
        metadata.get("reprocessed_at")
        or metadata.get("uploaded_at")
        or fallback
    )


def version_change_type(metadata, existing_version):
    if existing_version is None:
        return (
            "uploaded"
            if metadata.get("source_kind") == "uploaded"
            else "registered"
        )
    if (
        metadata.get("reprocessed_at")
        != existing_version.version_metadata.get(
            "reprocessed_at"
        )
    ):
        return "reprocessed"
    if (
        metadata.get("content_hash")
        != existing_version.content_hash
    ):
        return "content_changed"
    return "path_changed"


def sync_source(
    connection,
    source_id,
    metadata,
    timestamp,
):
    """
    Create or replace one active source inside a caller transaction.
    """
    metadata = canonicalize_metadata(metadata)
    source = get_source(connection, source_id)
    arguments = normalized_arguments(
        source_id,
        metadata,
    )
    if source is None:
        create_source(
            connection,
            entity_id=source_id,
            status="active",
            metadata=metadata,
            created_at=version_timestamp(
                metadata,
                timestamp,
            ),
            **arguments,
        )
    else:
        update_source(
            connection,
            source_id,
            status="active",
            metadata=metadata,
            updated_at=timestamp,
            **arguments,
        )

    source = get_source(connection, source_id)
    current_version = (
        get_source_version(
            connection,
            source.current_source_version_id,
        )
        if source.current_source_version_id
        else None
    )
    content_hash = metadata.get("content_hash")
    original_path = metadata.get("original_path")
    reprocessed_at = metadata.get("reprocessed_at")
    version_changed = (
        current_version is None
        or current_version.content_hash
        != content_hash
        or current_version.original_path != original_path
        or current_version.version_metadata.get(
            "reprocessed_at"
        ) != reprocessed_at
    )
    if not version_changed:
        return

    matching_version = find_matching_source_version(
        connection,
        source_id,
        content_hash=content_hash,
        original_path=original_path,
        reprocessed_at=reprocessed_at,
    )
    if matching_version is not None:
        set_current_source_version(
            connection,
            source_id,
            matching_version.entity_id,
            updated_at=timestamp,
        )
        return

    create_source_version(
        connection,
        entity_id=str(uuid.uuid4()),
        source_id=source_id,
        version_number=next_source_version_number(
            connection,
            source_id,
        ),
        content_hash=content_hash,
        original_path=original_path,
        change_type=version_change_type(
            metadata,
            current_version,
        ),
        version_metadata={
            key: metadata[key]
            for key in (
                "uploaded_at",
                "reprocessed_at",
            )
            if key in metadata
        },
        captured_at=version_timestamp(
            metadata,
            timestamp,
        ),
    )


def import_legacy_registry_if_needed(connection):
    """
    Perform the one-time JSON cutover when appropriate.
    """
    if get_legacy_import(
        connection,
        LEGACY_IMPORT_KEY,
    ) is not None:
        return

    if list_sources(connection):
        timestamp = utc_now()
        with transaction(connection):
            record_legacy_import(
                connection,
                import_key=LEGACY_IMPORT_KEY,
                status="skipped",
                completed_at=timestamp,
                details={
                    "reason": "ledger_sources_already_exist"
                },
            )
        return

    registry = read_legacy_registry()
    # Absence is deliberately not marked so a legitimate later seed can
    # still be imported.
    if registry is None:
        return

    timestamp = utc_now()
    with transaction(connection):
        for source_id, metadata in registry.items():
            sync_source(
                connection,
                source_id,
                metadata,
                timestamp,
            )
        record_legacy_import(
            connection,
            import_key=LEGACY_IMPORT_KEY,
            status="completed",
            completed_at=timestamp,
            details={"source_count": len(registry)},
        )


def open_registry_database():
    connection = connect_database()
    try:
        apply_migrations(connection)
        import_legacy_registry_if_needed(connection)
    except Exception:
        connection.close()
        raise
    return connection


def load_source_registry():
    """
    Load all active source metadata from Ledger.
    """
    connection = open_registry_database()
    try:
        return {
            source.entity_id: dict(source.metadata)
            for source in list_active_sources(connection)
        }
    finally:
        connection.close()


def save_source_registry(registry):
    """
    Replace the complete active source snapshot in one transaction.
    """
    validate_registry(registry)
    connection = open_registry_database()
    try:
        timestamp = utc_now()
        with transaction(connection):
            existing_sources = {
                source.entity_id: source
                for source in list_sources(connection)
            }
            for source_id, metadata in registry.items():
                sync_source(
                    connection,
                    source_id,
                    metadata,
                    timestamp,
                )
            for source_id, source in existing_sources.items():
                if (
                    source_id not in registry
                    and source.status == "active"
                ):
                    set_source_status(
                        connection,
                        source_id,
                        "removed",
                        updated_at=timestamp,
                    )
    finally:
        connection.close()


def register_source(source_id, metadata):
    """
    Create or update one source-registry entry.
    """
    if not isinstance(metadata, dict):
        raise ValueError(
            "Source metadata must contain a JSON object."
        )
    validate_registry({source_id: metadata})
    connection = open_registry_database()
    try:
        existing = get_source(connection, source_id)
        merged_metadata = canonicalize_metadata(
            {
                **(
                    existing.metadata
                    if existing is not None
                    else {}
                ),
                **metadata,
            }
        )
        with transaction(connection):
            sync_source(
                connection,
                source_id,
                merged_metadata,
                utc_now(),
            )
        return merged_metadata
    finally:
        connection.close()


def find_source_by_content_hash(content_hash):
    """
    Find an active source with identical current file content.
    """
    connection = open_registry_database()
    try:
        source = find_active_source_by_current_content_hash(
            connection,
            content_hash,
        )
        if source is None:
            return None, None
        return source.entity_id, dict(source.metadata)
    finally:
        connection.close()


def enrich_evidence_sources(evidence):
    """
    Attach friendly source metadata to evidence while
    preserving the internal source identifier.
    """
    registry = load_source_registry()
    enriched_evidence = []

    for item in evidence:
        source_id = item.get("source")
        stored_metadata = registry.get(
            source_id,
            {},
        )

        source_metadata = {
            **stored_metadata,
            "id": source_id,
            "display_name": stored_metadata.get(
                "display_name",
                source_id or "Unknown source",
            ),
            "file_name": stored_metadata.get("file_name"),
            "file_type": stored_metadata.get("file_type"),
            "mime_type": stored_metadata.get(
                "mime_type",
                "application/octet-stream",
            ),
            "domain": stored_metadata.get(
                "domain",
                item.get("domain"),
            ),
            "source_url": stored_metadata.get("source_url"),
            "original_path": stored_metadata.get(
                "original_path"
            ),
            "content_hash": stored_metadata.get(
                "content_hash"
            ),
            "uploaded_at": stored_metadata.get("uploaded_at"),
            "source_kind": stored_metadata.get(
                "source_kind",
                "repository",
            ),
        }

        enriched_evidence.append(
            {
                **item,
                "source_metadata": source_metadata,
            }
        )

    return enriched_evidence
