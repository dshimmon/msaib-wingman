"""Compatibility facade for the historical `ledger.source_repository` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "ledger.source_repository")
