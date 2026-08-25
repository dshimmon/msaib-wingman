"""Source-backed Atlas course catalog for the website Flight Cards contract."""

from collections import Counter, defaultdict
from pathlib import Path

from products.atlas import intake_service, source_summary_service
from products.atlas.product_config import normalize_course_id
from products.atlas.syllabus_intake import material_type_for_catalog
from wingman.shared.library_service import (
    list_library_sources,
    load_source_knowledge,
)
from wingman.shared.source_registry import (
    load_source_registry,
    update_active_source_metadata,
)


_SOURCE_STATUS = {
    "Ready": "ready",
    "Partially indexed": "partially_indexed",
    "Needs processing": "needs_processing",
    "Original unavailable": "original_unavailable",
}


def _course_label(source):
    return source.get("course_name") or source.get("course_id") or "Unassigned"


def _canonical_course_label(course_id, sources):
    labels = Counter(
        source["course_name"].strip()
        for source in sources
        if isinstance(source.get("course_name"), str)
        and source["course_name"].strip()
        and source["course_name"].strip().casefold() != course_id.casefold()
    )
    if not labels:
        return course_id
    return sorted(
        labels,
        key=lambda value: (-labels[value], value.casefold(), value),
    )[0]


def _source_link(source):
    if source.get("source_url"):
        return {
            "kind": "external_url",
            "url": source["source_url"],
            "label": "Open original source",
        }
    if source.get("original_available"):
        return {"kind": "download", "label": "Download original source"}
    return {"kind": "unavailable"}


def _validated_upload_paths(source):
    if source.get("source_kind") != "upload":
        return None, None
    try:
        source_id = source["source_id"]
        source_directory = intake_service.validated_source_directory(
            source_id
        ).resolve()
        original = Path(source.get("original_path") or "")
        knowledge = Path(source.get("knowledge_path") or "")
        if (
            original.is_symlink()
            or not original.is_file()
            or original.resolve().parent != source_directory
        ):
            original = None
        if (
            knowledge.is_symlink()
            or not knowledge.is_file()
            or knowledge.resolve().parent != source_directory
            or knowledge.name != f"{source_id}.json"
        ):
            knowledge = None
        return original, knowledge
    except (KeyError, OSError, ValueError):
        return None, None


def _flight_card(source):
    course_id = source.get("course_id")
    summary_original, summary_knowledge = _validated_upload_paths(source)
    knowledge_objects = None
    if summary_knowledge is not None:
        try:
            knowledge_objects = load_source_knowledge(summary_knowledge)
        except (OSError, TypeError, ValueError):
            pass
    summary = source_summary_service.load_persisted_summary(
        source_id=source["source_id"],
        source_hash=source.get("content_hash"),
        original_path=summary_original,
        knowledge_objects=knowledge_objects,
        attempted_status=source.get(
            source_summary_service.SUMMARY_STATUS_METADATA_KEY
        ),
    )
    can_request_summary = bool(
        summary_original
        and summary_knowledge
        and knowledge_objects
        and source.get("knowledge_object_count", 0)
    )
    return {
        "source_id": source["source_id"],
        "display_name": source.get("display_name") or source["source_id"],
        "file_name": source.get("file_name"),
        "file_type": source.get("file_type"),
        "course_state": "assigned" if course_id else "unassigned",
        "course_id": course_id,
        "course_label": _course_label(source),
        "material_type": material_type_for_catalog(source.get("material_type")),
        "source_status": _SOURCE_STATUS.get(
            source.get("status"), "needs_processing"
        ),
        **summary,
        "source_hash": source.get("content_hash"),
        "source_link": _source_link(source),
        "knowledge_object_count": source.get("knowledge_object_count", 0),
        "concept_count": source.get("concept_count", 0),
        "record_count": source.get("record_count", 0),
        "embedding_count": source.get("embedding_count", 0),
        "allowed_actions": {
            "set_source_course": True,
            "request_source_summary": can_request_summary,
            "reprocess_library_source": bool(source.get("can_reprocess")),
            "remove_library_source": bool(source.get("can_remove")),
        },
    }


