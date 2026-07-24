# Browser interface for Academic Wingman — Atlas.

import streamlit as st

from wingman_service import ask_wingman


st.set_page_config(
    page_title="Atlas | Wingman",
    page_icon="🪿",
)

st.title("Academic Wingman")
st.caption("Call Sign: Atlas")


def display_sources(evidence):
    """
    Display supporting evidence inside an expandable section.
    """
    if not evidence:
        return

    with st.expander("Supporting Sources"):
        for item in evidence:
            source = item.get("source") or "Unknown source"
            location = item.get("location") or "Unknown location"

            st.markdown(
                f"**{source} — {location}**"
            )
            st.write(item.get("text", ""))


if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

        if message["role"] == "assistant":
            display_sources(
                message.get("evidence", [])
            )


question = st.chat_input(
    "Ask Atlas a question..."
)

if question:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner(
            "Atlas is reviewing the evidence..."
        ):
            result = ask_wingman(question)

        st.write(result["answer"])
        display_sources(result["evidence"])

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "evidence": result["evidence"],
        }
    )