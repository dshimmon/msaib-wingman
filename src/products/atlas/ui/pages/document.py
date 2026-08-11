"""Dedicated Flight Card document page."""

from urllib.parse import urlparse

import streamlit as st

from products.atlas.library_management_service import (
    remove_library_source,
    reprocess_library_source,
)
from products.atlas.ui.components import (
    consume_flash,
    render_dependency_unavailable,
    render_hero,
    render_status,
    set_flash,
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


def _valid_external_url(url):
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _render_source_access(gateway, card):
    st.subheader("Original source")
    st.write(
        "Open the source before relying on any derived summary. Summary failures never remove source access."
    )
    link = card.source_link
    if link.kind == "external_url" and _valid_external_url(link.url):
        st.link_button(link.label or "Open source", link.url, type="primary")
        return
    if link.kind == "download":
        try:
            download = gateway.get_source_download(card.source_id)
        except (FlightCardsUnavailable, FlightCardsRequestError) as error:
            st.warning(str(error), icon="⚠️")
            return
        st.download_button(
            link.label or "Download source",
            data=download.data,
            file_name=download.file_name,
            mime=download.mime_type,
            type="primary",
        )
        return
    st.warning("The original source is currently unavailable.", icon="⚠️")


def _render_summary(card):
    st.subheader("AI-generated summary")
    st.markdown(
        "<div class='atlas-provenance'>This summary is AI-generated and source-grounded. Verify important details against the original source and cited evidence.</div>",
        unsafe_allow_html=True,
    )
    render_status(card.summary_status, summary=True)
    if card.summary_status in {"failed", "stale"}:
        st.warning(
            card.safe_failure_message
            or (
                "The summary is out of date; the source remains available."
                if card.summary_status == "stale"
                else "The summary could not be created; the source remains available."
            ),
            icon="⚠️",
        )
    if not card.summary_points:
        st.info("No summary points are available yet.", icon="ℹ️")
    for point_index, point in enumerate(card.summary_points, start=1):
        with st.container(border=True):
            st.markdown(f"**{point_index}. {point.text}**")
            if point.evidence_refs:
                st.caption("Evidence: " + ", ".join(point.evidence_refs))


def _render_evidence_map(card):
    if not card.evidence_map:
        return
    st.subheader("Summary evidence")
    for reference, evidence in card.evidence_map.items():
        with st.container(border=True):
            st.markdown(f"**{reference}**")
            if isinstance(evidence, dict):
                location = evidence.get("location")
                heading = evidence.get("heading")
                excerpt = evidence.get("text") or evidence.get("excerpt")
                if location:
                    st.caption(f"Location: {location}")
                if heading:
                    st.write(heading)
                if excerpt:
                    st.write(excerpt)
            else:
                st.write(evidence)


def _render_provenance(card):
    st.subheader("Provenance")
    st.write(f"Source ID: `{card.source_id}`")
    values = (
        ("Source hash", card.source_hash),
        ("Summary source hash", card.summary_source_hash),
        ("Generator", card.generator_version),
        ("Prompt", card.prompt_version),
        ("Generated", card.generated_at),
    )
    for label, value in values:
        st.write(f"{label}: `{value}`" if value else f"{label}: Not provided")


def _assignment_options(filters):
    options = [option for option in filters if option.kind != "all"]
    if not any(option.kind == "unassigned" for option in options):
        from products.atlas.ui.flight_cards import CourseFilterOption

        options.append(
            CourseFilterOption(
                kind="unassigned", course_id=None, label="Unassigned", document_count=0
            )
        )
    return options


def _render_actions(gateway, card, product_context):
    st.subheader("Allowed actions")
    action_visible = False
    if card.can_request_summary:
        action_visible = True
        if st.button(
            (
                "Generate summary"
                if card.summary_status == "missing"
                else "Refresh summary"
            ),
            type="primary",
        ):
            try:
                gateway.request_source_summary(card.source_id)
                set_flash("Summary request accepted.")
                st.rerun()
            except (FlightCardsUnavailable, FlightCardsRequestError) as error:
                st.error(str(error))

    if card.can_set_course:
        action_visible = True
        try:
            filters = gateway.list_course_filters()
            options = _assignment_options(filters)
        except (FlightCardsUnavailable, FlightCardsRequestError) as error:
            st.warning(str(error))
            options = ()
        if options:
            current_index = next(
                (
                    index
                    for index, option in enumerate(options)
                    if option.course_id == card.course_id
                    and option.kind == card.course_state
                ),
                0,
            )
            selected = st.selectbox(
                "Course assignment",
                options,
                index=current_index,
                format_func=lambda option: option.label,
            )
            if st.button("Save course assignment"):
                try:
                    gateway.set_source_course(card.source_id, selected.course_id)
                    set_flash("Course assignment updated.")
                    st.rerun()
                except (FlightCardsUnavailable, FlightCardsRequestError) as error:
                    st.error(str(error))

    management_columns = st.columns(2)
    with management_columns[0]:
        if card.can_reprocess:
            action_visible = True
            if st.button("Reprocess source", use_container_width=True):
                try:
                    with st.spinner("Atlas is rebuilding this source…"):
                        result = reprocess_library_source(
                            card.source_id, product_context=product_context
                        )
                    set_flash(
                        f"Reprocessed {result['knowledge_object_count']} knowledge units."
                    )
                    st.rerun()
                except Exception as error:
                    st.error(f"Atlas could not reprocess this source: {error}")
    with management_columns[1]:
        if card.can_remove:
            action_visible = True
            confirmation = st.text_input(
                "Type REMOVE to confirm",
                key=f"document_remove_confirm_{card.source_id}",
            )
            if st.button(
                "Remove source",
                disabled=confirmation.strip().upper() != "REMOVE",
                use_container_width=True,
            ):
                try:
                    result = remove_library_source(
                        card.source_id, product_context=product_context
                    )
                    if result["cleanup_warning"]:
                        set_flash(result["cleanup_warning"], "warning")
                    else:
                        set_flash(f"Removed “{result['display_name']}”.")
                    navigate(AtlasPage.LIBRARY)
                except Exception as error:
                    st.error(f"Atlas could not remove this source: {error}")
    if not action_visible:
        st.caption("No mutations are allowed for this document.")


def render_document_page(gateway, source_id, product_context):
    if not gateway.available:
        render_hero(
            "Document",
            "Document presentation is unavailable.",
            "This link is valid, but its Flight Card cannot be loaded in this build.",
        )
        render_dependency_unavailable(gateway.unavailable_reason)
        return
    try:
        with st.spinner("Loading the document…"):
            card = gateway.get_flight_card(source_id)
    except FlightCardsUnavailable as error:
        render_dependency_unavailable(str(error))
        return
    except FlightCardsRequestError as error:
        st.error(str(error), icon="⚠️")
        if st.button("Back to Course Cockpit"):
            navigate(AtlasPage.COCKPIT)
        return

    render_hero(
        card.course_label,
        card.display_name,
        "Review source health, original access, AI-derived summary, citations, provenance, and only the actions this document allows.",
    )
    consume_flash()
    if st.button("← Back to course"):
        navigate(
            AtlasPage.COURSE,
            course_id=card.course_id or UNASSIGNED_COURSE_ID,
        )

    status_columns = st.columns(2)
    with status_columns[0]:
        render_status(card.source_status)
    with status_columns[1]:
        render_status(card.summary_status, summary=True)

    metric_columns = st.columns(4)
    metric_columns[0].metric("Knowledge units", card.knowledge_object_count)
    metric_columns[1].metric("Concepts", card.concept_count)
    metric_columns[2].metric("Records", card.record_count)
    metric_columns[3].metric("Embeddings", card.embedding_count)

    _render_source_access(gateway, card)
    st.divider()
    _render_summary(card)
    _render_evidence_map(card)
    st.divider()
    _render_provenance(card)
    st.divider()
    _render_actions(gateway, card, product_context)
