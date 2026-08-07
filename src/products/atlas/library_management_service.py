# Safely reprocesses and removes registered Atlas sources.

import hashlib
import shutil
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from products.atlas.product_config import create_atlas_context
from wingman.shared.product_contract import ProductCapability

from wingman.core.concept_registry_storage import (
    load_registry,
    save_registry,
)
from products.atlas.document_ingestion import ingest_document
from wingman.core.embedding_storage import (
    load_embeddings,
    save_embeddings,
)
from products.atlas.intake_service import UPLOADS_DIRECTORY
from wingman.shared.library_service import find_knowledge_path
from wingman.shared.source_registry import (
    load_source_registry,
    save_source_registry,
)


def remove_source_embeddings(source_id, embeddings):
    """
    Remove embeddings owned by one exact source prefix.
    """
    prefix = f"{source_id}_"
    updated_embeddings = {
        knowledge_id: embedding
        for knowledge_id, embedding in embeddings.items()
        if not knowledge_id.startswith(prefix)
    }

    return (
        updated_embeddings,
        len(embeddings) - len(updated_embeddings),
    )


def remove_source_concept_occurrences(
    source_id,
    concept_registry,
):
    """
    Remove source occurrences and now-unused concepts.
    """
    updated_registry = {}
    removed_occurrence_count = 0
    removed_concept_count = 0

    for registry_key, concept in concept_registry.items():
        updated_concept = deepcopy(concept)
        occurrences = concept.get("occurrences", [])
        remaining_occurrences = [
            occurrence
            for occurrence in occurrences
            if occurrence.get("document") != source_id
        ]
        removed_occurrence_count += (
            len(occurrences)
            - len(remaining_occurrences)
        )

        if not remaining_occurrences:
            removed_concept_count += 1
            continue

        updated_concept["occurrences"] = (
            remaining_occurrences
        )
        updated_registry[registry_key] = updated_concept

    return (
        updated_registry,
        removed_occurrence_count,
        removed_concept_count,
    )


def restore_processed_knowledge(
    knowledge_path,
    previous_bytes,
):
    """
    Restore exact processed JSON bytes or remove a new file.
    """
    if previous_bytes is None:
        if knowledge_path.exists():
            knowledge_path.unlink()

        return

    knowledge_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary_path = knowledge_path.with_name(
        f".{knowledge_path.name}.rollback.tmp"
    )
    temporary_path.write_bytes(previous_bytes)
    temporary_path.replace(knowledge_path)


def rollback_reprocessing(
    original_error,
    source_registry,
    embeddings,
    concept_registry,
    knowledge_path,
    previous_knowledge_bytes,
):
    """
    Restore all reprocessing state or raise a rollback error.
    """
    restoration_failures = []
    restoration_steps = [
        (
            "source registry",
            lambda: save_source_registry(
                source_registry
            ),
        ),
        (
            "embedding index",
            lambda: save_embeddings(embeddings),
        ),
        (
            "concept registry",
            lambda: save_registry(concept_registry),
        ),
        (
            "processed knowledge JSON",
            lambda: restore_processed_knowledge(
                knowledge_path,
                previous_knowledge_bytes,
            ),
        ),
    ]

    for label, restore in restoration_steps:
        try:
            restore()
        except Exception as error:
            restoration_failures.append(
                f"{label}: {error}"
            )

    if restoration_failures:
        raise RuntimeError(
            "Reprocessing rollback was incomplete: "
            + "; ".join(restoration_failures)
        ) from original_error


def rollback_removal(
    original_error,
    source_registry,
    embeddings,
    concept_registry,
    source_directory,
    tombstone_path,
):
    """
    Restore all removal state or raise a rollback error.
    """
    restoration_failures = []
    restoration_steps = [
        (
            "source registry",
            lambda: save_source_registry(
                source_registry
            ),
        ),
        (
            "embedding index",
            lambda: save_embeddings(embeddings),
        ),
        (
            "concept registry",
            lambda: save_registry(concept_registry),
        ),
    ]

    if tombstone_path:
        restoration_steps.append(
            (
                "uploaded source directory",
                lambda: tombstone_path.rename(
                    source_directory
                ),
            )
        )

    for label, restore in restoration_steps:
        try:
            restore()
        except Exception as error:
            restoration_failures.append(
                f"{label}: {error}"
            )

    if restoration_failures:
        raise RuntimeError(
            "Source-removal rollback was incomplete: "
            + "; ".join(restoration_failures)
        ) from original_error


def require_registered_source(source_id, registry):
    """
    Return source metadata or raise a clear lookup error.
    """
    if source_id not in registry:
        raise KeyError(
            f"Unknown library source: {source_id}"
        )

    return registry[source_id]


