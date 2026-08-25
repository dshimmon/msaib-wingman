"""Atlas-owned sequential batch ingestion with resumable local evidence."""

import hashlib
import json
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from wingman.core.document_errors import NoExtractableTextError
from wingman.core.document_router import SUPPORTED_EXTENSIONS
from wingman.core.folder_intake import (
    FolderEntry,
    normalized_relative_path,
    read_selected_file,
)
from products.atlas.intake_service import (
    IntakeRollbackError,
    cleanup_interrupted_upload,
    create_display_name,
    ingest_uploaded_document,
)
from wingman.shared.product_contract import ProductCapability, ProductContext
from wingman.shared.product_runtime import normalize_source_metadata
from wingman.shared.source_registry import (
    SourceMetadataConflictError,
    load_source_registry,
    update_active_source_metadata,
)


MANIFEST_VERSION = 1
DEFAULT_IMPORT_DIRECTORY = Path("data/imports")
TERMINAL_RESULTS = frozenset(
    {"succeeded", "skipped", "duplicate", "needs_ocr", "failed"}
)
PROGRESS_STAGES = frozenset(
    {"pending", "validating", "extracting", "saving", "indexing", "registering"}
)
COURSE_DUPLICATE_METADATA_FIELDS = (
    "course_id",
    "course_name",
    "material_type",
)
MANIFEST_FIELDS = frozenset(
    {
        "manifest_version",
        "batch_id",
        "product_id",
        "created_at",
        "updated_at",
        "completed_at",
        "input_mode",
        "domain",
        "assignments_confirmed",
        "cleanup_failure_stopped_batch",
        "stopped_file",
        "stopped_stage",
        "files",
    }
)
FILE_RECORD_FIELDS = frozenset(
    {
        "file_id",
        "relative_path",
        "visible_name",
        "display_name",
        "file_size",
        "content_hash",
        "course_id",
        "product_metadata",
        "supported",
        "ready",
        "progress_stage",
        "terminal_result",
        "attempt_count",
        "reason_code",
        "message",
        "source_id",
        "duplicate_source_id",
        "knowledge_object_count",
        "summary_status",
        "possible_revision_of",
        "cleanup_verified",
        "retryable",
    }
)
OPTIONAL_FILE_RECORD_FIELDS = frozenset({"summary_status"})


class BatchValidationError(ValueError):
    """A batch is not ready for any persistent document mutation."""


class ManifestPersistenceError(RuntimeError):
    """Operational batch evidence could not be persisted atomically."""


@dataclass(frozen=True)
class BatchFileInput:
    """One runtime-only file reference; bytes never enter the manifest."""

    relative_path: str
    visible_name: str
    file_bytes: bytes | None = None
    file_path: Path | None = None
    folder_root: Path | None = None
    expected_root_identity: tuple[int, int] | None = None
    expected_file_identity: tuple[int, int] | None = None
    rejection_code: str | None = None
    rejection_message: str | None = None

    def read_bytes(self):
        if self.file_bytes is not None:
            return self.file_bytes
        if self.file_path is None:
            raise OSError("The selected file is unavailable.")
        if self.folder_root is not None:
            return read_selected_file(
                self.folder_root,
                self.relative_path,
                expected_root_identity=self.expected_root_identity,
                expected_file_identity=self.expected_file_identity,
            )
        return self.file_path.read_bytes()


@dataclass
class BatchPlan:
    """Serializable manifest state plus runtime-only selected inputs."""

    manifest: dict
    inputs: dict[str, BatchFileInput]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def create_batch_id():
    return f"batch-{uuid.uuid4().hex}"


def reset_assignment_confirmation_if_changed(
    state,
    assignment_signature,
    *,
    selection_changed=False,
    batch_id_factory=create_batch_id,
):
    """Invalidate browser confirmation when its reviewed assignments change."""
    prior_signature = state.get("batch_assignment_signature")
    if prior_signature == assignment_signature:
        return False
    state["batch_assignment_signature"] = assignment_signature
    state["batch_assignments_confirmed"] = False
    if prior_signature is not None and not selection_changed:
        state["batch_id"] = batch_id_factory()
        state["batch_result"] = None
    return True


