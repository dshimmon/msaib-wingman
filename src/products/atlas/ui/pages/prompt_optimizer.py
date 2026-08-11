"""Product-neutral Prompt Optimizer presentation."""

import streamlit as st

from products.atlas.ui.components import render_hero
from wingman.core import prompt_optimizer


PROMPT_OPTIMIZER_LABEL = "Prompt Optimizer"


def clear_prompt_optimizer_result():
    st.session_state.optimized_prompt = None


def edit_optimized_prompt():
    optimized_prompt = st.session_state.get("optimized_prompt")
    if optimized_prompt:
        st.session_state.prompt_optimizer_input = optimized_prompt
    st.session_state.optimized_prompt = None


def render_prompt_optimizer_page():
    render_hero(
        "Global tool",
        PROMPT_OPTIMIZER_LABEL,
        "Turn a rough prompt into a clearer, more specific prompt without changing its intent.",
    )
    prompt = st.text_area(
        "Prompt to optimize",
        key="prompt_optimizer_input",
        height=240,
        placeholder="Example: Help me make a launch plan for my new product.",
        on_change=clear_prompt_optimizer_result,
    )
    if st.button("Optimize Prompt", type="primary", disabled=not prompt.strip()):
        st.session_state.optimized_prompt = None
        try:
            with st.spinner("Improving your prompt…"):
                st.session_state.optimized_prompt = prompt_optimizer.optimize_prompt(
                    prompt
                )
        except Exception as error:
            st.error(f"The prompt could not be optimized: {error}")
    optimized_prompt = st.session_state.get("optimized_prompt")
    if not optimized_prompt:
        return
    st.divider()
    st.subheader("Optimized Prompt")
    st.caption("Use the copy button to copy this prompt.")
    st.code(optimized_prompt, language=None, wrap_lines=True)
    st.button("Edit Optimized Prompt", on_click=edit_optimized_prompt)
