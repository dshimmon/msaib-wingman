# Tests source-registry persistence and evidence enrichment.

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import source_registry


class SourceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )
        self.registry_path = (
            Path(self.temporary_directory.name)
            / "sources"
            / "source-registry.json"
        )
        self.registry_patch = patch.object(
            source_registry,
            "SOURCE_REGISTRY_PATH",
            self.registry_path,
        )
        self.registry_patch.start()
        self.addCleanup(self.registry_patch.stop)

    def write_registry(self, registry):
        self.registry_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.registry_path.write_text(
            json.dumps(registry),
            encoding="utf-8",
        )

    def test_missing_registry_returns_empty_dictionary(self):
        self.assertEqual(
            source_registry.load_source_registry(),
            {},
        )

    def test_non_object_registry_raises_value_error(self):
        self.write_registry(["not", "an", "object"])

        with self.assertRaisesRegex(
            ValueError,
            "must contain a JSON object",
        ):
            source_registry.load_source_registry()

    def test_save_writes_valid_json_atomically(self):
        registry = {
            "source-one": {
                "display_name": "Source One",
            }
        }

        source_registry.save_source_registry(registry)

        self.assertEqual(
            json.loads(
                self.registry_path.read_text(
                    encoding="utf-8",
                )
            ),
            registry,
        )
        self.assertFalse(
            Path(f"{self.registry_path}.tmp").exists()
        )

    def test_register_source_creates_entry(self):
        result = source_registry.register_source(
            "source-one",
            {"display_name": "Source One"},
        )

        self.assertEqual(
            result,
            {"display_name": "Source One"},
        )
        self.assertEqual(
            source_registry.load_source_registry(),
            {"source-one": result},
        )

    def test_register_source_updates_without_losing_fields(self):
        self.write_registry(
            {
                "source-one": {
                    "display_name": "Old Name",
                    "file_type": "pdf",
                }
            }
        )

        result = source_registry.register_source(
            "source-one",
            {"display_name": "New Name"},
        )

        self.assertEqual(
            result,
            {
                "display_name": "New Name",
                "file_type": "pdf",
            },
        )

    def test_find_source_by_content_hash(self):
        self.write_registry(
            {
                "source-one": {
                    "content_hash": "first",
                },
                "source-two": {
                    "content_hash": "target",
                },
            }
        )

        self.assertEqual(
            source_registry.find_source_by_content_hash(
                "target"
            ),
            (
                "source-two",
                {"content_hash": "target"},
            ),
        )

    def test_enrich_evidence_attaches_friendly_metadata(self):
        self.write_registry(
            {
                "source-one": {
                    "display_name": "Friendly Source",
                    "file_name": "source.pdf",
                    "mime_type": "application/pdf",
                    "domain": "Academics",
                }
            }
        )

        enriched = source_registry.enrich_evidence_sources(
            [
                {
                    "source": "source-one",
                    "domain": "Original",
                    "text": "Evidence",
                }
            ]
        )

        metadata = enriched[0]["source_metadata"]
        self.assertEqual(
            metadata["display_name"],
            "Friendly Source",
        )
        self.assertEqual(
            metadata["file_name"],
            "source.pdf",
        )
        self.assertEqual(
            metadata["mime_type"],
            "application/pdf",
        )
        self.assertEqual(
            metadata["domain"],
            "Academics",
        )

    def test_unregistered_evidence_uses_fallbacks(self):
        enriched = source_registry.enrich_evidence_sources(
            [
                {
                    "source": "unregistered",
                    "domain": "Fallback Domain",
                }
            ]
        )

        metadata = enriched[0]["source_metadata"]
        self.assertEqual(metadata["id"], "unregistered")
        self.assertEqual(
            metadata["display_name"],
            "unregistered",
        )
        self.assertEqual(
            metadata["mime_type"],
            "application/octet-stream",
        )
        self.assertEqual(
            metadata["domain"],
            "Fallback Domain",
        )


if __name__ == "__main__":
    unittest.main()