def browser_file_input(file_name, file_bytes):
    """Build a browser candidate while rejecting path-bearing names."""
    if not isinstance(file_name, str) or not file_name.strip():
        return BatchFileInput(
            "unnamed",
            "unnamed",
            rejection_code="invalid_file_name",
            rejection_message="A visible filename is required.",
        )
    normalized_name = file_name.replace("\\", "/")
    if "/" in normalized_name or normalized_name in {".", ".."}:
        return BatchFileInput(
            Path(normalized_name).name or "unnamed",
            Path(normalized_name).name or "unnamed",
            rejection_code="unsafe_file_name",
            rejection_message="Browser filenames cannot contain paths or aliases.",
        )
    return BatchFileInput(normalized_name, normalized_name, file_bytes=file_bytes)


def folder_file_inputs(entries):
    """Translate bounded folder entries into the one batch input contract."""
    result = []
    for entry in entries:
        if not isinstance(entry, FolderEntry):
            raise TypeError("Folder inputs must contain FolderEntry values.")
        result.append(
            BatchFileInput(
                relative_path=entry.relative_path,
                visible_name=Path(entry.relative_path).name,
                file_path=entry.path,
                folder_root=entry.root,
                expected_root_identity=entry.root_identity,
                expected_file_identity=entry.file_identity,
                rejection_code=entry.reason_code,
                rejection_message=entry.message,
            )
        )
    return result


def normalize_course_assignment(context, value):
    """Apply Atlas's declared metadata rule to an explicit assignment."""
    if "course_id" not in {
        field.key for field in context.product.source_metadata_fields
    }:
        raise BatchValidationError(
            "The selected product does not declare Atlas course metadata."
        )
    normalized = normalize_source_metadata(context, {"course_id": value})
    return normalized.get("course_id")


