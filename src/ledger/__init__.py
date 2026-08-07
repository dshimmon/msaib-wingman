"""Compatibility facade for the historical `ledger` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "ledger")
