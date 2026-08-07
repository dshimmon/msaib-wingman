"""Compatibility facade for the historical `main` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "main")
