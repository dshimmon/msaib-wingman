"""Narrow Atlas UI adapter for the Flight Cards website contract."""

from dataclasses import dataclass, field
import importlib
from types import MappingProxyType
from typing import Any, Mapping

from products.atlas.syllabus_intake import material_type_for_catalog


FLIGHT_CARDS_SERVICE_MODULE = "products.atlas.flight_cards_service"
COURSE_KINDS = frozenset({"all", "assigned", "unassigned"})
COURSE_STATES = frozenset({"assigned", "unassigned"})
SOURCE_STATUSES = frozenset(
    {"ready", "partially_indexed", "needs_processing", "original_unavailable"}
)
SUMMARY_STATUSES = frozenset({"missing", "pending", "ready", "failed", "stale"})
SOURCE_LINK_KINDS = frozenset({"external_url", "download", "unavailable"})


class FlightCardsUnavailable(RuntimeError):
    """The presentation service is not available in this build."""


class FlightCardsRequestError(RuntimeError):
    """A presentation-service request failed without exposing unsafe details."""


@dataclass(frozen=True)
class CourseFilterOption:
    kind: str
    course_id: str | None
    label: str
    document_count: int


@dataclass(frozen=True)
class SummaryPoint:
    text: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceLink:
    kind: str = "unavailable"
    url: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class SourceDownload:
    data: bytes
    file_name: str
    mime_type: str = "application/octet-stream"


@dataclass(frozen=True)
class FlightCardView:
    source_id: str
    display_name: str
    file_name: str | None
    file_type: str | None
    course_state: str
    course_id: str | None
    course_label: str
    source_status: str
    summary_status: str
    material_type: str
    summary_title: str | None = None
    summary_points: tuple[SummaryPoint, ...] = ()
    safe_failure_title: str | None = None
    safe_failure_message: str | None = None
    source_hash: str | None = None
    summary_source_hash: str | None = None
    summary_knowledge_hash: str | None = None
    generator_version: str | None = None
    prompt_version: str | None = None
    generated_at: str | None = None
    evidence_map: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )
    source_link: SourceLink = field(default_factory=SourceLink)
    knowledge_object_count: int = 0
    concept_count: int = 0
    record_count: int = 0
    embedding_count: int = 0
    can_set_course: bool = False
    can_request_summary: bool = False
    can_reprocess: bool = False
    can_remove: bool = False


def _read(value, *names, default=None):
    for name in names:
        if isinstance(value, Mapping) and name in value:
            return value[name]
        if hasattr(value, name):
            return getattr(value, name)
    return default


def _mapping(value):
    if isinstance(value, Mapping):
        return value
    return {}


def _text(value, fallback=None):
    if value is None:
        return fallback
    rendered = str(value).strip()
    return rendered or fallback


def _count(value):
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _choice(value, allowed, fallback):
    normalized = _text(value, fallback)
    return normalized if normalized in allowed else fallback


def _coalesce(value, fallback):
    return fallback if value is None else value


def normalize_course_filter(value):
    kind = _choice(_read(value, "kind"), COURSE_KINDS, "all")
    course_id = _text(_read(value, "course_id"))
    if kind == "unassigned":
        course_id = None
    label = _text(
        _read(value, "label"),
        "Unassigned" if kind == "unassigned" else course_id or "All materials",
    )
    return CourseFilterOption(
        kind=kind,
        course_id=course_id,
        label=label,
        document_count=_count(_read(value, "document_count")),
    )


def _normalize_summary_points(value):
    points = []
    for item in value or ():
        if isinstance(item, str):
            text = item.strip()
            refs = ()
        else:
            text = _text(_read(item, "text", "point", "content", "summary"), "")
            refs = _read(item, "evidence_refs", "references", default=()) or ()
        if text:
            points.append(
                SummaryPoint(
                    text=text,
                    evidence_refs=tuple(
                        str(reference).strip()
                        for reference in refs
                        if str(reference).strip()
                    ),
                )
            )
    return tuple(points)


