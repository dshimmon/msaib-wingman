# Validates, stores, ingests, and registers uploaded documents.

import hashlib
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from wingman.core import concept_registry_storage
from wingman.core import embedding_storage
from wingman.core.document_errors import NoReadableContentError
from products.atlas.document_ingestion import ingest_document
from wingman.core.document_router import SUPPORTED_EXTENSIONS
from products.atlas import source_summary_service
from products.atlas.product_config import ATLAS_PRODUCT, create_atlas_context
from wingman.shared.product_runtime import normalize_source_metadata
from wingman.shared.source_registry import (
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
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}


class IntakeRollbackError(RuntimeError):
    """An intake failure whose cleanup could not be proven complete."""

    def __init__(self, stage, failures):
        self.stage = stage
        self.cleanup_verified = False
        self.failures = tuple(failures)
        super().__init__(
            f"Intake rollback was incomplete at {stage}: "
            + "; ".join(self.failures)
        )


def capture_file(path):
    """Capture exact bytes and existence for one persistent JSON store."""
    path = Path(path)
    return path.exists(), path.read_bytes() if path.exists() else None


def restore_file(path, snapshot):
    """Restore exact prior bytes or remove a newly created store."""
    path = Path(path)
    existed, content = snapshot
    temporary_path = path.with_name(f".{path.name}.rollback.tmp")
    if existed:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_bytes(content)
        temporary_path.replace(path)
        return
    if temporary_path.exists():
        temporary_path.unlink()
    if path.exists():
        path.unlink()


def file_matches_snapshot(path, snapshot):
    """Verify exact persistence restoration without parsing contents."""
    path = Path(path)
    existed, content = snapshot
    return path.exists() == existed and (
        not existed or path.read_bytes() == content
    )


