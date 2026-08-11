"""Course Cockpit landing page."""

from collections import Counter

import streamlit as st

from products.atlas.ui.components import (
    render_dependency_unavailable,
    render_hero,
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


def _open_course(option):
    course_id = (
        UNASSIGNED_COURSE_ID if option.kind == "unassigned" else option.course_id
    )
    navigate(AtlasPage.COURSE, course_id=course_id)


def render_cockpit_page(gateway):
    render_hero(
        "Course Cockpit",
        "Your courses, ready for takeoff.",
        "Open a course to review its materials and grounded summaries, or start with documents that still need a course.",
    )

    if not gateway.available:
        render_dependency_unavailable(gateway.unavailable_reason)
        action_columns = st.columns(2)
        if action_columns[0].button(
            "Open Library", type="primary", use_container_width=True
        ):
            navigate(AtlasPage.LIBRARY)
        if action_columns[1].button("Add materials", use_container_width=True):
            navigate(AtlasPage.UPLOAD)
        return

    try:
        with st.spinner("Loading your courses…"):
            filters = gateway.list_course_filters()
            cards = gateway.list_flight_cards()
    except FlightCardsUnavailable as error:
        render_dependency_unavailable(str(error))
        return
    except FlightCardsRequestError as error:
        st.error(str(error), icon="⚠️")
        st.caption("Your other Atlas workspaces are still available from navigation.")
        return

    course_options = [option for option in filters if option.kind != "all"]
    summary_counts = Counter(
        (
            card.course_id if card.course_state == "assigned" else None,
            card.summary_status,
        )
        for card in cards
    )
    total_documents = sum(option.document_count for option in course_options)
    ready_summaries = sum(card.summary_status == "ready" for card in cards)
    unassigned_count = next(
        (
            option.document_count
            for option in course_options
            if option.kind == "unassigned"
        ),
        0,
    )

    metric_columns = st.columns(3)
    metric_columns[0].metric("Materials", total_documents)
    metric_columns[1].metric("AI summaries ready", ready_summaries)
    metric_columns[2].metric("Unassigned", unassigned_count)

    st.header("Courses")
    if not course_options:
        st.info("No course groups are available yet.", icon="ℹ️")
        if st.button("Add your first materials", type="primary"):
            navigate(AtlasPage.UPLOAD)
        return

    for row_start in range(0, len(course_options), 3):
        columns = st.columns(3)
        for column, option in zip(columns, course_options[row_start : row_start + 3]):
            key_id = option.course_id or UNASSIGNED_COURSE_ID
            ready_count = summary_counts[(option.course_id, "ready")]
            with column.container(border=True):
                st.markdown(
                    "<div class='atlas-kicker'>"
                    + (
                        "Needs organization"
                        if option.kind == "unassigned"
                        else "Course"
                    )
                    + "</div>",
                    unsafe_allow_html=True,
                )
                st.subheader(option.label)
                st.write(f"{option.document_count} material(s)")
                st.caption(f"{ready_count} AI summary or summaries ready")
                if st.button(
                    f"Open {option.label}",
                    key=f"open_course_{key_id}",
                    type="primary" if option.kind != "unassigned" else "secondary",
                    use_container_width=True,
                ):
                    _open_course(option)
