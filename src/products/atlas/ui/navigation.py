"""Stable Atlas page and deep-link state."""

from dataclasses import dataclass
from enum import Enum


UNASSIGNED_COURSE_ID = "_unassigned"
MAX_IDENTIFIER_LENGTH = 200


class AtlasPage(str, Enum):
    """Pages owned by the single-script Atlas Streamlit application."""

    COCKPIT = "cockpit"
    COURSE = "course"
    DOCUMENT = "document"
    CHAT = "chat"
    BRIEFING = "briefing"
    LIBRARY = "library"
    UPLOAD = "upload"
    PROMPT_OPTIMIZER = "prompt-optimizer"
    PRACTICE_TEST = "practice-test"


PRIMARY_NAVIGATION = (
    ("Course Cockpit", AtlasPage.COCKPIT),
    ("Chat", AtlasPage.CHAT),
    ("Briefings", AtlasPage.BRIEFING),
    ("Library", AtlasPage.LIBRARY),
    ("Add Materials", AtlasPage.UPLOAD),
    ("Prompt Optimizer", AtlasPage.PROMPT_OPTIMIZER),
)


@dataclass(frozen=True)
class NavigationState:
    """One validated page selection recovered from query parameters."""

    page: AtlasPage = AtlasPage.COCKPIT
    course_id: str | None = None
    source_id: str | None = None
    recovered: bool = False
    notice: str | None = None


def _first(value):
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def normalize_identifier(value):
    """Accept bounded opaque IDs while rejecting controls and empty values."""
    value = _first(value)
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value or len(value) > MAX_IDENTIFIER_LENGTH:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    return value


def parse_query_state(query_params):
    """Resolve a safe page state, recovering invalid deep links to Cockpit."""
    raw_page = normalize_identifier(query_params.get("page")) or AtlasPage.COCKPIT.value
    course_id = normalize_identifier(query_params.get("course"))
    source_id = normalize_identifier(query_params.get("source"))

    try:
        page = AtlasPage(raw_page)
    except ValueError:
        return NavigationState(
            recovered=True,
            notice="That Atlas link is not recognized. Course Cockpit is open instead.",
        )

    if page in {AtlasPage.COURSE, AtlasPage.PRACTICE_TEST} and not course_id:
        return NavigationState(
            recovered=True,
            notice="That course link is incomplete. Course Cockpit is open instead.",
        )
    if page is AtlasPage.DOCUMENT and not source_id:
        return NavigationState(
            recovered=True,
            notice="That document link is incomplete. Course Cockpit is open instead.",
        )

    return NavigationState(page=page, course_id=course_id, source_id=source_id)


def query_for(page, *, course_id=None, source_id=None):
    """Create the canonical query representation for a deep link."""
    values = {"page": AtlasPage(page).value}
    course_id = normalize_identifier(course_id)
    source_id = normalize_identifier(source_id)
    if course_id:
        values["course"] = course_id
    if source_id:
        values["source"] = source_id
    return values


def navigate(page, *, course_id=None, source_id=None):
    """Navigate within the single Streamlit script using stable identifiers."""
    import streamlit as st

    st.query_params.clear()
    st.query_params.update(query_for(page, course_id=course_id, source_id=source_id))
    st.rerun()


def primary_page_for(page):
    """Map a detail page to its persistent primary navigation section."""
    page = AtlasPage(page)
    if page in {
        AtlasPage.COURSE,
        AtlasPage.DOCUMENT,
        AtlasPage.PRACTICE_TEST,
    }:
        return AtlasPage.COCKPIT
    return page
