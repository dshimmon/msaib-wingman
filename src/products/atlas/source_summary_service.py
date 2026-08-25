"""Generate and persist source-grounded Atlas document summaries."""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


SUMMARY_SCHEMA_VERSION = 1
# Processed knowledge loaders intentionally reserve ``*.json`` below
# ``data/documents`` for lists of neutral knowledge objects.
SUMMARY_FILE_NAME = "source-summary.atlas"
SUMMARY_MODEL = "gpt-5"
SUMMARY_GENERATOR_VERSION = "atlas-source-summary-v1"
SUMMARY_PROMPT_VERSION = "atlas-source-summary-1-to-2-pages-v1"
SUMMARY_TARGET_MIN_WORDS = 450
SUMMARY_TARGET_MAX_WORDS = 900
SUMMARY_ABSOLUTE_MAX_WORDS = 1000
MIN_SOURCE_WORDS_FOR_FULL_LENGTH = 700
MAX_EVIDENCE_UNITS = 160
MAX_EVIDENCE_UNITS_FOR_FULL_LENGTH = 800
MAX_EVIDENCE_CHARACTERS = 120_000
MAX_EVIDENCE_EXCERPT_CHARACTERS = 1200

SAFE_FAILURE_TITLE = "Summary unavailable"
SAFE_FAILURE_MESSAGE = (
    "Atlas could not create this summary. The original source remains "
    "available; retry when AI generation is available."
)
SUMMARY_STATUS_METADATA_KEY = "atlas_summary_status"
SUMMARY_ATTEMPTED_STATES = frozenset({"pending", "ready", "failed"})


class SummaryGenerationError(RuntimeError):
    """A source summary could not be generated or validated."""


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def summary_path_for_original(original_path):
    """Keep a derived summary beside its source-identified upload artifacts."""
    original_path = Path(original_path)
    if original_path.is_symlink():
        raise ValueError("The original source cannot be a symbolic link.")
    return original_path.parent / SUMMARY_FILE_NAME


def _word_count(value):
    return len(str(value or "").split())


