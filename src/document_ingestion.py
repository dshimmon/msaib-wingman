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
from product_config import create_atlas_context
from product_runtime import create_product_knowledge_objects
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
    product_context=None,
):
    """Create objects using Atlas's concept and record enrichment."""
    explicit_context = product_context is not None
    context = (
        product_context
        if explicit_context
        else create_atlas_context()
    )
    return create_product_knowledge_objects(
        context,
        file_path,
        domain,
        source_id=source_id,
        enricher=(
            enricher
            if enricher is not None
            else (
                context.product.records.enrich_knowledge
                if explicit_context
                else enrich_concepts
            )
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
        core_creator=create_core_knowledge_objects,
    )


def ingest_document(
    file_path,
    domain,
    output_path=None,
    source_id=None,
    *,
    indexer=None,
    product_context=None,
    progress_callback=None,
):
    """Run ingestion with Atlas enrichment injected into Core."""
    explicit_context = product_context is not None
    context = (
        product_context
        if explicit_context
        else create_atlas_context()
    )

    def configured_creator(
        composed_file_path,
        composed_domain,
        source_id=None,
        *,
        enricher=None,
    ):
        return create_knowledge_objects(
            composed_file_path,
            composed_domain,
            source_id=source_id,
            enricher=enricher,
            product_context=context,
        )

    arguments = {
        "output_path": output_path,
        "source_id": source_id,
        "enricher": (
            context.product.records.enrich_knowledge
            if explicit_context
            else enrich_concepts
        ),
        "object_creator": configured_creator,
        "object_saver": save_knowledge_objects,
        "indexer": (
            indexer
            if indexer is not None
            else index_knowledge_objects
        ),
    }
    if progress_callback is not None:
        arguments["progress_callback"] = progress_callback
    return ingest_core_document(
        file_path,
        domain,
        **arguments,
    )


def build_argument_parser(product_context=None):
    """Build the supported ingestion command-line interface."""
    context = (
        product_context
        if product_context is not None
        else create_atlas_context()
    )
    parser = argparse.ArgumentParser(
        description=(
            "Ingest one document through the Atlas "
            "compatibility composition."
        )
    )
    parser.add_argument("file_path")
    parser.add_argument(
        "--domain",
        default=context.product.default_domain,
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
    product_context = create_atlas_context()
    options = build_argument_parser(
        product_context
    ).parse_args(
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
        product_context=product_context,
    )
    print(f"Saved {len(chunks)} chunks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
