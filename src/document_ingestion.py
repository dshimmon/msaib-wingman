# Converts normalized document units into enriched Wingman knowledge.

import json
from pathlib import Path

from concept_enrichment import enrich_concepts
from document_router import extract_document_units
from embedding_indexer import index_knowledge_objects
from section_resolver import resolve_section


def create_knowledge_objects(
    file_path,
    domain,
    source_id=None,
):
    """
    Convert a supported document into enriched
    Wingman knowledge objects.
    """
    if source_id is None:
        source_id = Path(file_path).stem

    document_units = extract_document_units(file_path)

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

        current_section = resolve_section(
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

        enriched_object = enrich_concepts(
            knowledge_object
        )

        knowledge_objects.append(
            enriched_object
        )

    return knowledge_objects


def save_knowledge_objects(
    knowledge_objects,
    output_path,
):
    """
    Save completed knowledge objects as JSON.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            knowledge_objects,
            file,
            indent=2,
        )


def ingest_document(
    file_path,
    domain,
    output_path=None,
    source_id=None,
):
    """
    Run the complete ingestion pipeline for one document.
    """
    source_path = Path(file_path)

    if source_id is None:
        source_id = source_path.stem

    if output_path is None:
        output_path = (
            source_path.parent
            / f"{source_id}.json"
        )

    knowledge_objects = create_knowledge_objects(
        source_path,
        domain,
        source_id=source_id,
    )

    save_knowledge_objects(
        knowledge_objects,
        output_path,
    )

    index_knowledge_objects(
        knowledge_objects
    )

    return knowledge_objects


if __name__ == "__main__":
    chunks = ingest_document(
        file_path=(
            "data/documents/onboarding/"
            "msaib-onboarding-2026.pptx"
        ),
        domain="Onboarding",
    )

    print(f"Saved {len(chunks)} chunks.")