def processed_knowledge_hash(knowledge_objects):
    """Return a stable digest for the complete processed-knowledge payload."""
    if knowledge_objects is None:
        return None
    try:
        canonical = json.dumps(
            knowledge_objects,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def source_content_hash(original_path):
    """Hash the current registered original without trusting registry history."""
    digest = hashlib.sha256()
    with Path(original_path).open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _readable_units(knowledge_objects):
    return [
        item
        for item in knowledge_objects or ()
        if isinstance(item, dict) and str(item.get("text") or "").strip()
    ]


def _selected_units(readable_units):
    if len(readable_units) <= MAX_EVIDENCE_UNITS:
        return readable_units

    selection_limit = min(
        len(readable_units),
        MAX_EVIDENCE_UNITS_FOR_FULL_LENGTH,
    )
    selected_count = MAX_EVIDENCE_UNITS
    while True:
        last_index = len(readable_units) - 1
        indexes = {
            round(index * last_index / (selected_count - 1))
            for index in range(selected_count)
        }
        selected_units = [readable_units[index] for index in sorted(indexes)]
        if (
            selected_count >= selection_limit
            or sum(_word_count(item.get("text")) for item in selected_units)
            >= MIN_SOURCE_WORDS_FOR_FULL_LENGTH
        ):
            return selected_units
        selected_count = min(
            selection_limit,
            selected_count + MAX_EVIDENCE_UNITS,
        )


def build_evidence_catalog(knowledge_objects):
    """Build bounded, document-wide evidence for one summary request."""
    readable_units = _readable_units(knowledge_objects)
    source_word_count = sum(_word_count(item.get("text")) for item in readable_units)
    selected_units = _selected_units(readable_units)
    if not selected_units:
        raise SummaryGenerationError(
            "A summary requires readable source-backed knowledge."
        )

    per_unit_limit = max(
        200,
        min(6000, MAX_EVIDENCE_CHARACTERS // len(selected_units)),
    )
    evidence_map = {}
    evidence_sections = []
    remaining_characters = MAX_EVIDENCE_CHARACTERS

    for evidence_number, item in enumerate(selected_units, start=1):
        if remaining_characters <= 0:
            break
        reference = f"E{evidence_number}"
        full_text = str(item.get("text") or "").strip()
        text = full_text[: min(per_unit_limit, remaining_characters)]
        remaining_characters -= len(text)
        heading = item.get("heading") or item.get("section")
        location = item.get("location")
        source_id = item.get("document")
        evidence_map[reference] = {
            "source": source_id,
            "knowledge_id": item.get("id"),
            "location": location,
            "heading": heading,
            "excerpt": text[:MAX_EVIDENCE_EXCERPT_CHARACTERS],
        }
        evidence_sections.append(
            "\n".join(
                (
                    f"Evidence Reference: {reference}",
                    f"Source: {source_id}",
                    f"Location: {location}",
                    f"Heading: {heading}",
                    "Text:",
                    text,
                )
            )
        )

    if not evidence_map:
        raise SummaryGenerationError(
            "A summary requires readable source-backed knowledge."
        )
    return evidence_map, "\n\n".join(evidence_sections), source_word_count


def _summary_prompt(evidence_catalog, source_word_count):
    length_rule = (
        f"Write approximately {SUMMARY_TARGET_MIN_WORDS}–"
        f"{SUMMARY_TARGET_MAX_WORDS} words (roughly 1–2 pages)."
        if source_word_count >= MIN_SOURCE_WORDS_FOR_FULL_LENGTH
        else (
            "The source is shorter than a full-length summary target. Summarize "
            "it proportionately; never repeat or pad content to reach a word count."
        )
    )
    return f"""
You are Academic Wingman — Atlas.

Create a study-ready summary of exactly one uploaded document using only the
source evidence below.

{length_rule}

SUMMARY RULES

- Cover the document's central ideas, important details, relationships, and
  explicit requirements or dates that matter for study.
- Never invent, infer, or import facts that are absent from the evidence.
- Preserve qualifications and uncertainty from the source.
- Organize the summary into clear prose paragraphs, not isolated bullet facts.
- Every paragraph must cite at least one supplied evidence reference.
- Use only supplied evidence reference IDs. Do not place citation markers in
  paragraph text; return them in each paragraph's evidence_refs field.
- Do not add a bibliography. Atlas separately displays the evidence map and
  preserves access to the original document.

SOURCE EVIDENCE

{evidence_catalog}
""".strip()


def _response_schema(allowed_references):
    return {
        "type": "json_schema",
        "name": "atlas_source_summary",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "paragraphs": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 12,
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "evidence_refs": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "type": "string",
                                    "enum": list(allowed_references),
                                },
                            },
                        },
                        "required": ["text", "evidence_refs"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["title", "paragraphs"],
            "additionalProperties": False,
        },
    }


def _response_client(response_client=None):
    if response_client is not None:
        return response_client
    if not os.getenv("OPENAI_API_KEY"):
        raise SummaryGenerationError(
            "AI summary generation is not configured in this environment."
        )
    from wingman.core.openai_client import client

    return client


