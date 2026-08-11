"""Honest navigation seam for the not-yet-contracted Practice Test."""

import streamlit as st

from products.atlas.ui.components import render_hero
from products.atlas.ui.navigation import AtlasPage, navigate


def render_practice_test_page(course_id):
    render_hero(
        "Practice Test",
        "Assessment is not available yet.",
        "This page reserves a stable course entry point without inventing questions, scoring, attempts, storage, or assessment behavior.",
    )
    st.warning(
        "Practice Test is waiting for an approved owning service contract.",
        icon="⚠️",
    )
    st.write(f"Course context: {course_id}")
    st.caption(
        "Full Practice Test acceptance remains blocked. No assessment data has been created or stored."
    )
    action_columns = st.columns(2)
    if action_columns[0].button(
        "Back to course", type="primary", use_container_width=True
    ):
        navigate(AtlasPage.COURSE, course_id=course_id)
    if action_columns[1].button("Ask Atlas instead", use_container_width=True):
        navigate(AtlasPage.CHAT, course_id=course_id)
