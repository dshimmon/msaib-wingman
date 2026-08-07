"""Compatibility facade for the historical `ledger.action_repository` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "ledger.action_repository")