def _generate_summary(
    knowledge_objects,
    *,
    response_client=None,
):
    evidence_map, evidence_catalog, source_word_count = build_evidence_catalog(
        knowledge_objects
    )
    prompt = _summary_prompt(evidence_catalog, source_word_count)
    response = _response_client(response_client).responses.create(
        model=SUMMARY_MODEL,
        input=prompt,
        text={"format": _response_schema(evidence_map)},
    )
    try:
        payload = json.loads(response.output_text)
    except (AttributeError, TypeError, json.JSONDecodeError) as error:
        raise SummaryGenerationError(
            "The summary generator returned unreadable output."
        ) from error

    title = str(payload.get("title") or "").strip()
    paragraphs = payload.get("paragraphs")
    if not title or not isinstance(paragraphs, list) or not paragraphs:
        raise SummaryGenerationError(
            "The summary generator returned an incomplete summary."
        )

    allowed_references = set(evidence_map)
    normalized_points = []
    for paragraph in paragraphs:
        if not isinstance(paragraph, dict):
            raise SummaryGenerationError(
                "The summary generator returned an invalid paragraph."
            )
        text = str(paragraph.get("text") or "").strip()
        references = tuple(
            dict.fromkeys(
                str(reference).strip()
                for reference in paragraph.get("evidence_refs") or ()
                if str(reference).strip()
            )
        )
        if (
            not text
            or not references
            or any(reference not in allowed_references for reference in references)
        ):
            raise SummaryGenerationError(
                "The summary generator returned an ungrounded paragraph."
            )
        normalized_points.append({"text": text, "evidence_refs": list(references)})

    summary_word_count = sum(_word_count(point["text"]) for point in normalized_points)
    if summary_word_count > SUMMARY_ABSOLUTE_MAX_WORDS:
        raise SummaryGenerationError(
            "The generated summary exceeded the supported length."
        )
    if (
        source_word_count >= MIN_SOURCE_WORDS_FOR_FULL_LENGTH
        and summary_word_count < SUMMARY_TARGET_MIN_WORDS
    ):
        raise SummaryGenerationError(
            "The generated summary did not reach the 1–2 page target."
        )
    if (
        source_word_count < MIN_SOURCE_WORDS_FOR_FULL_LENGTH
        and summary_word_count > source_word_count
    ):
        raise SummaryGenerationError(
            "The generated summary was not proportional to the short source."
        )

    return {
        "title": title,
        "points": normalized_points,
        "evidence_map": evidence_map,
        "word_count": summary_word_count,
        "source_word_count": source_word_count,
    }


def _write_artifact(path, artifact):
    path = Path(path)
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise FileNotFoundError(
            "The registered source directory is no longer available."
        )
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(artifact, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except Exception:
        try:
            if temporary_path.exists():
                temporary_path.unlink()
        except Exception:
            pass
        raise


def _base_artifact(source_id, source_hash, knowledge_hash, generated_at):
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_id": source_id,
        "source_hash": source_hash,
        "knowledge_hash": knowledge_hash,
        "generator_version": SUMMARY_GENERATOR_VERSION,
        "prompt_version": SUMMARY_PROMPT_VERSION,
        "model": SUMMARY_MODEL,
        "generated_at": generated_at,
        "target_length": "approximately_1_to_2_pages",
        "target_word_range": [
            SUMMARY_TARGET_MIN_WORDS,
            SUMMARY_TARGET_MAX_WORDS,
        ],
    }


def generate_and_persist_summary(
    *,
    source_id,
    source_hash,
    original_path,
    knowledge_objects,
    response_client=None,
    clock=utc_now,
):
    """Attempt one summary without making source availability depend on AI."""
    generated_at = clock()
    knowledge_hash = processed_knowledge_hash(knowledge_objects)
    current_source_hash = None
    try:
        current_source_hash = source_content_hash(original_path)
        if not source_hash or source_hash != current_source_hash:
            raise SummaryGenerationError(
                "The registered source hash does not match the current original."
            )
        if knowledge_hash is None:
            raise SummaryGenerationError(
                "Processed knowledge could not be bound to this summary."
            )
        base = _base_artifact(
            source_id,
            current_source_hash,
            knowledge_hash,
            generated_at,
        )
        generated = _generate_summary(
            knowledge_objects,
            response_client=response_client,
        )
        artifact = {
            **base,
            "status": "ready",
            **generated,
        }
    except Exception:
        base = _base_artifact(
            source_id,
            current_source_hash or source_hash,
            knowledge_hash,
            generated_at,
        )
        artifact = {
            **base,
            "status": "failed",
            "title": None,
            "points": [],
            "evidence_map": {},
            "word_count": 0,
            "safe_failure": {
                "title": SAFE_FAILURE_TITLE,
                "message": SAFE_FAILURE_MESSAGE,
            },
        }

    _write_artifact(summary_path_for_original(original_path), artifact)
    return artifact


