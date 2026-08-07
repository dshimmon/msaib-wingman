"""Compatibility facade for the historical `document_ingestion` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "document_ingestion")
