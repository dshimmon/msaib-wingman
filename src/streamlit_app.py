# Browser interface for Academic Wingman — Atlas.

# Run with: python -m streamlit run src/streamlit_app.py

from datetime import datetime
from pathlib import Path
from library_management_service import (
    remove_library_source,
    reprocess_library_source,
)


import streamlit as st

from intake_service import (
    create_display_name,
    ingest_uploaded_document,
)
from library_service import list_library_sources
from wingman_service import ask_wingman


st.set_page_config(
    page_title="Atlas | Wingman",
    page_icon="🪿",
    layout="wide",
)


def format_uploaded_at(uploaded_at):
    """
    Convert an ISO upload timestamp into readable text.
    """
    if not uploaded_at:
        return None

    try:
        timestamp = datetime.fromisoformat(
            uploaded_at.replace("Z", "+00:00")
        )

        return timestamp.strftime(
            "%B %d, %Y at %I:%M %p UTC"
        )
    except ValueError:
        return uploaded_at


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


def display_library_source(source, source_index):
    """
    Display one registered source inside the Library.
    """
    display_name = source["display_name"]
    status = source["status"]

    with st.expander(
        f"{display_name} — {status}"
    ):
        file_type = source.get("file_type")
        domain = source.get("domain")
        program = source.get("program")
        academic_year = source.get(
            "academic_year"
        )

        source_details = [
            detail
            for detail in [
                file_type.upper()
                if file_type
                else None,
                domain,
                program,
                academic_year,
            ]
            if detail
        ]

        if source_details:
            st.caption(
                " • ".join(source_details)
            )

        if status == "Ready":
            st.success(
                "This source is ready for Atlas."
            )
        elif status == "Partially indexed":
            st.warning(
                "This source is only partially indexed."
            )
        else:
            st.error(
                f"Source status: {status}"
            )

        metric_columns = st.columns(4)

        metric_columns[0].metric(
            "Knowledge Units",
            source["knowledge_object_count"],
        )

        metric_columns[1].metric(
            "Concepts",
            source["concept_count"],
        )

        metric_columns[2].metric(
            "Records",
            source["record_count"],
        )

        metric_columns[3].metric(
            "Embeddings",
            source["embedding_count"],
        )

        st.markdown("#### Source Details")

        st.write(
            f"**Original file:** "
            f"{source.get('file_name') or 'Unknown'}"
        )

        st.write(
            f"**Internal source ID:** "
            f"`{source['source_id']}`"
        )

        uploaded_at = format_uploaded_at(
            source.get("uploaded_at")
        )

        if uploaded_at:
            st.write(
                f"**Uploaded:** {uploaded_at}"
            )

        source_url = source.get("source_url")
        original_path = source.get(
            "original_path"
        )

        if source_url:
            st.link_button(
                "Open Original Source",
                source_url,
            )
        elif (
            original_path
            and source["original_available"]
        ):
            source_path = Path(original_path)

            st.download_button(
                label="Download Original Source",
                data=source_path.read_bytes(),
                file_name=(
                    source.get("file_name")
                    or source_path.name
                ),
                mime="application/octet-stream",

                key=(
                    f"library_download_"
                    f"{source_index}_"
                    f"{source['source_id']}"
                ),
            )
        else:
            st.caption(
                "The original source file is unavailable."
            )

        st.divider()
        st.markdown("#### Manage Source")

        action_columns = st.columns(2)

        with action_columns[0]:
            if source["can_reprocess"]:
                if st.button(
                    "Reprocess Source",
                    key=(
                        f"reprocess_"
                        f"{source['source_id']}"
                    ),
                ):
                    try:
                        with st.spinner(
                            "Atlas is rebuilding this source..."
                        ):
                            result = (
                                reprocess_library_source(
                                    source["source_id"]
                                )
                            )

                        st.success(
                            "Reprocessed "
                            f"{result['knowledge_object_count']} "
                            "knowledge units."
                        )

                        st.rerun()

                    except Exception as error:
                        st.error(
                            "Atlas could not reprocess "
                            f"this source: {error}"
                        )
            else:
                st.caption(
                    "Reprocessing is unavailable because "
                    "the original file cannot be found."
                )

            with action_columns[1]:
                if source["can_remove"]:
                    confirmation_key = (
                        f"confirm_remove_"
                        f"{source['source_id']}"
                    )

                    confirmation_text = st.text_input(
                        "Type REMOVE to confirm",
                        key=confirmation_key,
                    )

                    remove_confirmed = (
                        confirmation_text.strip().upper()
                        == "REMOVE"
                    )

                    if st.button(
                        "Remove Source",
                        type="secondary",
                        disabled=not remove_confirmed,
                        key=(
                            f"remove_"
                            f"{source['source_id']}"
                        ),
                    ):
                        try:
                            result = remove_library_source(
                                source["source_id"]
                            )

                            if result["cleanup_warning"]:
                                st.warning(
                                    result["cleanup_warning"]
                                )
                            else:
                                st.success(
                                    f"Removed “{result['display_name']}”."
                                )

                            st.rerun()

                        except Exception as error:
                            st.error(
                                "Atlas could not remove "
                                f"this source: {error}"
                            )
                else:
                    st.caption(
                        "Repository sources are protected "
                        "and cannot be removed."
                    )


