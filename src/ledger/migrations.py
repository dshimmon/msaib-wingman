"""Compatibility facade for the historical `ledger.migrations` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "ledger.migrations")
