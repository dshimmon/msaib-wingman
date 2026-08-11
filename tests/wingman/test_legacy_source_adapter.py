"""Version-3 source storage compatibility at the private repository seam."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

from wingman.core.ledger.database import connect_database, transaction
from wingman.core.ledger.migrations import apply_migrations
from wingman.core.ledger.source_repository import (
    create_source,
    get_source,
    update_source,
)
import wingman.shared.source_registry as source_registry


class LegacySourceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = (
            Path(self.temporary_directory.name)
            / "ledger.sqlite3"
        )
        self.enterContext(
            patch.dict(
                os.environ,
                {
                    "WINGMAN_LEDGER_PATH": str(
                        self.database_path
                    )
                },
                clear=False,
            )
        )
        self.enterContext(
            patch.object(
                source_registry,
                "SOURCE_REGISTRY_PATH",
                Path(self.temporary_directory.name)
                / "missing-registry.json",
            )
        )
        initialization_connection = connect_database(
            self.database_path,
            lock_mode="exclusive",
        )
        self.assertEqual(
            apply_migrations(
                initialization_connection,
                target_version=3,
            ),
            {1, 2, 3},
        )
        initialization_connection.close()
        self.connection = connect_database(self.database_path)
        self.addCleanup(self.connection.close)

    def test_version_3_schema_is_unchanged(self):
        columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(sources)"
            )
        }
        self.assertEqual(
            columns,
            {
                "entity_id",
                "source_kind",
                "display_name",
                "file_name",
                "file_type",
                "mime_type",
                "program",
                "academic_year",
                "source_url",
                "original_path",
                "current_source_version_id",
            },
        )

    def test_read_uses_metadata_first_without_mutating_storage(self):
        with transaction(self.connection):
            create_source(
                self.connection,
                entity_id="source",
                source_kind="repository",
                display_name="Source",
                metadata={
                    "program": None,
                    "nested": {
                        "tracks": ["one", "two"],
                    },
                },
            )
            self.connection.execute(
                """
                UPDATE sources
                SET program = ?, academic_year = ?
                WHERE entity_id = ?
                """,
                (
                    "legacy conflict",
                    "legacy fallback",
                    "source",
                ),
            )

        before = tuple(
            self.connection.execute(
                """
                SELECT e.metadata_json, s.program, s.academic_year
                FROM entities AS e
                JOIN sources AS s USING (entity_id)
                WHERE e.entity_id = ?
                """,
                ("source",),
            ).fetchone()
        )

        source = get_source(self.connection, "source")

        after = tuple(
            self.connection.execute(
                """
                SELECT e.metadata_json, s.program, s.academic_year
                FROM entities AS e
                JOIN sources AS s USING (entity_id)
                WHERE e.entity_id = ?
                """,
                ("source",),
            ).fetchone()
        )
        self.assertEqual(
            source.metadata,
            {
                "program": None,
                "academic_year": "legacy fallback",
                "nested": {
                    "tracks": ["one", "two"],
                },
            },
        )
        self.assertEqual(before, after)

    def test_generic_writes_mirror_version_3_columns(self):
        metadata = {
            "program": "Program A",
            "academic_year": "Year 1",
            "custom_key": "custom value",
            "nested": {
                "levels": [1, {"enabled": True}],
            },
        }
        with transaction(self.connection):
            created = create_source(
                self.connection,
                entity_id="source",
                source_kind="upload",
                display_name="Source",
                metadata=metadata,
            )

        row = self.connection.execute(
            """
            SELECT e.metadata_json, s.program, s.academic_year
            FROM entities AS e
            JOIN sources AS s USING (entity_id)
            WHERE e.entity_id = ?
            """,
            ("source",),
        ).fetchone()
        self.assertEqual(
            json.loads(row["metadata_json"]),
            metadata,
        )
        self.assertEqual(row["program"], "Program A")
        self.assertEqual(row["academic_year"], "Year 1")
        self.assertFalse(hasattr(created, "program"))
        self.assertFalse(hasattr(created, "academic_year"))

        with transaction(self.connection):
            updated = update_source(
                self.connection,
                "source",
                source_kind="upload",
                display_name="Source",
                status="active",
                metadata={
                    "program": "Program B",
                    "custom_key": "updated",
                    "nested": {
                        "levels": [2, {"enabled": False}],
                    },
                },
            )

        row = self.connection.execute(
            """
            SELECT program, academic_year
            FROM sources
            WHERE entity_id = ?
            """,
            ("source",),
        ).fetchone()
        self.assertEqual(row["program"], "Program B")
        self.assertIsNone(row["academic_year"])
        self.assertEqual(
            updated.metadata,
            {
                "program": "Program B",
                "custom_key": "updated",
                "nested": {
                    "levels": [2, {"enabled": False}],
                },
            },
        )

    def test_metadata_only_values_survive_null_legacy_columns(self):
        metadata = {
            "program": "Metadata Program",
            "academic_year": "Metadata Year",
            "nested": {"policy": {"modes": ["a", "b"]}},
        }
        with transaction(self.connection):
            create_source(
                self.connection,
                entity_id="metadata-only",
                source_kind="repository",
                display_name="Metadata only",
                metadata=metadata,
            )
            self.connection.execute(
                """
                UPDATE sources
                SET program = NULL, academic_year = NULL
                WHERE entity_id = ?
                """,
                ("metadata-only",),
            )

        source = get_source(
            self.connection,
            "metadata-only",
        )
        self.assertEqual(source.metadata, metadata)

    def test_partial_registration_preserves_existing_metadata(self):
        initial = {
            "display_name": "Original",
            "source_kind": "repository",
            "program": "Program A",
            "academic_year": "Year 1",
            "nested": {
                "tracks": ["core", "elective"],
                "settings": {"visible": True},
            },
        }
        source_registry.register_source("registered", initial)

        merged = source_registry.register_source(
            "registered",
            {
                "display_name": "Renamed",
                "new_key": "new value",
            },
        )

        expected = {
            **initial,
            "display_name": "Renamed",
            "new_key": "new value",
        }
        self.assertEqual(merged, expected)
        self.assertEqual(
            source_registry.load_source_registry()[
                "registered"
            ],
            expected,
        )
        row = self.connection.execute(
            """
            SELECT program, academic_year
            FROM sources
            WHERE entity_id = ?
            """,
            ("registered",),
        ).fetchone()
        self.assertEqual(
            tuple(row),
            ("Program A", "Year 1"),
        )

    def test_complete_registry_save_replaces_snapshot(self):
        source_registry.register_source(
            "retained",
            {
                "display_name": "Old",
                "source_kind": "repository",
                "program": "Old Program",
                "academic_year": "Old Year",
                "obsolete": True,
            },
        )
        source_registry.register_source(
            "removed",
            {
                "display_name": "Removed",
                "source_kind": "repository",
            },
        )
        replacement = {
            "retained": {
                "display_name": "Replacement",
                "source_kind": "repository",
                "program": None,
                "nested": {
                    "rules": [
                        {"name": "preserve", "enabled": True}
                    ]
                },
            }
        }

        source_registry.save_source_registry(replacement)

        self.assertEqual(
            source_registry.load_source_registry(),
            replacement,
        )
        row = self.connection.execute(
            """
            SELECT program, academic_year
            FROM sources
            WHERE entity_id = ?
            """,
            ("retained",),
        ).fetchone()
        self.assertEqual(tuple(row), (None, None))
        removed_status = self.connection.execute(
            """
            SELECT status
            FROM entities
            WHERE entity_id = ?
            """,
            ("removed",),
        ).fetchone()["status"]
        self.assertEqual(removed_status, "removed")


if __name__ == "__main__":
    unittest.main()