def preview_batch(
    inputs,
    *,
    product_context,
    input_mode,
    default_course_id=None,
    course_overrides=None,
    display_name_overrides=None,
    product_metadata=None,
    product_metadata_overrides=None,
    domain=None,
    assignments_confirmed=False,
    batch_id=None,
    clock=utc_now,
):
    """Validate a deterministic batch preview without source mutation."""
    if not isinstance(product_context, ProductContext):
        raise TypeError("Batch ingestion requires an explicit ProductContext.")
    product_context.require(ProductCapability.SOURCE_INGESTION)
    if input_mode not in {"browser", "folder"}:
        raise ValueError("Input mode must be 'browser' or 'folder'.")
    overrides = dict(course_overrides or {})
    display_overrides = dict(display_name_overrides or {})
    metadata_overrides = dict(product_metadata_overrides or {})
    normalized_common_metadata = normalize_source_metadata(
        product_context,
        dict(product_metadata or {}),
    )
    metadata_assignment = normalized_common_metadata.get("course_id")
    if (
        default_course_id is not None
        and metadata_assignment is not None
        and normalize_course_assignment(product_context, default_course_id)
        != metadata_assignment
    ):
        raise BatchValidationError(
            "Default course assignment conflicts with product metadata."
        )
    default_assignment = normalize_course_assignment(
        product_context,
        default_course_id if default_course_id is not None else metadata_assignment,
    )
    timestamp = clock()
    batch_id = batch_id or create_batch_id()
    runtime_inputs = {}
    records = []
    seen_paths = set()

    ordered_inputs = sorted(
        inputs,
        key=lambda item: (
            item.relative_path.casefold(),
            item.relative_path,
        ),
    )
    for item in ordered_inputs:
        try:
            relative_path = normalized_relative_path(item.relative_path)
        except ValueError as error:
            relative_path = Path(item.relative_path).name or "unsafe"
            item = BatchFileInput(
                relative_path,
                relative_path,
                rejection_code="unsafe_relative_path",
                rejection_message=str(error),
            )
        normalized_key = relative_path.casefold()
        rejection_code = item.rejection_code
        rejection_message = item.rejection_message
        if normalized_key in seen_paths:
            rejection_code = "path_alias"
            rejection_message = "Another selected file uses the same normalized path."
        seen_paths.add(normalized_key)

        content = None
        if rejection_code is None:
            try:
                content = item.read_bytes()
            except Exception:
                rejection_code = "unreadable_input"
                rejection_message = "The selected file could not be read."
        extension = Path(item.visible_name).suffix.lower()
        if rejection_code is None and extension not in SUPPORTED_EXTENSIONS:
            rejection_code = "unsupported_format"
            rejection_message = f"Unsupported document type: {extension or '(none)'}"
        if rejection_code is None and not content:
            rejection_code = "empty_file"
            rejection_message = "The selected document is empty."

        content_hash = (
            hashlib.sha256(content).hexdigest()
            if content is not None
            else None
        )
        size = len(content) if content is not None else 0
        raw_override = overrides.get(relative_path)
        override_assignment = normalize_course_assignment(
            product_context, raw_override
        ) if raw_override is not None else None
        raw_file_metadata = metadata_overrides.get(relative_path, {})
        if not isinstance(raw_file_metadata, dict):
            raise BatchValidationError(
                f"Product metadata override must be a mapping for: {relative_path}"
            )
        normalized_file_metadata = normalize_source_metadata(
            product_context,
            {
                **normalized_common_metadata,
                **raw_file_metadata,
            },
        )
        file_metadata_assignment = normalized_file_metadata.get("course_id")
        if (
            override_assignment is not None
            and file_metadata_assignment is not None
            and override_assignment != file_metadata_assignment
        ):
            raise BatchValidationError(
                f"Course assignment conflicts with product metadata for: {relative_path}"
            )
        assignment = (
            override_assignment
            or file_metadata_assignment
            or default_assignment
        )
        ready = rejection_code is None and assignment is not None
        reason_code = rejection_code
        message = rejection_message
        terminal_result = "skipped" if rejection_code else None
        if rejection_code is None and assignment is None:
            reason_code = "course_assignment_required"
            message = "An explicit course assignment is required before ingestion."

        file_id = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]
        records.append(
            {
                "file_id": file_id,
                "relative_path": relative_path,
                "visible_name": item.visible_name,
                "display_name": (
                    display_overrides.get(relative_path, "").strip()
                    or create_display_name(item.visible_name)
                ),
                "file_size": size,
                "content_hash": content_hash,
                "course_id": assignment,
                "product_metadata": {
                    **normalized_file_metadata,
                    "course_id": assignment,
                },
                "supported": extension in SUPPORTED_EXTENSIONS,
                "ready": ready,
                "progress_stage": "pending",
                "terminal_result": terminal_result,
                "attempt_count": 0,
                "reason_code": reason_code,
                "message": message,
                "source_id": None,
                "duplicate_source_id": None,
                "knowledge_object_count": None,
                "summary_status": None,
                "possible_revision_of": [],
                "cleanup_verified": None,
                "retryable": False,
            }
        )
        if relative_path not in runtime_inputs:
            runtime_inputs[relative_path] = BatchFileInput(
                relative_path=relative_path,
                visible_name=item.visible_name,
                file_bytes=content if item.file_bytes is not None else None,
                file_path=item.file_path,
                folder_root=item.folder_root,
                expected_root_identity=item.expected_root_identity,
                expected_file_identity=item.expected_file_identity,
                rejection_code=rejection_code,
                rejection_message=rejection_message,
            )

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "batch_id": batch_id,
        "product_id": product_context.product_id,
        "created_at": timestamp,
        "updated_at": timestamp,
        "completed_at": None,
        "input_mode": input_mode,
        "domain": domain or product_context.product.default_domain,
        "assignments_confirmed": bool(assignments_confirmed),
        "cleanup_failure_stopped_batch": False,
        "stopped_file": None,
        "stopped_stage": None,
        "files": records,
    }
    return BatchPlan(manifest, runtime_inputs)