def list_course_filters():
    """List source-backed course folders plus the unassigned workspace."""
    sources = list_library_sources()
    grouped = defaultdict(list)
    unassigned_count = 0
    for source in sources:
        course_id = source.get("course_id")
        if course_id:
            grouped[course_id].append(source)
        else:
            unassigned_count += 1

    filters = [
        {
            "kind": "all",
            "course_id": None,
            "label": "All materials",
            "document_count": len(sources),
        }
    ]
    for course_id, course_sources in sorted(
        grouped.items(), key=lambda item: item[0].casefold()
    ):
        label = _canonical_course_label(course_id, course_sources)
        filters.append(
            {
                "kind": "assigned",
                "course_id": course_id,
                "label": label,
                "document_count": len(course_sources),
            }
        )
    if unassigned_count:
        filters.append(
            {
                "kind": "unassigned",
                "course_id": None,
                "label": "Unassigned",
                "document_count": unassigned_count,
            }
        )
    return filters


def list_flight_cards(course_id=None, course_state=None):
    """Return source-backed material cards with optional course filtering."""
    cards = [_flight_card(source) for source in list_library_sources()]
    if course_id is not None:
        cards = [card for card in cards if card["course_id"] == course_id]
    if course_state is not None:
        cards = [card for card in cards if card["course_state"] == course_state]
    return cards


def get_flight_card(source_id):
    """Return one exact source as a course material card."""
    for source in list_library_sources():
        if source["source_id"] == source_id:
            return _flight_card(source)
    raise KeyError(f"Unknown course material: {source_id}")


def get_source_download(source_id):
    """Read the registered original while preserving its exact source identity."""
    registry = load_source_registry()
    metadata = registry.get(source_id)
    if metadata is None:
        raise KeyError(f"Unknown course material: {source_id}")
    original_path_value = metadata.get("original_path")
    if not original_path_value:
        raise FileNotFoundError("The original source is unavailable.")
    original_path = Path(original_path_value)
    if original_path.is_symlink() or not original_path.is_file():
        raise FileNotFoundError("The original source is unavailable.")
    return {
        "data": original_path.read_bytes(),
        "file_name": metadata.get("file_name") or original_path.name,
        "mime_type": metadata.get("mime_type") or "application/octet-stream",
    }


def set_source_course(source_id, course_id):
    """Move one source between virtual course folders in registry metadata."""
    normalized_course_id = normalize_course_id(course_id)
    registry = load_source_registry()
    if source_id not in registry:
        raise KeyError(f"Unknown course material: {source_id}")

    course_name = None
    if normalized_course_id:
        course_name = _canonical_course_label(
            normalized_course_id,
            [
                metadata
                for candidate_id, metadata in registry.items()
                if candidate_id != source_id
                and metadata.get("course_id") == normalized_course_id
            ],
        )
    update_active_source_metadata(
        source_id,
        {
            "course_id": normalized_course_id,
            "course_name": course_name,
        },
    )
    return {
        "status": "assigned" if normalized_course_id else "unassigned",
        "source_id": source_id,
        "course_id": normalized_course_id,
        "course_name": course_name,
    }


def request_source_summary(source_id):
    """Refresh one uploaded source summary from its processed knowledge."""
    source = next(
        (
            item
            for item in list_library_sources()
            if item["source_id"] == source_id
        ),
        None,
    )
    if source is None:
        raise KeyError(f"Unknown course material: {source_id}")
    if source.get("source_kind") != "upload":
        raise PermissionError(
            "Only uploaded course materials can receive stored summaries."
        )
    original, knowledge = _validated_upload_paths(source)
    if original is None or knowledge is None:
        raise FileNotFoundError(
            "The source or its processed knowledge is unavailable."
        )
    source_hash = source.get("content_hash")
    expected_metadata = {"content_hash": source_hash}
    status_key = source_summary_service.SUMMARY_STATUS_METADATA_KEY
    update_active_source_metadata(
        source_id,
        {status_key: "pending"},
        expected_metadata=expected_metadata,
    )
    try:
        artifact = source_summary_service.generate_and_persist_summary(
            source_id=source_id,
            source_hash=source_hash,
            original_path=original,
            knowledge_objects=load_source_knowledge(knowledge),
        )
    except Exception:
        try:
            update_active_source_metadata(
                source_id,
                {status_key: "failed"},
                expected_metadata=expected_metadata,
            )
        except Exception:
            pass
        raise

    terminal_status = artifact.get("status")
    if terminal_status not in {"ready", "failed"}:
        terminal_status = "failed"
    try:
        update_active_source_metadata(
            source_id,
            {status_key: terminal_status},
            expected_metadata=expected_metadata,
        )
    except Exception:
        pass
    return artifact
