"""Atlas Library presentation using its owning service boundary."""

from pathlib import Path

import streamlit as st

from products.atlas.library_management_service import (
    remove_library_source,
    reprocess_library_source,
)
from products.atlas.ui.components import format_uploaded_at, render_hero
from products.atlas.ui.navigation import AtlasPage, navigate
from wingman.shared.library_service import list_library_sources


def _render_source_access(source, source_index):
    source_url = source.get("source_url")
    original_path = source.get("original_path")
    if source_url:
        st.link_button("Open original source", source_url)
    elif original_path and source.get("original_available"):
        source_path = Path(original_path)
        try:
            st.download_button(
                "Download original source",
                data=source_path.read_bytes(),
                file_name=source.get("file_name") or source_path.name,
                mime="application/octet-stream",
                key=f"library_download_{source_index}_{source['source_id']}",
            )
        except OSError:
            st.caption("The original source file is unavailable.")
    else:
        st.caption("The original source file is unavailable.")


def _render_library_source(source, source_index, product_context):
    display_name = source["display_name"]
    status = source["status"]
    with st.expander(f"{display_name} — {status}"):
        details = [
            source.get("file_type", "").upper() or None,
            source.get("domain"),
            source.get("course_id"),
            source.get("program"),
            source.get("academic_year"),
        ]
        details = [detail for detail in details if detail]
        if details:
            st.caption(" • ".join(details))
        if status == "Ready":
            st.success("This source is ready for Atlas.", icon="✅")
        elif status == "Partially indexed":
            st.warning("This source is only partially indexed.", icon="⚠️")
        else:
            st.error(f"Source status: {status}", icon="⚠️")

        metric_columns = st.columns(4)
        metric_columns[0].metric("Knowledge units", source["knowledge_object_count"])
        metric_columns[1].metric("Concepts", source["concept_count"])
        metric_columns[2].metric("Records", source["record_count"])
        metric_columns[3].metric("Embeddings", source["embedding_count"])
        st.markdown("#### Source details")
        st.write(f"Original file: {source.get('file_name') or 'Unknown'}")
        st.write(f"Internal source ID: `{source['source_id']}`")
        uploaded_at = format_uploaded_at(source.get("uploaded_at"))
        if uploaded_at:
            st.write(f"Uploaded: {uploaded_at}")
        _render_source_access(source, source_index)

        if st.button(
            "Open document page",
            key=f"library_document_{source['source_id']}",
            use_container_width=True,
        ):
            navigate(
                AtlasPage.DOCUMENT,
                course_id=source.get("course_id"),
                source_id=source["source_id"],
            )

        st.divider()
        st.markdown("#### Manage source")
        action_columns = st.columns(2)
        with action_columns[0]:
            if source["can_reprocess"]:
                if st.button(
                    "Reprocess source", key=f"reprocess_{source['source_id']}"
                ):
                    try:
                        with st.spinner("Atlas is rebuilding this source…"):
                            result = reprocess_library_source(
                                source["source_id"], product_context=product_context
                            )
                        st.success(
                            f"Reprocessed {result['knowledge_object_count']} knowledge units."
                        )
                    except Exception as error:
                        st.error(f"Atlas could not reprocess this source: {error}")
            else:
                st.caption(
                    "Reprocessing is unavailable because the original file cannot be found."
                )
        with action_columns[1]:
            if source["can_remove"]:
                confirmation_text = st.text_input(
                    "Type REMOVE to confirm",
                    key=f"confirm_remove_{source['source_id']}",
                )
                if st.button(
                    "Remove source",
                    disabled=confirmation_text.strip().upper() != "REMOVE",
                    key=f"remove_{source['source_id']}",
                ):
                    try:
                        result = remove_library_source(
                            source["source_id"], product_context=product_context
                        )
                        if result["cleanup_warning"]:
                            st.warning(result["cleanup_warning"])
                        else:
                            st.success(f"Removed “{result['display_name']}”.")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Atlas could not remove this source: {error}")
            else:
                st.caption("Repository sources are protected and cannot be removed.")


def render_library_page(product_context):
    render_hero(
        "Atlas Library",
        "Every registered source, in one place.",
        "Review source health, preserve access to originals, and use only the management actions each source allows.",
    )
    try:
        with st.spinner("Loading the Library…"):
            sources = list_library_sources()
    except Exception as error:
        st.error(f"Atlas could not load the Library: {error}", icon="⚠️")
        return
    if not sources:
        st.info("Atlas does not have any registered sources yet.", icon="ℹ️")
        if st.button("Add materials", type="primary"):
            navigate(AtlasPage.UPLOAD)
        return

    summary_columns = st.columns(4)
    summary_columns[0].metric("Sources", len(sources))
    summary_columns[1].metric(
        "Knowledge units", sum(source["knowledge_object_count"] for source in sources)
    )
    summary_columns[2].metric(
        "Structured records", sum(source["record_count"] for source in sources)
    )
    summary_columns[3].metric(
        "Embeddings", sum(source["embedding_count"] for source in sources)
    )
    st.header("Registered sources")
    for source_index, source in enumerate(sources):
        _render_library_source(source, source_index, product_context)
