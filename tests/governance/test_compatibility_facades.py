"""Compatibility registry, module-alias, and historical-path coverage."""

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from wingman.shared.compatibility import (  # noqa: E402
    COMPATIBILITY_FACADES,
    FACADE_BY_HISTORICAL,
)


def facade_path(historical):
    if historical == "ledger":
        return SRC / "ledger" / "__init__.py"
    if historical.startswith("ledger."):
        return SRC.joinpath(*historical.split(".")).with_suffix(".py")
    return SRC / f"{historical}.py"


def canonical_path(canonical):
    parts = canonical.split(".")
    package_path = SRC.joinpath(*parts)
    init_path = package_path / "__init__.py"
    return init_path if init_path.is_file() else package_path.with_suffix(".py")


class CompatibilityFacadeTests(unittest.TestCase):
    def test_every_facade_is_registered_complete_and_physical(self):
        self.assertEqual(
            len(COMPATIBILITY_FACADES), len(FACADE_BY_HISTORICAL)
        )
        for facade in COMPATIBILITY_FACADES:
            with self.subTest(historical=facade.historical):
                self.assertTrue(facade.owner)
                self.assertTrue(facade.reason)
                self.assertTrue(facade.supported_callers)
                self.assertTrue(facade.removal_condition)
                historical_path = facade_path(facade.historical)
                self.assertTrue(historical_path.is_file(), historical_path)
                self.assertTrue(
                    canonical_path(facade.canonical).is_file(), facade.canonical
                )
                self.assertIn(
                    f'_expose(__name__, "{facade.historical}")',
                    historical_path.read_text(encoding="utf-8"),
                )

    def test_representative_imports_alias_the_canonical_module_object(self):
        pairs = (
            ("knowledge", "wingman.core.knowledge"),
            ("product_contract", "wingman.shared.product_contract"),
            ("product_config", "products.atlas.product_config"),
            ("ledger.database", "wingman.core.ledger.database"),
        )
        for historical, canonical in pairs:
            with self.subTest(historical=historical):
                self.assertIs(
                    importlib.import_module(historical),
                    importlib.import_module(canonical),
                )

    def test_legacy_monkeypatch_reaches_canonical_callers(self):
        historical = importlib.import_module("prompt_optimizer")
        canonical = importlib.import_module("wingman.core.prompt_optimizer")
        sentinel = object()
        with patch.object(historical, "client", sentinel):
            self.assertIs(canonical.client, sentinel)

    def test_radar_namespace_contains_no_production_module(self):
        radar_files = sorted(
            path.name for path in (SRC / "products" / "radar").glob("*.py")
        )
        self.assertEqual(radar_files, ["__init__.py"])


if __name__ == "__main__":
    unittest.main()
