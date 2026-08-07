# Tests source-registry persistence and evidence enrichment.

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import wingman.shared.source_registry as source_registry


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
        self.database_path = (
            Path(self.temporary_directory.name)
            / "ledger"
            / "test.sqlite3"
        )
        self.environment_patch = patch.dict(
            os.environ,
            {
                "WINGMAN_LEDGER_PATH": str(
                    self.database_path
                )
            },
        )
        self.environment_patch.start()
        self.addCleanup(self.environment_patch.stop)

    def write_registry(self, registry):
        self.registry_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.registry_path.write_text(
            json.dumps(registry),
            encoding="utf-8",
        )

    def database_rows(self, statement, parameters=()):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            return connection.execute(
                statement,
                parameters,
            ).fetchall()
        finally:
            connection.close()

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

    def test_save_writes_valid_registry_to_ledger(self):
        registry = {
            "source-one": {
                "display_name": "Source One",
            }
        }

        source_registry.save_source_registry(registry)

        self.assertEqual(
            source_registry.load_source_registry(),
            registry,
        )
        self.assertFalse(self.registry_path.exists())

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
                    "course_id": "AI-101",
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
        self.assertEqual(metadata["course_id"], "AI-101")

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

    def test_import_preserves_ids_metadata_and_creates_versions(self):
        self.write_registry(
            {
                "repository-id": {
                    "display_name": "Repository",
                    "domain": "Academics",
                    "future_field": {"kept": True},
                },
                "upload-id": {
                    "source_kind": "uploaded",
                    "display_name": "Upload",
                    "content_hash": "abc",
                    "uploaded_at": "2026-01-02T03:04:05+00:00",
                },
            }
        )

        loaded = source_registry.load_source_registry()

        self.assertEqual(set(loaded), {"repository-id", "upload-id"})
        self.assertEqual(
            loaded["repository-id"]["future_field"],
            {"kept": True},
        )
        rows = self.database_rows(
            """
            SELECT source_id, version_number, content_hash, change_type
            FROM source_versions
            ORDER BY source_id
            """
        )
        self.assertEqual(
            [
                (
                    row["source_id"],
                    row["version_number"],
                    row["content_hash"],
                    row["change_type"],
                )
                for row in rows
            ],
            [
                ("repository-id", 1, None, "registered"),
                ("upload-id", 1, "abc", "uploaded"),
            ],
        )

    def test_import_is_idempotent_and_marker_survives_removal(self):
        self.write_registry(
            {"source-one": {"display_name": "Original"}}
        )
        source_registry.load_source_registry()
        self.write_registry(
            {"stale": {"display_name": "Stale"}}
        )
        source_registry.save_source_registry({})

        self.assertEqual(source_registry.load_source_registry(), {})
        self.assertEqual(
            len(
                self.database_rows(
                    "SELECT * FROM source_versions"
                )
            ),
            1,
        )
        marker = self.database_rows(
            "SELECT status FROM legacy_imports"
        )
        self.assertEqual(marker[0]["status"], "completed")

    def test_existing_ledger_state_skips_stale_seed(self):
        source_registry.register_source(
            "ledger-source",
            {"display_name": "Ledger"},
        )
        self.write_registry(
            {"stale-source": {"display_name": "Stale"}}
        )

        self.assertEqual(
            source_registry.load_source_registry(),
            {
                "ledger-source": {
                    "display_name": "Ledger"
                }
            },
        )

    def test_missing_seed_can_be_imported_later(self):
        self.assertEqual(source_registry.load_source_registry(), {})
        self.assertEqual(
            self.database_rows(
                "SELECT * FROM legacy_imports"
            ),
            [],
        )
        self.write_registry(
            {"later": {"display_name": "Later"}}
        )
        self.assertIn(
            "later",
            source_registry.load_source_registry(),
        )

    def test_malformed_or_invalid_seed_does_not_mark_import(self):
        self.registry_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.registry_path.write_text(
            '{"first": {"display_name": "First"}, '
            '"broken": NaN}',
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            source_registry.load_source_registry()
        self.assertEqual(
            self.database_rows(
                "SELECT * FROM sources"
            ),
            [],
        )
        self.assertEqual(
            self.database_rows(
                "SELECT * FROM legacy_imports"
            ),
            [],
        )

    def test_complete_snapshot_soft_removes_and_reactivates(self):
        original = {
            "source-one": {
                "display_name": "One",
                "content_hash": "hash",
            }
        }
        source_registry.save_source_registry(original)
        source_registry.save_source_registry({})

        self.assertEqual(
            source_registry.find_source_by_content_hash("hash"),
            (None, None),
        )
        self.assertEqual(
            self.database_rows(
                """
                SELECT status FROM entities
                WHERE entity_id = 'source-one'
                """
            )[0]["status"],
            "removed",
        )

        source_registry.save_source_registry(original)
        self.assertEqual(
            source_registry.load_source_registry(),
            original,
        )
        self.assertEqual(
            len(
                self.database_rows(
                    """
                    SELECT * FROM source_versions
                    WHERE source_id = 'source-one'
                    """
                )
            ),
            1,
        )

    def test_missing_hash_round_trips_absent_and_cannot_match(
        self,
    ):
        source_registry.register_source(
            "unhashed",
            {
                "display_name": "Unhashed",
                "future_field": "preserved",
            },
        )

        loaded = source_registry.load_source_registry()
        self.assertNotIn(
            "content_hash",
            loaded["unhashed"],
        )
        self.assertIsNone(
            self.database_rows(
                """
                SELECT content_hash FROM source_versions
                WHERE source_id = 'unhashed'
                """
            )[0]["content_hash"]
        )
        self.assertEqual(
            source_registry.find_source_by_content_hash(""),
            (None, None),
        )
        self.assertEqual(
            source_registry.find_source_by_content_hash(None),
            (None, None),
        )

        result = source_registry.register_source(
            "explicit-empty",
            {
                "display_name": "Explicit Empty",
                "content_hash": "",
            },
        )
        self.assertNotIn("content_hash", result)
        self.assertIsNone(
            self.database_rows(
                """
                SELECT content_hash FROM source_versions
                WHERE source_id = 'explicit-empty'
                """
            )[0]["content_hash"]
        )

        source_registry.save_source_registry({})
        source_registry.save_source_registry(loaded)
        self.assertEqual(
            source_registry.load_source_registry(),
            loaded,
        )

    def test_registering_removed_source_preserves_unknown_metadata(
        self,
    ):
        source_registry.register_source(
            "source-one",
            {
                "display_name": "Original",
                "future_field": {"preserved": True},
            },
        )
        source_registry.save_source_registry({})

        result = source_registry.register_source(
            "source-one",
            {"display_name": "Restored"},
        )

        self.assertEqual(
            result,
            {
                "display_name": "Restored",
                "future_field": {"preserved": True},
            },
        )
        self.assertEqual(
            source_registry.load_source_registry()[
                "source-one"
            ],
            result,
        )

    def test_import_failure_after_insert_rolls_back_everything(
        self,
    ):
        self.write_registry(
            {
                "first": {"display_name": "First"},
                "second": {"display_name": "Second"},
            }
        )
        original_sync = source_registry.sync_source
        call_count = 0

        def fail_second_sync(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("injected import failure")
            return original_sync(*args, **kwargs)

        with patch.object(
            source_registry,
            "sync_source",
            side_effect=fail_second_sync,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "injected import failure",
            ):
                source_registry.load_source_registry()

        self.assertEqual(
            self.database_rows("SELECT * FROM sources"),
            [],
        )
        self.assertEqual(
            self.database_rows("SELECT * FROM source_versions"),
            [],
        )
        self.assertEqual(
            self.database_rows("SELECT * FROM legacy_imports"),
            [],
        )

    def test_version_defining_changes_are_sequential_and_reused(self):
        first = {
            "display_name": "One",
            "content_hash": "first",
            "original_path": "/first",
        }
        second = {
            **first,
            "display_name": "Renamed",
        }
        source_registry.register_source("source-one", first)
        source_registry.register_source("source-one", second)
        source_registry.register_source(
            "source-one",
            {
                "content_hash": "second",
                "reprocessed_at": "2026-02-03T04:05:06+00:00",
            },
        )
        source_registry.register_source(
            "source-one",
            {
                "content_hash": "first",
                "original_path": "/first",
                "reprocessed_at": None,
            },
        )

        rows = self.database_rows(
            """
            SELECT version_number FROM source_versions
            WHERE source_id = 'source-one'
            ORDER BY version_number
            """
        )
        self.assertEqual(
            [row["version_number"] for row in rows],
            [1, 2],
        )


if __name__ == "__main__":
    unittest.main()
