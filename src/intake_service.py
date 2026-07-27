# Validates, stores, ingests, and registers uploaded documents.

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from document_ingestion import ingest_document
from document_router import SUPPORTED_EXTENSIONS
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


def ingest_uploaded_document(
    file_name,
    file_bytes,
    display_name=None,
    domain="General",
    program=None,
    academic_year=None,
):
    """
    Store, ingest, and register one uploaded document.
    """
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
        knowledge_objects = ingest_document(
            file_path=original_path,
            domain=domain,
            output_path=output_path,
            source_id=source_id,
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
                "program": (
                    program.strip()
                    if program
                    and program.strip()
                    else None
                ),
                "academic_year": (
                    academic_year.strip()
                    if academic_year
                    and academic_year.strip()
                    else None
                ),
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