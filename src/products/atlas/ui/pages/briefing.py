"""Source-grounded Atlas Briefing page."""

import streamlit as st

from products.atlas.briefing_service import create_study_briefing
from products.atlas.ui.components import render_evidence, render_hero


def render_briefing_page(product_context, course_id=None):
    render_hero(
        "Study Briefings",
        "Turn evidence into a practical plan.",
        "Atlas gathers supporting evidence, identifies verified facts, and proposes traceable study actions.",
    )
    if course_id:
        st.info(
            f"Opened from course context: {course_id}. Briefing follows the topic you enter; its owning service does not prove course-only retrieval.",
            icon="ℹ️",
        )
    briefing_topic = st.text_input(
        "What should Atlas prepare you for?",
        placeholder="Example: Prepare me for Fall Module A.",
    )
    if st.button(
        "Create Briefing", type="primary", disabled=not briefing_topic.strip()
    ):
        try:
            with st.spinner("Atlas is gathering evidence and preparing your briefing…"):
                st.session_state.briefing_result = create_study_briefing(
                    briefing_topic, product_context=product_context
                )
        except Exception as error:
            st.error(f"Atlas could not create the briefing: {error}")

    result = st.session_state.get("briefing_result")
    if not result:
        st.caption("Your generated briefing will appear here.")
        return
    if result.get("persistence", {}).get("status") == "failed":
        st.warning("This briefing was generated but could not be saved.", icon="⚠️")

    briefing = result["briefing"]
    st.divider()
    st.header(briefing["title"])
    st.write(briefing["overview"])
    st.subheader("Verified facts")
    for fact in briefing["verified_facts"]:
        st.markdown(f"**{fact['category']}** — {fact['fact']}")
        st.caption("Evidence: " + ", ".join(fact["evidence_refs"]))
    st.subheader("Recommended actions")
    for action in briefing["recommended_actions"]:
        st.markdown(f"**{action['priority']} priority — {action['action']}**")
        st.write(action["rationale"])
        st.caption("Based on evidence: " + ", ".join(action["evidence_refs"]))
    if briefing["open_questions"]:
        st.subheader("Open questions")
        for question in briefing["open_questions"]:
            st.markdown(f"**{question['question']}**")
            st.write(question["why_it_matters"])
    st.subheader("Supporting sources")
    for reference, source in result["evidence_reference_map"].items():
        st.markdown(f"**{reference} — {source.get('location') or 'Unknown location'}**")
        if source.get("heading"):
            st.write(source["heading"])
    with st.expander("View complete source evidence"):
        render_evidence(result["evidence"], key_prefix="briefing")
