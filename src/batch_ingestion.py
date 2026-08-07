"""Compatibility facade for the historical `batch_ingestion` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "batch_ingestion")
