"""Compatibility facade for the historical `embedding_storage` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "embedding_storage")
