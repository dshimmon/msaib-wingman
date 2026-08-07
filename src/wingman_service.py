"""Compatibility facade for the historical `wingman_service` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "wingman_service")
