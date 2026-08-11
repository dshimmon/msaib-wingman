"""Atlas batch upload, preview, progress, and retry page."""

import hashlib
from pathlib import Path

import streamlit as st

from products.atlas.batch_ingestion import (
    browser_file_input,
    create_batch_id,
    execute_batch,
    preview_batch,
    reset_assignment_confirmation_if_changed,
    resume_plan,
)
from products.atlas.intake_service import create_display_name
from products.atlas.ui.components import render_hero


SUPPORTED_UPLOAD_TYPES = [
    "pptx",
    "pdf",
    "docx",
    "xlsx",
    "csv",
    "txt",
    "md",
    "markdown",
]


def _selection_signature(uploaded_files):
    selected_bytes = [
        (uploaded_file.name, uploaded_file.getvalue())
        for uploaded_file in uploaded_files
    ]
    signature = tuple(
        sorted(
            (name, len(file_bytes), hashlib.sha256(file_bytes).hexdigest())
            for name, file_bytes in selected_bytes
        )
    )
    return selected_bytes, signature


def _render_batch_result(batch_result, batch_inputs, product_context):
    st.markdown("#### Import report")
    st.markdown(batch_result["report"])
    st.caption(
        "Open the Library to reprocess or remove each successful source individually."
    )
    can_retry = any(
        record.get("terminal_result") == "failed" and record.get("retryable")
        for record in batch_result["manifest"]["files"]
    )
    if can_retry and st.button("Retry failed files"):
        try:
            retry_plan = resume_plan(
                batch_result["manifest_path"],
                batch_inputs,
                product_context=product_context,
            )
            st.session_state.batch_result = execute_batch(
                retry_plan,
                product_context=product_context,
                manifest_path=batch_result["manifest_path"],
                report_path=batch_result["report_path"],
                retry_failed=True,
            )
            st.rerun()
        except Exception as error:
            st.error(f"Atlas could not retry the failed files: {error}")


def render_upload_page(product_context):
    product = product_context.product
    render_hero(
        "Add Materials",
        "Bring course documents into Atlas.",
        "Review names and course assignments before any file is processed. Atlas imports a confirmed batch sequentially and preserves retry evidence.",
    )
    uploaded_files = st.file_uploader(
        "Upload documents",
        type=SUPPORTED_UPLOAD_TYPES,
        accept_multiple_files=True,
    )
    if not uploaded_files:
        st.info(
            "Choose PDF, DOCX, XLSX, PPTX, CSV, TXT, MD, or MARKDOWN files to begin.",
            icon="ℹ️",
        )
        return

    domain = st.text_input("Domain", value=product.default_domain)
    default_course_id = st.text_input("Batch course ID", placeholder="Required")
    product_metadata = {
        field.key: st.text_input(field.label, placeholder=field.placeholder)
        for field in product.source_metadata_fields
        if field.key != "course_id"
    }
    display_name_overrides = {}
    course_overrides = {}
    st.subheader("Review every file")
    st.caption("Leave a course override blank to use the confirmed batch course ID.")
    for file_index, uploaded_file in enumerate(uploaded_files):
        with st.container(border=True):
            st.markdown(f"**{uploaded_file.name}**")
            entered_display_name = st.text_input(
                f"Display name — {uploaded_file.name}",
                value=create_display_name(uploaded_file.name),
                key=f"display_name_{file_index}_{uploaded_file.name}",
            )
            entered_course_override = st.text_input(
                f"Course override — {uploaded_file.name}",
                key=f"course_override_{file_index}_{uploaded_file.name}",
                placeholder="Uses batch course ID",
            )
            display_name_overrides.setdefault(uploaded_file.name, entered_display_name)
            course_overrides.setdefault(uploaded_file.name, entered_course_override)

    selected_bytes, selection_signature = _selection_signature(uploaded_files)
    selection_changed = (
        st.session_state.get("batch_selection_signature") != selection_signature
    )
    if selection_changed:
        st.session_state.batch_selection_signature = selection_signature
        st.session_state.batch_id = create_batch_id()
        st.session_state.batch_result = None
    assignment_signature = (
        selection_signature,
        default_course_id.strip(),
        tuple(
            sorted(
                (relative_path, value.strip())
                for relative_path, value in course_overrides.items()
            )
        ),
    )
    reset_assignment_confirmation_if_changed(
        st.session_state,
        assignment_signature,
        selection_changed=selection_changed,
    )
    assignments_confirmed = st.checkbox(
        "I confirm the course assignment shown for every ingestible file.",
        key="batch_assignments_confirmed",
    )
    batch_inputs = [
        browser_file_input(name, file_bytes) for name, file_bytes in selected_bytes
    ]
    try:
        batch_plan = preview_batch(
            batch_inputs,
            product_context=product_context,
            input_mode="browser",
            default_course_id=default_course_id,
            course_overrides=course_overrides,
            display_name_overrides=display_name_overrides,
            product_metadata=product_metadata,
            domain=domain,
            assignments_confirmed=assignments_confirmed,
            batch_id=st.session_state.batch_id,
        )
    except Exception as error:
        st.error(f"Atlas could not prepare the batch preview: {error}")
        batch_plan = None

    if batch_plan is not None:
        st.markdown("#### Batch preview")
        st.dataframe(
            [
                {
                    "File": record["relative_path"],
                    "Format": Path(record["visible_name"]).suffix.lower(),
                    "Size": record["file_size"],
                    "Course ID": record["course_id"] or "Required",
                    "Status": record["reason_code"] or "ready",
                }
                for record in batch_plan.manifest["files"]
            ],
            use_container_width=True,
            hide_index=True,
        )
        ready_to_start = assignments_confirmed and all(
            record["terminal_result"] == "skipped" or record["ready"]
            for record in batch_plan.manifest["files"]
        )
    else:
        ready_to_start = False

    existing_batch_result = st.session_state.get("batch_result")
    batch_already_started = bool(
        existing_batch_result
        and existing_batch_result["manifest"]["batch_id"] == st.session_state.batch_id
    )
    if st.button(
        "Start batch import",
        type="primary",
        disabled=not ready_to_start or batch_already_started,
    ):
        try:
            progress_rows = {
                record["relative_path"]: st.empty()
                for record in batch_plan.manifest["files"]
            }

            def show_batch_progress(batch_id, record):
                del batch_id
                state = record["terminal_result"] or record["progress_stage"]
                progress_rows[record["relative_path"]].info(
                    f"{record['relative_path']}: {state}"
                )

            st.session_state.batch_result = execute_batch(
                batch_plan,
                product_context=product_context,
                progress_callback=show_batch_progress,
            )
        except Exception as error:
            st.error(f"Atlas could not complete the batch import: {error}")

    batch_result = st.session_state.get("batch_result")
    if (
        batch_result
        and batch_result["manifest"]["batch_id"] == st.session_state.batch_id
    ):
        _render_batch_result(batch_result, batch_inputs, product_context)