def _normalize_source_link(value):
    if isinstance(value, str):
        return SourceLink(kind="external_url", url=value)
    kind = _choice(_read(value, "kind", "type"), SOURCE_LINK_KINDS, "unavailable")
    return SourceLink(
        kind=kind,
        url=_text(_read(value, "url", "external_url")),
        label=_text(_read(value, "label")),
    )


def _allowed_action(value, action, *field_names):
    for name in field_names:
        direct = _read(value, name)
        if direct is not None:
            return bool(direct)
    allowed = _read(value, "allowed_actions", default=()) or ()
    if isinstance(allowed, Mapping):
        return bool(allowed.get(action, False))
    return action in allowed


def normalize_flight_card(value):
    file_metadata = _mapping(_read(value, "file_metadata", default={}))
    summary = _mapping(_read(value, "summary", default={}))
    failure = _mapping(_read(value, "safe_failure", "failure", default={}))
    counts = _mapping(_read(value, "counts", default={}))
    generator_metadata = _mapping(_read(value, "generator_metadata", default={}))
    prompt_metadata = _mapping(_read(value, "prompt_metadata", default={}))
    source_id = _text(_read(value, "source_id"))
    if not source_id:
        raise FlightCardsRequestError("Flight Cards returned a document without an ID.")
    course_id = _text(_read(value, "course_id"))
    course_state = _choice(
        _read(value, "course_state"),
        COURSE_STATES,
        "assigned" if course_id else "unassigned",
    )
    if course_state == "unassigned":
        course_id = None
    display_name = _text(
        _read(value, "display_name", "title"),
        _text(_read(file_metadata, "display_name", "file_name"), source_id),
    )
    evidence = _read(value, "evidence_map", default={}) or {}
    if not isinstance(evidence, Mapping):
        evidence = {}
    summary_points = _read(value, "summary_points")
    if summary_points is None:
        summary_points = _read(summary, "points", default=())

    return FlightCardView(
        source_id=source_id,
        display_name=display_name,
        file_name=_text(
            _read(value, "file_name"), _text(_read(file_metadata, "file_name"))
        ),
        file_type=_text(
            _read(value, "file_type"), _text(_read(file_metadata, "file_type"))
        ),
        course_state=course_state,
        course_id=course_id,
        course_label=_text(_read(value, "course_label"), course_id or "Unassigned"),
        source_status=_choice(
            _read(value, "source_status"), SOURCE_STATUSES, "needs_processing"
        ),
        summary_status=_choice(
            _read(value, "summary_status", default=_read(summary, "status")),
            SUMMARY_STATUSES,
            "missing",
        ),
        material_type=material_type_for_catalog(_read(value, "material_type")),
        summary_title=_text(
            _read(value, "summary_title"), _text(_read(summary, "title"))
        ),
        summary_points=_normalize_summary_points(summary_points),
        safe_failure_title=_text(
            _read(value, "safe_failure_title"), _text(_read(failure, "title"))
        ),
        safe_failure_message=_text(
            _read(value, "safe_failure_message"), _text(_read(failure, "message"))
        ),
        source_hash=_text(_read(value, "source_hash")),
        summary_source_hash=_text(_read(value, "summary_source_hash")),
        summary_knowledge_hash=_text(_read(value, "summary_knowledge_hash")),
        generator_version=_text(
            _read(value, "generator_version"),
            _text(
                _read(generator_metadata, "version", "generator_version", "model"),
                _text(_read(summary, "generator_version")),
            ),
        ),
        prompt_version=_text(
            _read(value, "prompt_version"),
            _text(
                _read(prompt_metadata, "version", "prompt_version", "id"),
                _text(_read(summary, "prompt_version")),
            ),
        ),
        generated_at=_text(
            _read(value, "generated_at"), _text(_read(summary, "generated_at"))
        ),
        evidence_map=MappingProxyType(dict(evidence)),
        source_link=_normalize_source_link(_read(value, "source_link", default={})),
        knowledge_object_count=_count(
            _coalesce(
                _read(value, "knowledge_object_count"),
                _read(counts, "knowledge_object_count", "knowledge_objects"),
            )
        ),
        concept_count=_count(
            _coalesce(
                _read(value, "concept_count"),
                _read(counts, "concept_count", "concepts"),
            )
        ),
        record_count=_count(
            _coalesce(
                _read(value, "record_count"),
                _read(counts, "record_count", "records"),
            )
        ),
        embedding_count=_count(
            _coalesce(
                _read(value, "embedding_count"),
                _read(counts, "embedding_count", "embeddings"),
            )
        ),
        can_set_course=_allowed_action(value, "set_source_course", "can_set_course"),
        can_request_summary=_allowed_action(
            value, "request_source_summary", "can_request_summary"
        ),
        can_reprocess=_allowed_action(
            value, "reprocess_library_source", "can_reprocess"
        ),
        can_remove=_allowed_action(value, "remove_library_source", "can_remove"),
    )