def display_library_workspace():
    """
    Display Atlas's registered knowledge sources.
    """
    st.title("Atlas Library")
    st.caption(
        "Everything currently registered in "
        "Academic Wingman."
    )

    try:
        sources = list_library_sources()
    except Exception as error:
        st.error(
            "Atlas could not load the Library: "
            f"{error}"
        )
        return

    if not sources:
        st.info(
            "Atlas does not have any registered "
            "sources yet."
        )
        return

    total_knowledge_units = sum(
        source["knowledge_object_count"]
        for source in sources
    )

    total_records = sum(
        source["record_count"]
        for source in sources
    )

    total_embeddings = sum(
        source["embedding_count"]
        for source in sources
    )

    summary_columns = st.columns(4)

    summary_columns[0].metric(
        "Sources",
        len(sources),
    )

    summary_columns[1].metric(
        "Knowledge Units",
        total_knowledge_units,
    )

    summary_columns[2].metric(
        "Structured Records",
        total_records,
    )

    summary_columns[3].metric(
        "Embeddings",
        total_embeddings,
    )

    st.divider()
    st.subheader("Registered Sources")

    for source_index, source in enumerate(
        sources
    ):
        display_library_source(
            source,
            source_index,
        )


def display_chat_workspace():
    """
    Display Atlas's conversational workspace.
    """
    st.title("Academic Wingman")
    st.caption("Call Sign: Atlas")

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


with st.sidebar:
    st.markdown("## Academic Wingman")
    st.caption("Call Sign: Atlas")

    workspace = st.radio(
        "Workspace",
        [
            "Chat",
            "Library",
        ],
    )

    st.divider()
    st.header("Add Knowledge")

    uploaded_file = st.file_uploader(
        "Upload a document",
        type=[
            "pptx",
            "pdf",
            "docx",
            "xlsx",
        ],
    )

    if uploaded_file:
        default_display_name = (
            create_display_name(
                uploaded_file.name
            )
        )

        display_name = st.text_input(
            "Display name",
            value=default_display_name,
        )

        domain = st.text_input(
            "Domain",
            value="General",
        )

        program = st.text_input(
            "Program",
            placeholder="Optional",
        )

        academic_year = st.text_input(
            "Academic year",
            placeholder="Optional",
        )

        if st.button(
            "Add to Atlas",
            type="primary",
        ):
            try:
                with st.spinner(
                    "Atlas is processing the document..."
                ):
                    intake_result = (
                        ingest_uploaded_document(
                            file_name=uploaded_file.name,
                            file_bytes=(
                                uploaded_file.getvalue()
                            ),
                            display_name=display_name,
                            domain=domain,
                            program=program,
                            academic_year=academic_year,
                        )
                    )

                if (
                    intake_result["status"]
                    == "already_exists"
                ):
                    st.info(
                        "This document is already "
                        "in Atlas as "
                        f"“{intake_result['display_name']}”."
                    )
                else:
                    st.success(
                        "Added "
                        f"{intake_result['knowledge_object_count']} "
                        "knowledge units from "
                        f"“{intake_result['display_name']}”."
                    )

            except Exception as error:
                st.error(
                    "Atlas could not ingest this document: "
                    f"{error}"
                )


if workspace == "Library":
    display_library_workspace()
else:
    display_chat_workspace()