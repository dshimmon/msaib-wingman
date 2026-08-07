# Validates, stores, ingests, and registers uploaded documents.

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from document_ingestion import ingest_document
from document_router import SUPPORTED_EXTENSIONS
from product_config import create_atlas_context
from product_runtime import normalize_source_metadata
from source_registry import (
    find_source_by_content_hash,
    register_source,
)


UPLOADS_DIRECTORY = Path(
    "data/documents/uploads"
)

MIME_TYPES = {
    ".pptx": (
        "application/vnd.openxmlformats-officedocument."
        "presentationml.presentation"
    ),
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
    ".xlsx": (
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
}

def create_display_name(file_name):
    """
    Create a friendly default name from a filename.
    """
    stem = Path(file_name).stem

    readable_name = re.sub(
        r"[-_]+",
        " ",
        stem,
    )

    return readable_name.strip().title()


def create_source_id(file_name, content_hash):
    """
    Create a stable readable source ID.
    """
    stem = Path(file_name).stem.lower()

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        stem,
    ).strip("-")

    if not slug:
        slug = "source"

    return f"{slug}-{content_hash[:12]}"


def normalize_optional_metadata_value(value):
    """Use None consistently for configured blank string values."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def normalize_product_metadata(
    product_metadata,
    *,
    program=None,
    academic_year=None,
    product_context=None,
):
    """Validate and normalize product-owned source metadata."""
    if (
        product_metadata is not None
        and not isinstance(product_metadata, dict)
    ):
        raise ValueError(
            "Product metadata must contain a dictionary."
        )

    if product_context is None:
        normalized = {
            "program": normalize_optional_metadata_value(
                program
            ),
            "academic_year": (
                normalize_optional_metadata_value(
                    academic_year
                )
            ),
        }
        for key, value in (
            product_metadata or {}
        ).items():
            normalized_value = (
                normalize_optional_metadata_value(
                    value
                )
            )
            if (
                normalized.get(key) is not None
                and normalized_value
                != normalized[key]
            ):
                raise ValueError(
                    "Product metadata conflicts with the "
                    f"legacy argument for {key!r}."
                )
            normalized[key] = normalized_value
        return normalize_source_metadata(
            create_atlas_context(),
            normalized,
        )

    normalized = normalize_source_metadata(
        product_context,
        dict(product_metadata or {}),
    )
    declarations = {
        field.key: field
        for field in (
            product_context.product.source_metadata_fields
        )
    }
    for key, legacy_value in (
        ("program", program),
        ("academic_year", academic_year),
    ):
        declaration = declarations.get(key)
        if declaration is None:
            if legacy_value is not None:
                raise ValueError(
                    f"Product {product_context.product_id!r} does not "
                    f"declare legacy Atlas metadata field {key!r}."
                )
            continue
        normalized_legacy_value = declaration.normalizer(
            legacy_value
        )
        if key not in normalized:
            normalized[key] = normalized_legacy_value
        elif (
            normalized_legacy_value is not None
            and normalized[key] != normalized_legacy_value
        ):
            raise ValueError(
                "Product metadata conflicts with the "
                f"legacy argument for {key!r}."
            )
    return normalized


def ingest_uploaded_document(
    file_name,
    file_bytes,
    display_name=None,
    domain=None,
    program=None,
    academic_year=None,
    product_metadata=None,
    product_context=None,
):
    """
    Store, ingest, and register one uploaded document.
    """
    explicit_context = product_context is not None
    context = (
        product_context
        if explicit_context
        else create_atlas_context()
    )
    if domain is None:
        domain = context.product.default_domain

    safe_file_name = Path(file_name).name
    extension = Path(safe_file_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported document type: {extension}"
        )

    if not file_bytes:
        raise ValueError(
            "Uploaded document is empty."
        )

    content_hash = hashlib.sha256(
        file_bytes
    ).hexdigest()

    normalized_product_metadata = (
        normalize_product_metadata(
            product_metadata,
            program=program,
            academic_year=academic_year,
            product_context=(
                context if explicit_context else None
            ),
        )
    )

    existing_source_id, existing_metadata = (
        find_source_by_content_hash(
            content_hash
        )
    )

    if existing_source_id:
        return {
            "status": "already_exists",
            "source_id": existing_source_id,
            "display_name": (
                existing_metadata.get(
                    "display_name",
                    existing_source_id,
                )
            ),
            "knowledge_object_count": None,
        }

    source_id = create_source_id(
        safe_file_name,
        content_hash,
    )

    source_directory = (
        UPLOADS_DIRECTORY
        / source_id
    )

    source_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    original_path = (
        source_directory
        / safe_file_name
    )

    output_path = (
        source_directory
        / f"{source_id}.json"
    )

    original_path.write_bytes(
        file_bytes
    )

    try:
        ingestion_arguments = {
            "file_path": original_path,
            "domain": domain,
            "output_path": output_path,
            "source_id": source_id,
        }
        if explicit_context:
            ingestion_arguments["product_context"] = context
        knowledge_objects = ingest_document(
            **ingestion_arguments
        )

        final_display_name = (
            display_name.strip()
            if display_name
            and display_name.strip()
            else create_display_name(
                safe_file_name
            )
        )

        register_source(
            source_id,
            {
                "display_name": final_display_name,
                "file_name": safe_file_name,
                "file_type": extension.lstrip("."),
                "mime_type": MIME_TYPES[extension],
                "domain": domain,
                **normalized_product_metadata,
                "source_url": None,
                "original_path": str(original_path),
                "content_hash": content_hash,
                "uploaded_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "source_kind": "upload",
            },
        )

    except Exception:
        if output_path.exists():
            output_path.unlink()

        if original_path.exists():
            original_path.unlink()

        if (
            source_directory.exists()
            and not any(
                source_directory.iterdir()
            )
        ):
            source_directory.rmdir()

        raise

    return {
        "status": "ingested",
        "source_id": source_id,
        "display_name": final_display_name,
        "knowledge_object_count": len(
            knowledge_objects
        ),
    }
