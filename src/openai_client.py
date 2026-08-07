"""Compatibility facade for the historical `openai_client` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "openai_client")
