"""Persistent Atlas shell and primary navigation."""

from html import escape

import streamlit as st

from products.atlas.ui.navigation import (
    PRIMARY_NAVIGATION,
    navigate,
    primary_page_for,
)


def render_sidebar(product, state, gateway):
    """Render one persistent, keyboard-accessible navigation surface."""
    with st.sidebar:
        st.markdown(
            "<div class='atlas-brand'>"
            "<div class='atlas-brand__eyebrow'>Academic Wingman</div>"
            f"<div class='atlas-brand__name'>{escape(product.call_sign)}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        active_page = primary_page_for(state.page)
        labels = [label for label, _page in PRIMARY_NAVIGATION]
        pages_by_label = dict(PRIMARY_NAVIGATION)
        active_label = next(
            label for label, page in PRIMARY_NAVIGATION if page is active_page
        )
        selected = st.radio(
            "Navigate Atlas",
            labels,
            index=labels.index(active_label),
            key=f"atlas_navigation_{active_page.value}",
        )
        if selected != active_label:
            selected_page = pages_by_label[selected]
            context_course = (
                state.course_id if selected_page.value in {"chat", "briefing"} else None
            )
            navigate(selected_page, course_id=context_course)

        st.divider()
        if gateway.available:
            st.success("Flight Cards connected", icon="✅")
        else:
            st.warning("Flight Cards unavailable", icon="⚠️")
        st.caption("Atlas keeps every answer and summary connected to its source.")
