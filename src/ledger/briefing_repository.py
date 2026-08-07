"""Compatibility facade for the historical `ledger.briefing_repository` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "ledger.briefing_repository")