def _summary_state(status, *, failure_message=None):
    return {
        "summary_status": status,
        "summary_title": None,
        "summary_points": (),
        "summary_source_hash": None,
        "summary_knowledge_hash": None,
        "generator_version": None,
        "prompt_version": None,
        "generated_at": None,
        "evidence_map": {},
        "safe_failure_title": SAFE_FAILURE_TITLE if failure_message else None,
        "safe_failure_message": failure_message,
    }


def _missing_summary_state(attempted_status):
    if attempted_status in SUMMARY_ATTEMPTED_STATES:
        return _summary_state("failed", failure_message=SAFE_FAILURE_MESSAGE)
    return _summary_state("missing")


def load_persisted_summary(
    *,
    source_id,
    source_hash,
    original_path,
    knowledge_objects=None,
    attempted_status=None,
):
    """Load one saved summary as the Flight Cards presentation contract."""
    if not original_path:
        return _missing_summary_state(attempted_status)
    try:
        path = summary_path_for_original(original_path)
    except (OSError, ValueError):
        return _summary_state("failed", failure_message=SAFE_FAILURE_MESSAGE)
    if not path.is_file() or path.is_symlink():
        return _missing_summary_state(attempted_status)
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _summary_state("failed", failure_message=SAFE_FAILURE_MESSAGE)
    if (
        not isinstance(artifact, dict)
        or artifact.get("schema_version") != SUMMARY_SCHEMA_VERSION
        or artifact.get("source_id") != source_id
    ):
        return _summary_state("failed", failure_message=SAFE_FAILURE_MESSAGE)

    status = artifact.get("status")
    failure = artifact.get("safe_failure")
    if status == "failed":
        return {
            **_summary_state("failed", failure_message=SAFE_FAILURE_MESSAGE),
            "summary_source_hash": artifact.get("source_hash"),
            "summary_knowledge_hash": artifact.get("knowledge_hash"),
            "generator_version": artifact.get("generator_version"),
            "prompt_version": artifact.get("prompt_version"),
            "generated_at": artifact.get("generated_at"),
            "safe_failure_title": (
                failure.get("title")
                if isinstance(failure, dict) and failure.get("title")
                else SAFE_FAILURE_TITLE
            ),
        }
    if status != "ready":
        return _summary_state("failed", failure_message=SAFE_FAILURE_MESSAGE)

    points = artifact.get("points")
    evidence_map = artifact.get("evidence_map")
    if not isinstance(points, list) or not isinstance(evidence_map, dict):
        return _summary_state("failed", failure_message=SAFE_FAILURE_MESSAGE)
    current_knowledge_hash = processed_knowledge_hash(knowledge_objects)
    try:
        current_source_hash = source_content_hash(original_path)
    except (OSError, ValueError):
        return _summary_state("failed", failure_message=SAFE_FAILURE_MESSAGE)
    stored_knowledge_hash = artifact.get("knowledge_hash")
    summary_status = (
        "ready"
        if isinstance(source_hash, str)
        and bool(source_hash)
        and artifact.get("source_hash") == source_hash
        and source_hash == current_source_hash
        and isinstance(stored_knowledge_hash, str)
        and bool(stored_knowledge_hash)
        and stored_knowledge_hash == current_knowledge_hash
        else "stale"
    )
    return {
        "summary_status": summary_status,
        "summary_title": artifact.get("title"),
        "summary_points": points,
        "summary_source_hash": artifact.get("source_hash"),
        "summary_knowledge_hash": artifact.get("knowledge_hash"),
        "generator_version": artifact.get("generator_version"),
        "prompt_version": artifact.get("prompt_version"),
        "generated_at": artifact.get("generated_at"),
        "evidence_map": evidence_map,
        "safe_failure_title": (
            "Summary out of date" if summary_status == "stale" else None
        ),
        "safe_failure_message": (
            "The source or its processed knowledge changed after this summary "
            "was generated. Refresh the summary before relying on it."
            if summary_status == "stale"
            else None
        ),
    }
