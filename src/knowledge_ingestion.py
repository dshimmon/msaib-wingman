"""Product-neutral document-to-knowledge ingestion mechanisms."""

import json
from pathlib import Path

from document_router import extract_document_units
from embedding_indexer import index_knowledge_objects
from section_resolver import resolve_section


def create_knowledge_objects(
    file_path,
    domain,
    source_id=None,
    *,
    enricher=None,
    unit_extractor=None,
    section_selector=None,
):
    """
    Convert a supported document into Wingman knowledge objects.

    Product enrichment is an injected callable. Core creates and owns the
    source-backed object shape but does not select product record policy.
    """
    if source_id is None:
        source_id = Path(file_path).stem

    if unit_extractor is None:
        unit_extractor = extract_document_units
    if section_selector is None:
        section_selector = resolve_section

    document_units = unit_extractor(file_path)

    knowledge_objects = []
    current_section = "General"

    for unit_number, unit in enumerate(
        document_units,
        start=1,
    ):
        heading = unit.get("heading")
        text = unit.get("text", "").strip()
        location = unit.get("location")

        if not text:
            continue

        current_section = section_selector(
            heading,
            current_section,
        )

        knowledge_object = {
            "id": f"{source_id}_{unit_number:03}",
            "document": source_id,
            "domain": domain,
            "heading": heading,
            "section": current_section,
            "concepts": [],
            "records": [],
            "location": location,
            "text": text,
        }

        if enricher is not None:
            knowledge_object = enricher(
                knowledge_object
            )

        knowledge_objects.append(
            knowledge_object
        )

    return knowledge_objects


def save_knowledge_objects(
    knowledge_objects,
    output_path,
):
    """Save completed knowledge objects as JSON."""
    output_file = Path(output_path)
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = output_file.with_name(
        f".{output_file.name}.tmp"
    )
    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            knowledge_objects,
            file,
            indent=2,
        )
    temporary_file.replace(output_file)


def ingest_document(
    file_path,
    domain,
    output_path=None,
    source_id=None,
    *,
    enricher=None,
    object_creator=None,
    object_saver=None,
    indexer=None,
    progress_callback=None,
):
    """
    Run generic extraction, persistence, and indexing.

    ``object_creator`` must accept ``file_path``, ``domain``,
    ``source_id=`` and ``enricher=``. This explicit callback contract is
    shared by Core and compatibility composition wrappers.
    """
    source_path = Path(file_path)

    if object_creator is None:
        object_creator = create_knowledge_objects
    if object_saver is None:
        object_saver = save_knowledge_objects
    if indexer is None:
        indexer = index_knowledge_objects

    if source_id is None:
        source_id = source_path.stem

    if output_path is None:
        output_path = (
            source_path.parent
            / f"{source_id}.json"
        )

    if progress_callback is not None:
        progress_callback("extracting")
    knowledge_objects = object_creator(
        source_path,
        domain,
        source_id=source_id,
        enricher=enricher,
    )

    if progress_callback is not None:
        progress_callback("saving")
    object_saver(
        knowledge_objects,
        output_path,
    )

    if progress_callback is not None:
        progress_callback("indexing")
    indexer(
        knowledge_objects
    )

    return knowledge_objects
