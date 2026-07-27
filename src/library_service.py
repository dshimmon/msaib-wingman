# Builds Atlas's visible inventory of registered knowledge sources.

import json
from pathlib import Path

from embedding_storage import load_embeddings
from source_registry import load_source_registry


DOCUMENTS_DIRECTORY = Path("data/documents")


def find_knowledge_path(
    source_id,
    original_path=None,
):
    """
    Locate the processed knowledge JSON for one source.
    """
    possible_paths = []

    if original_path:
        source_path = Path(original_path)

        possible_paths.extend(
            [
                source_path.parent
                / f"{source_id}.json",
                source_path.with_suffix(".json"),
            ]
        )

    for possible_path in possible_paths:
        if possible_path.exists():
            return possible_path

    matching_paths = sorted(
        DOCUMENTS_DIRECTORY.rglob(
            f"{source_id}.json"
        )
    )

    if matching_paths:
        return matching_paths[0]

    return None


def load_source_knowledge(knowledge_path):
    """
    Load processed knowledge objects for one source.
    """
    if not knowledge_path:
        return []

    with knowledge_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        knowledge_objects = json.load(file)

    if not isinstance(knowledge_objects, list):
        raise ValueError(
            "Processed source knowledge must "
            "contain a JSON list."
        )

    return knowledge_objects


def count_source_embeddings(
    source_id,
    embeddings,
):
    """
    Count stored embeddings belonging to one source.
    """
    knowledge_id_prefix = f"{source_id}_"

    return sum(
        1
        for knowledge_id in embeddings
        if knowledge_id.startswith(
            knowledge_id_prefix
        )
    )


def determine_source_status(
    original_available,
    knowledge_object_count,
    embedding_count,
):
    """
    Describe whether a source is ready for Atlas.
    """
    if not original_available:
        return "Original unavailable"

    if knowledge_object_count == 0:
        return "Needs processing"

    if embedding_count < knowledge_object_count:
        return "Partially indexed"

    return "Ready"


def build_library_entry(
    source_id,
    metadata,
    embeddings,
):
    """
    Build one user-facing library entry.
    """
    original_path_value = metadata.get(
        "original_path"
    )

    original_path = (
        Path(original_path_value)
        if original_path_value
        else None
    )

    knowledge_path = find_knowledge_path(
        source_id,
        original_path=original_path_value,
    )

    knowledge_objects = load_source_knowledge(
        knowledge_path
    )

    concept_keys = set()
    record_count = 0

    for knowledge_object in knowledge_objects:
        record_count += len(
            knowledge_object.get(
                "records",
                [],
            )
        )

        for concept in knowledge_object.get(
            "concepts",
            [],
        ):
            if isinstance(concept, dict):
                concept_key = (
                    concept.get("id")
                    or concept.get("canonical")
                    or concept.get("name")
                )
            else:
                concept_key = str(concept)

            if concept_key:
                concept_keys.add(concept_key)

    embedding_count = count_source_embeddings(
        source_id,
        embeddings,
    )

    original_available = bool(
        original_path
        and original_path.is_file()
    )

    return {
        "source_id": source_id,
        "display_name": metadata.get(
            "display_name",
            source_id,
        ),
        "file_name": metadata.get("file_name"),
        "file_type": metadata.get("file_type"),
        "domain": metadata.get("domain"),
        "program": metadata.get("program"),
        "academic_year": metadata.get(
            "academic_year"
        ),
        "uploaded_at": metadata.get(
            "uploaded_at"
        ),
        "source_url": metadata.get(
            "source_url"
        ),
        "original_path": original_path_value,
        "knowledge_path": (
            str(knowledge_path)
            if knowledge_path
            else None
        ),
        "original_available": (
            original_available
        ),
        "knowledge_object_count": len(
            knowledge_objects
        ),
        "concept_count": len(concept_keys),
        "record_count": record_count,
        "embedding_count": embedding_count,
        "status": determine_source_status(
            original_available,
            len(knowledge_objects),
            embedding_count,
        ),
        "source_kind": metadata.get(
            "source_kind",
            "repository",
        ),
        "can_remove": (
            metadata.get(
                "source_kind",
                "repository",
            )
            == "upload"
        ),
        "can_reprocess": original_available,
        "reprocessed_at": metadata.get(
            "reprocessed_at"
        ),
    }


def list_library_sources():
    """
    Return every registered Atlas source with its
    current storage and indexing status.
    """
    registry = load_source_registry()
    embeddings = load_embeddings()

    library_entries = [
        build_library_entry(
            source_id,
            metadata,
            embeddings,
        )
        for source_id, metadata
        in registry.items()
    ]

    return sorted(
        library_entries,
        key=lambda entry: (
            entry["display_name"].lower()
        ),
    )
