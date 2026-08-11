"""Source-grounded Atlas chat page."""

import streamlit as st

from products.atlas.ui.components import render_evidence, render_hero
from products.atlas.wingman_service import ask_wingman


def render_chat_page(product_context, course_id=None):
    product = product_context.product
    render_hero(
        "Ask Atlas",
        "Chat with your academic knowledge.",
        "Ask a question and inspect the supporting source evidence attached to every grounded answer.",
    )
    if course_id:
        st.info(
            f"Opened from course context: {course_id}. Chat currently searches authorized Atlas knowledge; course-only retrieval is not proven by its owning service.",
            icon="ℹ️",
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message_index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant":
                render_evidence(
                    message.get("evidence", []), key_prefix=f"history_{message_index}"
                )

    question = st.chat_input(f"Ask {product.call_sign} a question…")
    if not question:
        if not st.session_state.messages:
            st.caption(
                "Try asking about a schedule, concept, policy, or preparation task."
            )
        return

    user_message = {"role": "user", "content": question}
    st.session_state.messages.append(user_message)
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Atlas is reviewing the evidence…"):
                result = ask_wingman(
                    question,
                    conversation_history=st.session_state.messages,
                    product_context=product_context,
                )
        except Exception as error:
            st.error(f"Atlas could not answer this question: {error}")
            return
        st.write(result["answer"])
        render_evidence(
            result["evidence"],
            key_prefix=f"current_{len(st.session_state.messages)}",
        )
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "evidence": result["evidence"],
        }
    )