def validate_manifest(manifest):
    """Reject unknown versions and structurally unsafe resume state."""
    if not isinstance(manifest, dict):
        raise BatchValidationError("Batch manifest must contain a JSON object.")
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise BatchValidationError(
            f"Unsupported batch manifest version: {manifest.get('manifest_version')!r}"
        )
    missing = sorted(MANIFEST_FIELDS - set(manifest))
    unknown = sorted(set(manifest) - MANIFEST_FIELDS)
    if missing or unknown:
        raise BatchValidationError(
            "Batch manifest fields are invalid; missing="
            + repr(missing)
            + ", unknown="
            + repr(unknown)
        )
    for name in ("batch_id", "product_id", "created_at", "updated_at", "input_mode"):
        if not isinstance(manifest[name], str) or not manifest[name]:
            raise BatchValidationError(f"Batch manifest {name} must be text.")
    if not isinstance(manifest["files"], list):
        raise BatchValidationError("Batch manifest files must contain a list.")
    for record in manifest["files"]:
        if not isinstance(record, dict):
            raise BatchValidationError("Each batch file record must be an object.")
        missing = sorted(
            FILE_RECORD_FIELDS - OPTIONAL_FILE_RECORD_FIELDS - set(record)
        )
        unknown = sorted(set(record) - FILE_RECORD_FIELDS)
        if missing or unknown:
            raise BatchValidationError(
                "Batch file fields are invalid; missing="
                + repr(missing)
                + ", unknown="
                + repr(unknown)
            )
        normalized_relative_path(record.get("relative_path"))
        if not isinstance(record.get("file_size"), int) or record["file_size"] < 0:
            raise BatchValidationError("Batch file size must be non-negative.")
        if (
            not isinstance(record.get("attempt_count"), int)
            or record["attempt_count"] < 0
        ):
            raise BatchValidationError("Batch attempt count must be non-negative.")
        if record.get("summary_status") not in {None, "ready", "failed"}:
            raise BatchValidationError(
                "Batch summary status must be ready, failed, or null."
            )
        content_hash = record.get("content_hash")
        if content_hash is not None and (
            not isinstance(content_hash, str)
            or len(content_hash) != 64
            or any(character not in "0123456789abcdef" for character in content_hash)
        ):
            raise BatchValidationError("Batch content hash must be SHA-256 hex.")
        if not isinstance(record.get("product_metadata"), dict):
            raise BatchValidationError("Batch product metadata must be an object.")
        if not isinstance(record.get("possible_revision_of"), list) or not all(
            isinstance(value, str) for value in record["possible_revision_of"]
        ):
            raise BatchValidationError("Possible revisions must contain source IDs.")
        result = record.get("terminal_result")
        if result is not None and result not in TERMINAL_RESULTS:
            raise BatchValidationError(f"Unknown terminal result: {result!r}")
        stage = record.get("progress_stage")
        if stage not in PROGRESS_STAGES:
            raise BatchValidationError(f"Unknown progress stage: {stage!r}")
    return manifest


