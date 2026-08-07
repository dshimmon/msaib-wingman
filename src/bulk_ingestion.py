"""Compatibility facade for the historical `bulk_ingestion` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "bulk_ingestion")
