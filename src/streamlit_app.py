"""Compatibility facade for the historical `streamlit_app` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "streamlit_app")
