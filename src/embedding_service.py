"""Compatibility facade for the historical `embedding_service` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "embedding_service")
