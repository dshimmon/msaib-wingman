# Loads, saves, and applies persistent source metadata.

import json
from pathlib import Path


SOURCE_REGISTRY_PATH = Path(
    "data/sources/source-registry.json"
)


def load_source_registry():
    """
    Load all registered source metadata.
    """
    if not SOURCE_REGISTRY_PATH.exists():
        return {}

    with SOURCE_REGISTRY_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        registry = json.load(file)

    if not isinstance(registry, dict):
        raise ValueError(
            "Source registry must contain a JSON object."
        )

    return registry


def save_source_registry(registry):
    """
    Save the source registry using an atomic replacement.
    """
    SOURCE_REGISTRY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = Path(
        f"{SOURCE_REGISTRY_PATH}.tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            registry,
            file,
            indent=2,
        )

    temporary_path.replace(
        SOURCE_REGISTRY_PATH
    )


def register_source(source_id, metadata):
    """
    Create or update one source-registry entry.
    """
    registry = load_source_registry()

    registry[source_id] = {
        **registry.get(source_id, {}),
        **metadata,
    }

    save_source_registry(registry)

    return registry[source_id]


def find_source_by_content_hash(content_hash):
    """
    Find an existing source with identical file content.
    """
    registry = load_source_registry()

    for source_id, metadata in registry.items():
        if metadata.get("content_hash") == content_hash:
            return source_id, metadata

    return None, None


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
            "id": source_id,
            "display_name": stored_metadata.get(
                "display_name",
                source_id or "Unknown source",
            ),
            "file_name": stored_metadata.get(
                "file_name",
            ),
            "file_type": stored_metadata.get(
                "file_type",
            ),
            "mime_type": stored_metadata.get(
                "mime_type",
                "application/octet-stream",
            ),
            "domain": stored_metadata.get(
                "domain",
                item.get("domain"),
            ),
            "program": stored_metadata.get(
                "program",
            ),
            "academic_year": stored_metadata.get(
                "academic_year",
            ),
            "source_url": stored_metadata.get(
                "source_url",
            ),
            "original_path": stored_metadata.get(
                "original_path",
            ),
            "content_hash": stored_metadata.get(
                "content_hash",
            ),
            "uploaded_at": stored_metadata.get(
                "uploaded_at",
            ),
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