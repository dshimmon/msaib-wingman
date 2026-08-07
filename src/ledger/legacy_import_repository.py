"""Compatibility facade for the historical `ledger.legacy_import_repository` module."""

from wingman.shared.compatibility import expose as _expose


_expose(__name__, "ledger.legacy_import_repository")
