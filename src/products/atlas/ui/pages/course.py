"""Unified course materials and summaries page."""

import streamlit as st

from products.atlas.syllabus_intake import MATERIAL_TYPE_LABELS
from products.atlas.ui.components import (
    render_dependency_unavailable,
    render_hero,
    render_status,
)
from products.atlas.ui.flight_cards import (
    FlightCardsRequestError,
    FlightCardsUnavailable,
)
from products.atlas.ui.navigation import (
    AtlasPage,
    UNASSIGNED_COURSE_ID,
    navigate,
)


def _course_selection(course_id):
    if course_id == UNASSIGNED_COURSE_ID:
        return None, "unassigned"
    return course_id, None


def _course_label(gateway, selected_course_id, course_state):
    if course_state == "unassigned":
        return "Unassigned materials"
    if not gateway.available:
        return selected_course_id
    try:
        return next(
            option.label
            for option in gateway.list_course_filters()
            if option.course_id == selected_course_id
        )
    except (StopIteration, FlightCardsUnavailable, FlightCardsRequestError):
        return selected_course_id


def _render_material(card):
    with st.container(border=True):
        st.subheader(card.display_name)
        details = [card.file_type.upper() if card.file_type else None, card.file_name]
        if any(details):
            st.caption(" • ".join(detail for detail in details if detail))
        status_columns = st.columns(2)
        with status_columns[0]:
            render_status(card.source_status)
        with status_columns[1]:
            render_status(card.summary_status, summary=True)
        if card.summary_points:
            st.write(card.summary_points[0].text)
        elif card.summary_status == "failed":
            st.caption(card.safe_failure_message or "The summary could not be created.")
        else:
            st.caption("Open this material for source access and summary details.")
        if st.button(
            "Open document",
            key=f"course_document_{card.source_id}",
            use_container_width=True,
        ):
            navigate(
                AtlasPage.DOCUMENT,
                course_id=card.course_id or UNASSIGNED_COURSE_ID,
                source_id=card.source_id,
            )


def _render_summary(card):
    with st.container(border=True):
        st.markdown(f"#### {card.summary_title or card.display_name}")
        if card.summary_title and card.summary_title != card.display_name:
            st.caption(f"Source: {card.display_name}")
        render_status(card.summary_status, summary=True)
        if card.summary_status in {"failed", "stale"} and card.safe_failure_message:
            st.warning(card.safe_failure_message)
        if not card.summary_points:
            st.caption("No summary points are available yet.")
        for point in card.summary_points:
            st.write(point.text)
            if point.evidence_refs:
                st.caption("Evidence: " + ", ".join(point.evidence_refs))
        if st.button(
            "Open source and summary details",
            key=f"course_summary_{card.source_id}",
            use_container_width=True,
        ):
            navigate(
                AtlasPage.DOCUMENT,
                course_id=card.course_id or UNASSIGNED_COURSE_ID,
                source_id=card.source_id,
            )


def render_course_page(gateway, course_id):
    selected_course_id, course_state = _course_selection(course_id)
    label = _course_label(gateway, selected_course_id, course_state)
    render_hero(
        "Course catalog",
        label,
        "Syllabus, notes, lectures, homework, and other materials stay organized inside this course folder. Chat and Briefings open with course context, but their owning services do not prove course-only retrieval.",
    )

    if st.button("← Back to Course Cockpit"):
        navigate(AtlasPage.COCKPIT)

    action_columns = st.columns(3)
    if action_columns[0].button("Ask Atlas", type="primary", use_container_width=True):
        navigate(AtlasPage.CHAT, course_id=course_id)
    if action_columns[1].button("Create briefing", use_container_width=True):
        navigate(AtlasPage.BRIEFING, course_id=course_id)
    if action_columns[2].button("Practice Test", use_container_width=True):
        navigate(AtlasPage.PRACTICE_TEST, course_id=course_id)

    if not gateway.available:
        render_dependency_unavailable(gateway.unavailable_reason)
        return

    try:
        with st.spinner("Loading course materials…"):
            cards = gateway.list_flight_cards(
                course_id=selected_course_id,
                course_state=course_state,
            )
    except FlightCardsUnavailable as error:
        render_dependency_unavailable(str(error))
        return
    except FlightCardsRequestError as error:
        st.error(str(error), icon="⚠️")
        return

    if not cards:
        st.info("No materials are assigned here yet.", icon="ℹ️")
        if st.button("Add materials", type="primary"):
            navigate(AtlasPage.UPLOAD)
        return

    source_issues = sum(card.source_status != "ready" for card in cards)
    summary_issues = sum(card.summary_status in {"failed", "stale"} for card in cards)
    metric_columns = st.columns(3)
    metric_columns[0].metric("Materials", len(cards))
    metric_columns[1].metric(
        "Summaries ready", sum(card.summary_status == "ready" for card in cards)
    )
    metric_columns[2].metric("Needs attention", source_issues + summary_issues)
    if source_issues or summary_issues:
        st.warning(
            "Some materials or summaries need attention. Valid original sources remain available from each document page.",
            icon="⚠️",
        )

    cards_by_material_type = {
        material_type: [
            card for card in cards if card.material_type == material_type
        ]
        for material_type in MATERIAL_TYPE_LABELS
    }
    tab_labels = [
        f"{label} ({len(cards_by_material_type[material_type])})"
        for material_type, label in MATERIAL_TYPE_LABELS.items()
    ]
    folder_tabs = st.tabs([*tab_labels, f"Summaries ({len(cards)})"])
    for folder_tab, (material_type, label) in zip(
        folder_tabs,
        MATERIAL_TYPE_LABELS.items(),
    ):
        with folder_tab:
            folder_cards = cards_by_material_type[material_type]
            if not folder_cards:
                st.caption(f"No {label.lower()} have been added yet.")
            for card in folder_cards:
                _render_material(card)
    with folder_tabs[-1]:
        st.caption(
            "Summaries are AI-generated and grounded in the cited source evidence."
        )
        for card in cards:
            _render_summary(card)