def reprocess_library_source(
    source_id,
    *,
    product_context=None,
):
    """
    Rebuild one registered source while preserving its identity.
    """
    explicit_context = product_context is not None
    context = (
        product_context
        if explicit_context
        else create_atlas_context()
    )
    context.require(ProductCapability.SOURCE_LIBRARY)
    context.require(ProductCapability.SOURCE_INGESTION)
    source_registry = load_source_registry()
    metadata = require_registered_source(
        source_id,
        source_registry,
    )
    original_path_value = metadata.get("original_path")
    original_path = (
        Path(original_path_value)
        if original_path_value
        else None
    )

    if (
        original_path is None
        or not original_path.exists()
        or not original_path.is_file()
    ):
        raise FileNotFoundError(
            f"Original file is unavailable for source: "
            f"{source_id}"
        )

    content_hash = hashlib.sha256(
        original_path.read_bytes()
    ).hexdigest()

    knowledge_path = find_knowledge_path(
        source_id,
        original_path=original_path_value,
    )

    if knowledge_path is None:
        knowledge_path = (
            original_path.parent
            / f"{source_id}.json"
        )

    embeddings = load_embeddings()
    concept_registry = load_registry()
    source_registry_backup = deepcopy(source_registry)
    embeddings_backup = deepcopy(embeddings)
    concept_registry_backup = deepcopy(
        concept_registry
    )
    previous_knowledge_bytes = (
        knowledge_path.read_bytes()
        if knowledge_path.exists()
        else None
    )

    (
        cleaned_embeddings,
        removed_embedding_count,
    ) = remove_source_embeddings(
        source_id,
        embeddings,
    )
    (
        cleaned_concepts,
        removed_occurrence_count,
        removed_concept_count,
    ) = remove_source_concept_occurrences(
        source_id,
        concept_registry,
    )

    try:
        save_embeddings(cleaned_embeddings)
        save_registry(cleaned_concepts)
        ingestion_arguments = {
            "file_path": original_path,
            "domain": (
                metadata.get("domain")
                or context.product.default_domain
            ),
            "output_path": knowledge_path,
            "source_id": source_id,
        }
        if explicit_context:
            ingestion_arguments["product_context"] = context
        knowledge_objects = ingest_document(
            **ingestion_arguments
        )
        reprocessed_at = datetime.now(
            timezone.utc
        ).isoformat()
        updated_source_registry = deepcopy(
            source_registry
        )
        updated_source_registry[source_id] = {
            **metadata,
            "content_hash": content_hash,
            "reprocessed_at": reprocessed_at,
        }
        save_source_registry(
            updated_source_registry
        )
    except Exception as original_error:
        rollback_reprocessing(
            original_error,
            source_registry_backup,
            embeddings_backup,
            concept_registry_backup,
            knowledge_path,
            previous_knowledge_bytes,
        )
        raise

    return {
        "status": "reprocessed",
        "source_id": source_id,
        "display_name": metadata.get(
            "display_name",
            source_id,
        ),
        "knowledge_object_count": len(
            knowledge_objects
        ),
        "removed_embedding_count": (
            removed_embedding_count
        ),
        "removed_occurrence_count": (
            removed_occurrence_count
        ),
        "removed_concept_count": (
            removed_concept_count
        ),
        "reprocessed_at": reprocessed_at,
    }


def remove_library_source(
    source_id,
    *,
    product_context=None,
):
    """
    Remove one uploaded source using transactional persistence.
    """
    context = (
        product_context
        if product_context is not None
        else create_atlas_context()
    )
    context.require(ProductCapability.SOURCE_LIBRARY)
    source_registry = load_source_registry()
    metadata = require_registered_source(
        source_id,
        source_registry,
    )

    if metadata.get(
        "source_kind",
        "repository",
    ) != "upload":
        raise PermissionError(
            "Repository sources are protected and "
            "cannot be removed from the Library."
        )

    expected_source_directory = (
        UPLOADS_DIRECTORY
        / source_id
    )

    if expected_source_directory.is_symlink():
        raise ValueError(
            "Uploaded source directory cannot be a "
            "symbolic link."
        )

    uploads_directory = UPLOADS_DIRECTORY.resolve()
    source_directory = (
        expected_source_directory.resolve()
    )

    if (
        source_directory.parent != uploads_directory
        or source_directory.name != source_id
    ):
        raise ValueError(
            "Uploaded source directory is outside the "
            "configured uploads directory."
        )

    if (
        expected_source_directory.exists()
        and not expected_source_directory.is_dir()
    ):
        raise ValueError(
            "Uploaded source path must be a directory."
        )

    embeddings = load_embeddings()
    concept_registry = load_registry()
    source_registry_backup = deepcopy(source_registry)
    embeddings_backup = deepcopy(embeddings)
    concept_registry_backup = deepcopy(
        concept_registry
    )
    updated_source_registry = deepcopy(
        source_registry
    )
    del updated_source_registry[source_id]
    (
        updated_embeddings,
        removed_embedding_count,
    ) = remove_source_embeddings(
        source_id,
        embeddings,
    )
    (
        updated_concepts,
        removed_occurrence_count,
        removed_concept_count,
    ) = remove_source_concept_occurrences(
        source_id,
        concept_registry,
    )
    tombstone_path = None

    try:
        if source_directory.exists():
            tombstone_path = (
                uploads_directory
                / (
                    f".{source_id}."
                    f"{uuid.uuid4().hex}.tombstone"
                )
            )
            source_directory.rename(tombstone_path)

        save_registry(updated_concepts)
        save_embeddings(updated_embeddings)
        save_source_registry(
            updated_source_registry
        )
    except Exception as original_error:
        rollback_removal(
            original_error,
            source_registry_backup,
            embeddings_backup,
            concept_registry_backup,
            source_directory,
            tombstone_path,
        )
        raise

    cleanup_warning = None

    if tombstone_path:
        try:
            shutil.rmtree(tombstone_path)
        except Exception as error:
            cleanup_warning = (
                "Source was removed, but tombstone "
                f"cleanup failed: {error}"
            )

    return {
        "status": "removed",
        "source_id": source_id,
        "display_name": metadata.get(
            "display_name",
            source_id,
        ),
        "removed_embedding_count": (
            removed_embedding_count
        ),
        "removed_occurrence_count": (
            removed_occurrence_count
        ),
        "removed_concept_count": (
            removed_concept_count
        ),
        "cleanup_warning": cleanup_warning,
    }
