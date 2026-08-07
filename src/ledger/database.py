"""Compatibility facade for the historical `ledger.database` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "ledger.database")
