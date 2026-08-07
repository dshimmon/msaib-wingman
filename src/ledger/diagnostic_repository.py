"""Compatibility facade for the historical `ledger.diagnostic_repository` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "ledger.diagnostic_repository")
