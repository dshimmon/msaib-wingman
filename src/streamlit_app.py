# Browser interface for Academic Wingman — Atlas.

# Run with: python -m streamlit run src/streamlit_app.py

from pathlib import Path

import streamlit as st

from wingman_service import ask_wingman


st.set_page_config(
    page_title="Atlas | Wingman",
    page_icon="🪿",
)

st.title("Academic Wingman")
st.caption("Call Sign: Atlas")


def display_sources(evidence, key_prefix):
    """
    Display friendly source cards with access to
    the original source file.
    """
    if not evidence:
        return

    with st.expander("Supporting Sources"):
        for index, item in enumerate(evidence):
            metadata = item.get(
                "source_metadata",
                {},
            )

            source_id = metadata.get(
                "id",
                item.get("source"),
            )

            display_name = metadata.get(
                "display_name",
                source_id or "Unknown source",
            )

            location = (
                item.get("location")
                or "Unknown location"
            )

            file_type = metadata.get("file_type")
            program = metadata.get("program")
            academic_year = metadata.get(
                "academic_year"
            )

            st.markdown(
                f"### {display_name}"
            )

            st.markdown(
                f"**Location:** {location}"
            )

            source_details = [
                detail
                for detail in [
                    file_type.upper()
                    if file_type
                    else None,
                    program,
                    academic_year,
                ]
                if detail
            ]

            if source_details:
                st.caption(
                    " • ".join(source_details)
                )

            st.write(item.get("text", ""))

            source_url = metadata.get(
                "source_url"
            )

            original_path = metadata.get(
                "original_path"
            )

            if source_url:
                st.link_button(
                    "Open Original Source",
                    source_url,
                )
            elif original_path:
                source_path = Path(original_path)

                if source_path.exists():
                    st.download_button(
                        label="Download Original Source",
                        data=source_path.read_bytes(),
                        file_name=(
                            metadata.get("file_name")
                            or source_path.name
                        ),
                        mime=metadata.get(
                            "mime_type",
                            "application/octet-stream",
                        ),
                        key=(
                            f"{key_prefix}_"
                            f"{source_id}_"
                            f"{index}"
                        ),
                    )
                else:
                    st.caption(
                        "Original source file is unavailable."
                    )

            if index < len(evidence) - 1:
                st.divider()


if "messages" not in st.session_state:
    st.session_state.messages = []


for message_index, message in enumerate(
    st.session_state.messages
):
    with st.chat_message(message["role"]):
        st.write(message["content"])

        if message["role"] == "assistant":
            display_sources(
                message.get("evidence", []),
                key_prefix=(
                    f"history_{message_index}"
                ),
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

        display_sources(
            result["evidence"],
            key_prefix=(
                f"current_"
                f"{len(st.session_state.messages)}"
            ),
        )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "evidence": result["evidence"],
        }
    )