def validated_source_directory(source_id):
    """Resolve one deterministic upload directory without path escape."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id):
        raise ValueError("Source ID is not safe for local upload storage.")
    if UPLOADS_DIRECTORY.is_symlink():
        raise ValueError("Uploads directory cannot be a symbolic link.")
    uploads_directory = UPLOADS_DIRECTORY.resolve()
    candidate = UPLOADS_DIRECTORY / source_id
    if candidate.is_symlink():
        raise ValueError("Uploaded source directory cannot be a symbolic link.")
    resolved = candidate.resolve()
    if resolved.parent != uploads_directory or resolved.name != source_id:
        raise ValueError("Uploaded source directory escaped its configured root.")
    return candidate


def rollback_failed_intake(
    *,
    stage,
    source_directory,
    directory_existed,
    generated_paths,
    store_snapshots,
):
    """Remove per-source files and restore shared stores, then verify."""
    failures = []
    for path in generated_paths:
        try:
            if path.exists():
                path.unlink()
        except Exception as error:
            failures.append(f"remove {path.name}: {error}")
    for path, snapshot in store_snapshots:
        try:
            restore_file(path, snapshot)
        except Exception as error:
            failures.append(f"restore {path.name}: {error}")
    try:
        if (
            not directory_existed
            and source_directory.exists()
            and not any(source_directory.iterdir())
        ):
            source_directory.rmdir()
    except Exception as error:
        failures.append(f"remove source directory: {error}")

    for path in generated_paths:
        if path.exists():
            failures.append(f"generated path remains: {path.name}")
    for path, snapshot in store_snapshots:
        try:
            if not file_matches_snapshot(path, snapshot):
                failures.append(f"store verification failed: {path.name}")
        except Exception as error:
            failures.append(f"verify {path.name}: {error}")
    if failures:
        raise IntakeRollbackError(stage, failures)
    return True


def cleanup_interrupted_upload(file_name, content_hash):
    """Remove unregistered artifacts for one deterministic source identity."""
    existing_source_id, _ = find_source_by_content_hash(content_hash)
    if existing_source_id:
        return {"registered": True, "source_id": existing_source_id}

    source_id = create_source_id(Path(file_name).name, content_hash)
    source_directory = validated_source_directory(source_id)
    failures = []

    try:
        embeddings = embedding_storage.load_embeddings()
        prefix = f"{source_id}_"
        cleaned_embeddings = {
            key: value
            for key, value in embeddings.items()
            if not key.startswith(prefix)
        }
        if cleaned_embeddings != embeddings:
            embedding_storage.save_embeddings(cleaned_embeddings)
    except Exception as error:
        failures.append(f"embedding cleanup: {error}")

    try:
        concepts = concept_registry_storage.load_registry()
        cleaned_concepts = {}
        for key, concept in concepts.items():
            occurrences = concept.get("occurrences", [])
            remaining = [
                occurrence
                for occurrence in occurrences
                if occurrence.get("document") != source_id
            ]
            if remaining or not occurrences:
                cleaned_concepts[key] = {
                    **concept,
                    "occurrences": remaining,
                }
        if cleaned_concepts != concepts:
            concept_registry_storage.save_registry(cleaned_concepts)
    except Exception as error:
        failures.append(f"concept cleanup: {error}")

    for store_path in (
        embedding_storage.EMBEDDINGS_PATH,
        concept_registry_storage.REGISTRY_PATH,
    ):
        temporary_path = Path(f"{store_path}.tmp")
        try:
            if temporary_path.exists():
                temporary_path.unlink()
        except Exception as error:
            failures.append(f"temporary-store cleanup: {error}")

    try:
        if source_directory.exists():
            if not source_directory.is_dir() or source_directory.is_symlink():
                raise ValueError("Interrupted upload path is not a safe directory.")
            shutil.rmtree(source_directory)
    except Exception as error:
        failures.append(f"source cleanup: {error}")

    if failures or source_directory.exists():
        if source_directory.exists():
            failures.append("source directory remains after cleanup")
        raise IntakeRollbackError("resume_cleanup", failures)
    return {"registered": False, "source_id": source_id}

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
    atomic=False,
    progress_callback=None,
):
    """
    Store, ingest, and register one uploaded document.
    """
    stage = "validating"

    def track_progress(next_stage):
        nonlocal stage
        stage = next_stage
        if progress_callback is not None:
            progress_callback(next_stage)

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

    source_directory = validated_source_directory(source_id)
    directory_existed = source_directory.exists()
    if directory_existed and (
        not source_directory.is_dir()
        or any(source_directory.iterdir())
    ):
        raise FileExistsError(
            f"Upload storage already exists for source: {source_id}"
        )

    original_path = (
        source_directory
        / safe_file_name
    )

    output_path = (
        source_directory
        / f"{source_id}.json"
    )

    original_temporary_path = source_directory / f".{safe_file_name}.upload.tmp"
    store_snapshots = []
    if atomic:
        store_snapshots = [
            (
                embedding_storage.EMBEDDINGS_PATH,
                capture_file(embedding_storage.EMBEDDINGS_PATH),
            ),
            (
                concept_registry_storage.REGISTRY_PATH,
                capture_file(concept_registry_storage.REGISTRY_PATH),
            ),
        ]
    try:
        track_progress("validating")
        source_directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        original_temporary_path.write_bytes(file_bytes)
        original_temporary_path.replace(original_path)
        ingestion_arguments = {
            "file_path": original_path,
            "domain": domain,
            "output_path": output_path,
            "source_id": source_id,
        }
        if explicit_context:
            ingestion_arguments["product_context"] = context
        if atomic or progress_callback is not None:
            ingestion_arguments["progress_callback"] = track_progress
        stage = "extracting"
        knowledge_objects = ingest_document(**ingestion_arguments)
        if not knowledge_objects:
            raise NoReadableContentError(
                "Document contains no readable content."
            )

        final_display_name = (
            display_name.strip()
            if display_name
            and display_name.strip()
            else create_display_name(
                safe_file_name
            )
        )

        track_progress("registering")
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

    except Exception as original_error:
        if atomic:
            try:
                cleanup_verified = rollback_failed_intake(
                    stage=stage,
                    source_directory=source_directory,
                    directory_existed=directory_existed,
                    generated_paths=(
                        output_path,
                        original_path,
                        original_temporary_path,
                    ),
                    store_snapshots=store_snapshots,
                )
            except IntakeRollbackError as rollback_error:
                raise rollback_error from original_error
            try:
                original_error.cleanup_verified = cleanup_verified
                original_error.failure_stage = stage
            except Exception:
                pass
        else:
            for path in (output_path, original_path, original_temporary_path):
                if path.exists():
                    path.unlink()
            if (
                not directory_existed
                and source_directory.exists()
                and not any(source_directory.iterdir())
            ):
                source_directory.rmdir()
        raise

    summary_status = None
    if context.product_id == ATLAS_PRODUCT.product_id:
        try:
            summary_artifact = source_summary_service.generate_and_persist_summary(
                source_id=source_id,
                source_hash=content_hash,
                original_path=original_path,
                knowledge_objects=knowledge_objects,
            )
            summary_status = summary_artifact.get("status", "failed")
        except Exception:
            # Derived-summary failure must never remove a valid uploaded source.
            summary_status = "failed"

    return {
        "status": "ingested",
        "source_id": source_id,
        "display_name": final_display_name,
        "knowledge_object_count": len(
            knowledge_objects
        ),
        "summary_status": summary_status,
    }