def normalize_source_download(value, source_id):
    if isinstance(value, bytes):
        return SourceDownload(data=value, file_name=source_id)
    if isinstance(value, tuple) and len(value) in {2, 3}:
        data, file_name, *mime_type = value
        value = {
            "data": data,
            "file_name": file_name,
            "mime_type": mime_type[0] if mime_type else None,
        }
    data = _read(value, "data", "content", "bytes")
    if not isinstance(data, bytes):
        raise FlightCardsRequestError("The source download is unavailable.")
    return SourceDownload(
        data=data,
        file_name=_text(_read(value, "file_name", "filename"), source_id),
        mime_type=_text(
            _read(value, "mime_type", "content_type"), "application/octet-stream"
        ),
    )


class FlightCardsGateway:
    """Translate the owning service's presentation objects for Atlas pages."""

    def __init__(self, service=None, *, unavailable_reason=None):
        self._service = service
        self.unavailable_reason = unavailable_reason

    @property
    def available(self):
        return self._service is not None

    def _operation(self, name):
        if self._service is None:
            raise FlightCardsUnavailable(
                self.unavailable_reason
                or "Flight Cards is not available in this build."
            )
        operation = getattr(self._service, name, None)
        if not callable(operation):
            raise FlightCardsUnavailable(
                f"Flight Cards does not provide the required {name} operation."
            )
        return operation

    def _call(self, name, *args, **kwargs):
        try:
            return self._operation(name)(*args, **kwargs)
        except FlightCardsUnavailable:
            raise
        except Exception as error:
            raise FlightCardsRequestError(
                "Atlas could not complete the Flight Cards request."
            ) from error

    def list_course_filters(self):
        return tuple(
            normalize_course_filter(item) for item in self._call("list_course_filters")
        )

    def list_flight_cards(self, *, course_id=None, course_state=None):
        cards = tuple(
            normalize_flight_card(item) for item in self._call("list_flight_cards")
        )
        if course_id is not None:
            cards = tuple(card for card in cards if card.course_id == course_id)
        if course_state is not None:
            cards = tuple(card for card in cards if card.course_state == course_state)
        return cards

    def get_flight_card(self, source_id):
        return normalize_flight_card(self._call("get_flight_card", source_id))

    def get_source_download(self, source_id):
        return normalize_source_download(
            self._call("get_source_download", source_id), source_id
        )

    def set_source_course(self, source_id, course_id):
        return self._call("set_source_course", source_id, course_id)

    def request_source_summary(self, source_id):
        return self._call("request_source_summary", source_id)


def load_flight_cards_gateway():
    """Discover only the canonical Flight Cards service, with honest fallback."""
    try:
        service = importlib.import_module(FLIGHT_CARDS_SERVICE_MODULE)
    except ModuleNotFoundError as error:
        if error.name != FLIGHT_CARDS_SERVICE_MODULE:
            return FlightCardsGateway(
                unavailable_reason="Flight Cards could not start in this build."
            )
        return FlightCardsGateway(
            unavailable_reason=(
                "Course and document summaries are waiting for the Flight Cards "
                "service to be added to this build."
            )
        )
    except Exception:
        return FlightCardsGateway(
            unavailable_reason="Flight Cards could not start in this build."
        )
    return FlightCardsGateway(service)
