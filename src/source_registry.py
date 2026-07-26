# Loads source metadata and attaches it to retrieved evidence.

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
        }

        enriched_evidence.append(
            {
                **item,
                "source_metadata": source_metadata,
            }
        )

    return enriched_evidence