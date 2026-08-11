"""Thin Streamlit composition for the Atlas website."""

import streamlit as st

from products.atlas.product_config import create_atlas_context
from products.atlas.ui.flight_cards import load_flight_cards_gateway
from products.atlas.ui.navigation import AtlasPage, parse_query_state
from products.atlas.ui.shell import render_sidebar
from products.atlas.ui.styles import apply_atlas_styles


def run():
    product_context = create_atlas_context()
    product = product_context.product
    st.set_page_config(
        page_title=product.page_title,
        page_icon=product.page_icon,
        layout="wide",
        initial_sidebar_state="auto",
    )
    apply_atlas_styles()

    state = parse_query_state(dict(st.query_params))
    gateway = load_flight_cards_gateway()
    render_sidebar(product, state, gateway)
    if state.notice:
        st.info(state.notice, icon="ℹ️")

    if state.page is AtlasPage.COCKPIT:
        from products.atlas.ui.pages.cockpit import render_cockpit_page

        render_cockpit_page(gateway)
    elif state.page is AtlasPage.COURSE:
        from products.atlas.ui.pages.course import render_course_page

        render_course_page(gateway, state.course_id)
    elif state.page is AtlasPage.DOCUMENT:
        from products.atlas.ui.pages.document import render_document_page

        render_document_page(gateway, state.source_id, product_context)
    elif state.page is AtlasPage.CHAT:
        from products.atlas.ui.pages.chat import render_chat_page

        render_chat_page(product_context, state.course_id)
    elif state.page is AtlasPage.BRIEFING:
        from products.atlas.ui.pages.briefing import render_briefing_page

        render_briefing_page(product_context, state.course_id)
    elif state.page is AtlasPage.LIBRARY:
        from products.atlas.ui.pages.library import render_library_page

        render_library_page(product_context)
    elif state.page is AtlasPage.UPLOAD:
        from products.atlas.ui.pages.upload import render_upload_page

        render_upload_page(product_context)
    elif state.page is AtlasPage.PROMPT_OPTIMIZER:
        from products.atlas.ui.pages.prompt_optimizer import (
            render_prompt_optimizer_page,
        )

        render_prompt_optimizer_page()
    elif state.page is AtlasPage.PRACTICE_TEST:
        from products.atlas.ui.pages.practice_test import render_practice_test_page

        render_practice_test_page(state.course_id)
