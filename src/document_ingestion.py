"""Atlas composition and CLI for product-enriched document ingestion."""

import argparse

from concept_enrichment import enrich_concepts
from document_router import extract_document_units
from embedding_indexer import index_knowledge_objects
from knowledge_ingestion import (
    create_knowledge_objects as create_core_knowledge_objects,
)
from knowledge_ingestion import (
    ingest_document as ingest_core_document,
)
from knowledge_ingestion import save_knowledge_objects
from section_resolver import resolve_section


# Supported through Mission 028: callers may import or patch these six
# names exactly as they could before the Airframe split.
__all__ = [
    "create_knowledge_objects",
    "extract_document_units",
    "index_knowledge_objects",
    "ingest_document",
    "resolve_section",
    "save_knowledge_objects",
]


def create_knowledge_objects(
    file_path,
    domain,
    source_id=None,
    *,
    enricher=None,
    unit_extractor=None,
    section_selector=None,
):
    """Create objects using Atlas's concept and record enrichment."""
    return create_core_knowledge_objects(
        file_path,
        domain,
        source_id=source_id,
        enricher=(
            enricher
            if enricher is not None
            else enrich_concepts
        ),
        unit_extractor=(
            unit_extractor
            if unit_extractor is not None
            else extract_document_units
        ),
        section_selector=(
            section_selector
            if section_selector is not None
            else resolve_section
        ),
    )


def ingest_document(
    file_path,
    domain,
    output_path=None,
    source_id=None,
    *,
    indexer=None,
):
    """Run ingestion with Atlas enrichment injected into Core."""
    return ingest_core_document(
        file_path,
        domain,
        output_path=output_path,
        source_id=source_id,
        enricher=enrich_concepts,
        object_creator=create_knowledge_objects,
        object_saver=save_knowledge_objects,
        indexer=(
            indexer
            if indexer is not None
            else index_knowledge_objects
        ),
    )


def build_argument_parser():
    """Build the supported ingestion command-line interface."""
    parser = argparse.ArgumentParser(
        description=(
            "Ingest one document through the Atlas "
            "compatibility composition."
        )
    )
    parser.add_argument("file_path")
    parser.add_argument(
        "--domain",
        default="General",
    )
    parser.add_argument("--output-path")
    parser.add_argument("--source-id")
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help=(
            "Create processed knowledge without model-backed "
            "embedding indexing."
        ),
    )
    return parser


def main(arguments=None):
    """Run the public compatibility wrapper from the command line."""
    options = build_argument_parser().parse_args(
        arguments
    )
    indexer = (
        (lambda knowledge_objects: None)
        if options.skip_index
        else None
    )
    chunks = ingest_document(
        file_path=options.file_path,
        domain=options.domain,
        output_path=options.output_path,
        source_id=options.source_id,
        indexer=indexer,
    )
    print(f"Saved {len(chunks)} chunks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
