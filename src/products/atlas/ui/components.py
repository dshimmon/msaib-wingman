"""Small accessible presentation components shared by Atlas pages."""

from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st


SOURCE_STATUS_LABELS = {
    "ready": ("Ready", "success", "✓"),
    "partially_indexed": ("Partially indexed", "warning", "!"),
    "needs_processing": ("Needs processing", "danger", "!"),
    "original_unavailable": ("Original unavailable", "danger", "!"),
}
SUMMARY_STATUS_LABELS = {
    "missing": ("Summary not created", "neutral", "○"),
    "pending": ("Summary pending", "warning", "…"),
    "ready": ("AI summary ready", "success", "✓"),
    "failed": ("Summary failed", "danger", "!"),
    "stale": ("Summary needs refresh", "warning", "!"),
}


def render_hero(eyebrow, title, description):
    st.markdown(
        "<section class='atlas-hero'>"
        f"<div class='atlas-eyebrow'>{escape(eyebrow)}</div>"
        f"<h1>{escape(title)}</h1>"
        f"<p>{escape(description)}</p>"
        "</section>",
        unsafe_allow_html=True,
    )


def render_status(value, *, summary=False):
    labels = SUMMARY_STATUS_LABELS if summary else SOURCE_STATUS_LABELS
    label, tone, symbol = labels.get(
        value, (str(value).replace("_", " ").title(), "neutral", "○")
    )
    st.markdown(
        f"<span class='atlas-status atlas-status--{tone}'>"
        f"<span aria-hidden='true'>{escape(symbol)}</span>{escape(label)}</span>",
        unsafe_allow_html=True,
    )


def format_uploaded_at(uploaded_at):
    if not uploaded_at:
        return None
    try:
        timestamp = datetime.fromisoformat(str(uploaded_at).replace("Z", "+00:00"))
        return timestamp.strftime("%B %d, %Y at %I:%M %p UTC")
    except ValueError:
        return str(uploaded_at)


def render_evidence(evidence, key_prefix):
    """Display friendly evidence with a source path preserved when available."""
    if not evidence:
        return
    with st.expander("Supporting sources"):
        for index, item in enumerate(evidence):
            metadata = item.get("source_metadata", {})
            source_id = metadata.get("id", item.get("source"))
            display_name = metadata.get("display_name", source_id or "Unknown source")
            st.markdown(f"#### {display_name}")
            st.write(f"Location: {item.get('location') or 'Unknown location'}")
            details = [
                metadata.get("file_type", "").upper() or None,
                metadata.get("course_id"),
                metadata.get("program"),
                metadata.get("academic_year"),
            ]
            details = [detail for detail in details if detail]
            if details:
                st.caption(" • ".join(details))
            st.write(item.get("text", ""))
            source_url = metadata.get("source_url")
            original_path = metadata.get("original_path")
            if source_url:
                st.link_button("Open original source", source_url)
            elif original_path:
                source_path = Path(original_path)
                if source_path.exists() and source_path.is_file():
                    try:
                        st.download_button(
                            "Download original source",
                            data=source_path.read_bytes(),
                            file_name=metadata.get("file_name") or source_path.name,
                            mime=metadata.get("mime_type", "application/octet-stream"),
                            key=f"{key_prefix}_{source_id}_{index}",
                        )
                    except OSError:
                        st.caption("Original source file is unavailable.")
                else:
                    st.caption("Original source file is unavailable.")
            if index < len(evidence) - 1:
                st.divider()


def render_dependency_unavailable(message):
    st.warning(message, icon="⚠️")
    st.caption(
        "Library, uploads, Chat, Briefings, and Prompt Optimizer remain available."
    )


def consume_flash():
    message = st.session_state.pop("atlas_flash_message", None)
    tone = st.session_state.pop("atlas_flash_tone", "success")
    if message:
        getattr(st, tone, st.info)(message)


def set_flash(message, tone="success"):
    st.session_state.atlas_flash_message = message
    st.session_state.atlas_flash_tone = tone