def write_text_atomic(path, content):
    """Write one operational artifact through same-directory replacement."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(content, encoding="utf-8")
        temporary_path.replace(path)
    except Exception as error:
        try:
            if temporary_path.exists():
                temporary_path.unlink()
        except Exception:
            pass
        raise ManifestPersistenceError(
            f"Could not persist operational batch artifact {path.name}: {error}"
        ) from error


def write_manifest(manifest, path, *, clock=utc_now):
    """Validate and atomically persist one versioned machine manifest."""
    validate_manifest(manifest)
    manifest["updated_at"] = clock()
    write_text_atomic(
        path,
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    )


def load_manifest(path):
    """Load and validate a machine manifest without accepting contents."""
    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BatchValidationError(f"Batch manifest is unreadable: {error}") from error
    return validate_manifest(manifest)


def manifest_path_for(batch_id):
    return DEFAULT_IMPORT_DIRECTORY / f"{batch_id}.json"


def artifact_paths_alias(first_path, second_path):
    """Conservatively detect operational output paths that may alias."""
    first = Path(first_path)
    second = Path(second_path)
    try:
        if first.exists() and second.exists() and first.samefile(second):
            return True
    except OSError:
        pass
    first_parent = first.parent.resolve(strict=False)
    second_parent = second.parent.resolve(strict=False)
    return (
        first_parent == second_parent
        and first.name.casefold() == second.name.casefold()
    )


def report_path_for(manifest_path):
    manifest_path = Path(manifest_path)
    report_path = manifest_path.with_suffix(".md")
    if artifact_paths_alias(manifest_path, report_path):
        report_path = manifest_path.with_name(
            f"{manifest_path.stem}.report.md"
        )
    return report_path


def report_counts(manifest):
    counts = {result: 0 for result in TERMINAL_RESULTS}
    for record in manifest["files"]:
        result = record.get("terminal_result")
        if result in counts:
            counts[result] += 1
    return counts


def render_import_report(manifest):
    """Render human-readable operational evidence from manifest fields only."""
    validate_manifest(manifest)
    counts = report_counts(manifest)
    assignments = {}
    for record in manifest["files"]:
        assignment = record.get("course_id")
        if assignment:
            assignments[assignment] = assignments.get(assignment, 0) + 1
    assignment_summary = ", ".join(
        f"{key} ({value})" for key, value in sorted(assignments.items())
    ) or "None"
    lines = [
        "# Document Import Report",
        "",
        f"- Batch ID: `{manifest['batch_id']}`",
        f"- Product: `{manifest['product_id']}`",
        f"- Course assignments: {assignment_summary}",
        f"- Started: {manifest['created_at']}",
        f"- Completed: {manifest.get('completed_at') or 'Not completed'}",
        f"- Files considered: {len(manifest['files'])}",
        f"- Succeeded: {counts['succeeded']}",
        f"- Skipped: {counts['skipped']}",
        f"- Duplicate: {counts['duplicate']}",
        f"- Needs OCR: {counts['needs_ocr']}",
        f"- Failed: {counts['failed']}",
        "- Cleanup failure stopped batch: "
        + ("Yes" if manifest.get("cleanup_failure_stopped_batch") else "No"),
        "",
        "## Per-file results",
        "",
    ]
    for record in manifest["files"]:
        result = record.get("terminal_result") or record.get("progress_stage")
        detail = f"- `{record['relative_path']}` — **{result}**"
        if record.get("reason_code"):
            detail += f" (`{record['reason_code']}`)"
        if record.get("message"):
            detail += f": {record['message']}"
        if record.get("source_id"):
            detail += f" Source: `{record['source_id']}`."
        elif record.get("duplicate_source_id"):
            detail += f" Existing source: `{record['duplicate_source_id']}`."
        if record.get("summary_status"):
            detail += f" Summary: **{record['summary_status']}**."
        lines.append(detail)
        revisions = record.get("possible_revision_of") or []
        if revisions:
            lines.append(
                "  - Possible revision of: "
                + ", ".join(f"`{source_id}`" for source_id in revisions)
                + ". No lineage was inferred or changed."
            )
        if record.get("terminal_result") == "failed" and record.get("retryable"):
            lines.append("  - Next action: explicitly retry this failed file.")
        if record.get("terminal_result") == "needs_ocr":
            lines.append(
                "  - The document exposed no extractable text, was not ingested "
                "as searchable knowledge, and requires OCR before processing."
            )
    lines.extend(
        [
            "",
            "The manifest and this report are local operational evidence. "
            "The Ledger and source registry remain canonical.",
            "",
        ]
    )
    return "\n".join(lines)


def find_matching_registered_source(registry, content_hash):
    for source_id, metadata in registry.items():
        if metadata.get("content_hash") == content_hash:
            return source_id
    return None


def reconcile_duplicate_course_metadata(
    record,
    source_id,
    existing_metadata,
    metadata_updater,
):
    """Apply confirmed Atlas course metadata without reassigning a conflict."""
    desired_metadata = record.get("product_metadata") or {}
    existing_course_id = existing_metadata.get("course_id")
    desired_course_id = desired_metadata.get("course_id")
    if (
        existing_course_id
        and desired_course_id
        and existing_course_id != desired_course_id
    ):
        return "conflict"

    metadata_updates = {
        key: desired_metadata[key]
        for key in COURSE_DUPLICATE_METADATA_FIELDS
        if desired_metadata.get(key) is not None
        and existing_metadata.get(key) != desired_metadata[key]
    }
    if not metadata_updates:
        return "unchanged"

    metadata_updater(
        source_id,
        metadata_updates,
        expected_metadata={"course_id": existing_course_id},
    )
    return "updated"


def record_duplicate_outcome(
    record,
    source_id,
    existing_metadata,
    metadata_updater,
    *,
    unchanged_reason,
):
    """Reconcile confirmed metadata before recording any duplicate outcome."""
    try:
        metadata_state = reconcile_duplicate_course_metadata(
            record,
            source_id,
            existing_metadata,
            metadata_updater,
        )
    except SourceMetadataConflictError:
        metadata_state = "conflict"
    except Exception as error:
        record.update(
            terminal_result="failed",
            reason_code="duplicate_metadata_update_failed",
            message=(
                "Matching content is already registered, but its confirmed "
                "course metadata could not be updated "
                f"({error.__class__.__name__})."
            ),
            duplicate_source_id=source_id,
            cleanup_verified=True,
            retryable=True,
        )
        return

    if metadata_state == "conflict":
        record.update(
            terminal_result="failed",
            reason_code="duplicate_course_conflict",
            message=(
                "Matching content is already assigned to a different "
                "course; review the existing source before reassigning it."
            ),
            duplicate_source_id=source_id,
            cleanup_verified=True,
            retryable=False,
        )
        return

    record.update(
        terminal_result="duplicate",
        reason_code=(
            "exact_duplicate_metadata_updated"
            if metadata_state == "updated"
            else unchanged_reason
        ),
        message=(
            "Matching content is already registered; its confirmed course "
            "metadata was updated without ingesting it again."
            if metadata_state == "updated"
            else "Matching content is already registered; it was not ingested again."
        ),
        duplicate_source_id=source_id,
        cleanup_verified=True,
        retryable=False,
    )


def possible_revisions(registry, visible_name, content_hash):
    return sorted(
        source_id
        for source_id, metadata in registry.items()
        if metadata.get("file_name") == visible_name
        and metadata.get("content_hash")
        and metadata.get("content_hash") != content_hash
    )


def notify_progress(callback, manifest, record):
    if callback is not None:
        callback(manifest["batch_id"], deepcopy(record))


def mark_stage(record, stage):
    if stage not in PROGRESS_STAGES:
        raise ValueError(f"Unknown ingestion stage: {stage}")
    record["progress_stage"] = stage


def validate_execution(plan, product_context):
    validate_manifest(plan.manifest)
    if plan.manifest["product_id"] != product_context.product_id:
        raise BatchValidationError("Manifest product does not match the context.")
    if not plan.manifest.get("assignments_confirmed"):
        raise BatchValidationError(
            "Course assignments must be explicitly confirmed before ingestion."
        )
    for record in plan.manifest["files"]:
        course_id = record.get("course_id")
        if course_id is not None and normalize_course_assignment(
            product_context, course_id
        ) != course_id:
            raise BatchValidationError(
                f"Course assignment is not normalized for: {record['relative_path']}"
            )
        if record.get("product_metadata", {}).get("course_id") != course_id:
            raise BatchValidationError(
                f"Course metadata is inconsistent for: {record['relative_path']}"
            )
    unassigned = [
        record["relative_path"]
        for record in plan.manifest["files"]
        if record.get("terminal_result") is None and not record.get("course_id")
    ]
    if unassigned:
        raise BatchValidationError(
            "Course assignment is missing for: " + ", ".join(unassigned)
        )


def execute_batch(
    plan,
    *,
    product_context,
    manifest_path=None,
    report_path=None,
    retry_failed=False,
    ingestor=ingest_uploaded_document,
    interrupted_cleanup=cleanup_interrupted_upload,
    registry_loader=load_source_registry,
    metadata_updater=update_active_source_metadata,
    progress_callback=None,
    clock=utc_now,
):
    """Process one batch sequentially and preserve every completed source."""
    if not isinstance(plan, BatchPlan):
        raise TypeError("execute_batch requires a BatchPlan.")
    if not isinstance(product_context, ProductContext):
        raise TypeError("Batch ingestion requires an explicit ProductContext.")
    product_context.require(ProductCapability.SOURCE_INGESTION)
    validate_execution(plan, product_context)
    manifest = plan.manifest
    manifest_path = Path(manifest_path or manifest_path_for(manifest["batch_id"]))
    report_path = Path(report_path or report_path_for(manifest_path))
    if artifact_paths_alias(manifest_path, report_path):
        raise BatchValidationError(
            "Manifest and report paths must be distinct."
        )
    write_manifest(manifest, manifest_path, clock=clock)

    for record in manifest["files"]:
        terminal = record.get("terminal_result")
        if terminal in {"succeeded", "duplicate", "skipped", "needs_ocr"}:
            continue
        if terminal == "failed" and not retry_failed:
            continue
        runtime_input = plan.inputs.get(record["relative_path"])
        if runtime_input is None:
            record.update(
                terminal_result="failed",
                reason_code="input_unavailable",
                message="The source file must be reselected before resume.",
                cleanup_verified=True,
                retryable=True,
            )
            write_manifest(manifest, manifest_path, clock=clock)
            notify_progress(progress_callback, manifest, record)
            continue

        try:
            file_bytes = runtime_input.read_bytes()
        except Exception as error:
            folder_input_changed = runtime_input.folder_root is not None
            record.update(
                terminal_result="failed",
                reason_code=(
                    "unsafe_input_changed"
                    if folder_input_changed
                    else "unreadable_input"
                ),
                message=(
                    "The selected folder file changed after preview; "
                    "create a new batch."
                    if folder_input_changed
                    else "The selected file could not be read "
                    f"({error.__class__.__name__})."
                ),
                cleanup_verified=True,
                retryable=not folder_input_changed,
            )
            write_manifest(manifest, manifest_path, clock=clock)
            notify_progress(progress_callback, manifest, record)
            continue
        current_hash = hashlib.sha256(file_bytes).hexdigest()
        if current_hash != record.get("content_hash"):
            record.update(
                terminal_result="failed",
                reason_code="content_changed",
                message="The selected file changed after preview; create a new batch.",
                cleanup_verified=True,
                retryable=False,
            )
            write_manifest(manifest, manifest_path, clock=clock)
            notify_progress(progress_callback, manifest, record)
            continue

        registry = registry_loader()
        registered = find_matching_registered_source(registry, current_hash)
        interrupted = (
            record.get("progress_stage") != "pending"
            or record.get("attempt_count", 0) > 0
        )
        if registered:
            record_duplicate_outcome(
                record,
                registered,
                registry.get(registered) or {},
                metadata_updater,
                unchanged_reason=(
                    "registered_during_interruption"
                    if interrupted
                    else "exact_duplicate"
                ),
            )
            write_manifest(manifest, manifest_path, clock=clock)
            notify_progress(progress_callback, manifest, record)
            continue
        if interrupted:
            try:
                cleanup_result = interrupted_cleanup(
                    record["visible_name"], current_hash
                )
            except Exception as error:
                record.update(
                    terminal_result="failed",
                    reason_code="cleanup_failed",
                    message=(
                        "Cleanup could not be verified "
                        f"({error.__class__.__name__})."
                    ),
                    cleanup_verified=False,
                    retryable=False,
                )
                manifest.update(
                    cleanup_failure_stopped_batch=True,
                    stopped_file=record["relative_path"],
                    stopped_stage=getattr(error, "stage", "resume_cleanup"),
                )
                write_manifest(manifest, manifest_path, clock=clock)
                notify_progress(progress_callback, manifest, record)
                break
            if cleanup_result.get("registered"):
                duplicate_source_id = cleanup_result.get("source_id")
                current_registry = registry_loader()
                record_duplicate_outcome(
                    record,
                    duplicate_source_id,
                    current_registry.get(duplicate_source_id) or {},
                    metadata_updater,
                    unchanged_reason="registered_during_interruption",
                )
                write_manifest(manifest, manifest_path, clock=clock)
                notify_progress(progress_callback, manifest, record)
                continue

        record["attempt_count"] = record.get("attempt_count", 0) + 1
        record["terminal_result"] = None
        record["reason_code"] = None
        record["message"] = None
        record["retryable"] = False
        record["cleanup_verified"] = None
        record["summary_status"] = None
        record["possible_revision_of"] = possible_revisions(
            registry, record["visible_name"], current_hash
        )

        def update_stage(stage):
            mark_stage(record, stage)
            write_manifest(manifest, manifest_path, clock=clock)
            notify_progress(progress_callback, manifest, record)

        update_stage("validating")
        try:
            result = ingestor(
                file_name=record["visible_name"],
                file_bytes=file_bytes,
                display_name=record.get("display_name")
                or create_display_name(record["visible_name"]),
                domain=manifest["domain"],
                product_metadata=record.get("product_metadata") or {
                    "course_id": record["course_id"]
                },
                product_context=product_context,
                atomic=True,
                progress_callback=update_stage,
            )
            if result["status"] == "already_exists":
                duplicate_source_id = result["source_id"]
                current_registry = registry_loader()
                record_duplicate_outcome(
                    record,
                    duplicate_source_id,
                    current_registry.get(duplicate_source_id) or {},
                    metadata_updater,
                    unchanged_reason="exact_duplicate",
                )
            else:
                record.update(
                    terminal_result="succeeded",
                    reason_code="ingested",
                    message="The source was ingested and registered successfully.",
                    source_id=result["source_id"],
                    knowledge_object_count=result["knowledge_object_count"],
                    summary_status=result.get("summary_status"),
                    cleanup_verified=True,
                    retryable=False,
                )
                if result.get("summary_status") == "failed":
                    record["message"] = (
                        "The source was ingested and registered successfully, "
                        "but its summary could not be created. Retry from the "
                        "document page."
                    )
        except NoExtractableTextError as error:
            cleanup_verified = bool(getattr(error, "cleanup_verified", False))
            record.update(
                terminal_result="needs_ocr",
                reason_code="no_extractable_text",
                message=(
                    "The document exposed no extractable text, was not ingested "
                    "as searchable knowledge, and requires OCR before processing."
                ),
                cleanup_verified=cleanup_verified,
                retryable=False,
            )
            if not cleanup_verified:
                manifest.update(
                    cleanup_failure_stopped_batch=True,
                    stopped_file=record["relative_path"],
                    stopped_stage=getattr(error, "failure_stage", "extracting"),
                )
        except IntakeRollbackError as error:
            record.update(
                terminal_result="failed",
                reason_code="cleanup_failed",
                message=(
                    "Cleanup could not be verified "
                    f"({error.__class__.__name__})."
                ),
                cleanup_verified=False,
                retryable=False,
            )
            manifest.update(
                cleanup_failure_stopped_batch=True,
                stopped_file=record["relative_path"],
                stopped_stage=error.stage,
            )
        except Exception as error:
            cleanup_verified = bool(getattr(error, "cleanup_verified", False))
            record.update(
                terminal_result="failed",
                reason_code="ingestion_failed",
                message=(
                    f"Ingestion failed during {record['progress_stage']} "
                    f"({error.__class__.__name__})."
                ),
                cleanup_verified=cleanup_verified,
                retryable=cleanup_verified,
            )
            if not cleanup_verified:
                manifest.update(
                    cleanup_failure_stopped_batch=True,
                    stopped_file=record["relative_path"],
                    stopped_stage=getattr(error, "failure_stage", record["progress_stage"]),
                )

        write_manifest(manifest, manifest_path, clock=clock)
        notify_progress(progress_callback, manifest, record)
        if manifest.get("cleanup_failure_stopped_batch"):
            break

    manifest["completed_at"] = clock()
    write_manifest(manifest, manifest_path, clock=clock)
    write_text_atomic(report_path, render_import_report(manifest))
    return {
        "manifest": manifest,
        "manifest_path": str(manifest_path),
        "report_path": str(report_path),
        "report": render_import_report(manifest),
        "counts": report_counts(manifest),
    }


def resume_plan(manifest_path, inputs, *, product_context):
    """Bind reselected runtime inputs to a validated persisted manifest."""
    manifest = load_manifest(manifest_path)
    if manifest["product_id"] != product_context.product_id:
        raise BatchValidationError("Manifest product does not match the context.")
    normalized_inputs = {}
    for item in inputs:
        relative_path = normalized_relative_path(item.relative_path)
        if relative_path in normalized_inputs:
            raise BatchValidationError(f"Duplicate reselected path: {relative_path}")
        normalized_inputs[relative_path] = item
    return BatchPlan(manifest, normalized_inputs)
