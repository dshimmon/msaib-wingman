# Tests the product-neutral Wingman Ledger foundation.

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import ledger.migrations
from ledger.action_repository import (
    create_action,
    get_action,
    update_action_status,
)
from ledger.briefing_repository import (
    create_briefing,
    create_briefing_version,
    get_briefing,
    set_current_briefing_version,
)
from ledger.database import (
    connect_database,
    get_database_path,
    transaction,
)
from ledger.diagnostic_repository import (
    create_diagnostic_event,
    get_diagnostic_event,
)
from ledger.migrations import (
    MIGRATIONS,
    Migration,
    apply_migrations,
)
from ledger.models import (
    ActionRecord,
    BriefingRecord,
    BriefingVersionRecord,
    DiagnosticEventRecord,
    SourceRecord,
    SourceVersionRecord,
)
from ledger.source_repository import (
    create_source,
    create_source_version,
    get_source,
    set_current_source_version,
)


TEST_TIMESTAMP = "2026-07-29T12:00:00+00:00"


class LedgerCoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )
        self.database_path = (
            Path(self.temporary_directory.name)
            / "ledger"
            / "test-ledger.sqlite3"
        )
        self.connection = connect_database(
            self.database_path
        )
        self.addCleanup(self.connection.close)

    def migrate(self):
        return apply_migrations(self.connection)

    def create_test_source(self):
        with transaction(self.connection):
            return create_source(
                self.connection,
                entity_id="source-one",
                source_kind="repository",
                display_name="Source One",
                product_key="product-one",
                domain="Academics",
                file_name="source.pdf",
                file_type="pdf",
                metadata={"owner": "Wingman"},
                created_at=TEST_TIMESTAMP,
            )

    def test_empty_database_migration_creates_schema(self):
        versions = self.migrate()
        table_names = {
            row["name"]
            for row in self.connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

        self.assertEqual(
            versions,
            {migration.version for migration in MIGRATIONS},
        )
        self.assertTrue(
            {
                "schema_migrations",
                "entities",
                "sources",
                "source_versions",
                "briefings",
                "briefing_versions",
                "actions",
                "diagnostic_events",
            }.issubset(table_names)
        )

    def test_migrations_are_idempotent_and_recorded(self):
        first_versions = self.migrate()
        second_versions = self.migrate()
        rows = self.connection.execute(
            """
            SELECT version, name
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()

        self.assertEqual(first_versions, second_versions)
        self.assertEqual(len(rows), len(MIGRATIONS))
        self.assertEqual(
            [
                (row["version"], row["name"])
                for row in rows
            ],
            [
                (migration.version, migration.name)
                for migration in MIGRATIONS
            ],
        )

    def test_fresh_schema_has_nullable_source_version_hash(
        self,
    ):
        self.migrate()

        columns = self.connection.execute(
            "PRAGMA table_info(source_versions)"
        ).fetchall()
        content_hash = next(
            column
            for column in columns
            if column["name"] == "content_hash"
        )

        self.assertEqual(content_hash["notnull"], 0)

    def test_nullable_hash_migration_preserves_versions_and_pointer(
        self,
    ):
        with patch.object(
            ledger.migrations,
            "MIGRATIONS",
            MIGRATIONS[:2],
        ):
            apply_migrations(self.connection)

        with transaction(self.connection):
            create_source(
                self.connection,
                entity_id="source-one",
                source_kind="repository",
                display_name="Source One",
                created_at=TEST_TIMESTAMP,
            )
            create_source_version(
                self.connection,
                entity_id="version-without-hash",
                source_id="source-one",
                version_number=1,
                content_hash="",
                change_type="registered",
                captured_at=TEST_TIMESTAMP,
            )
            create_source_version(
                self.connection,
                entity_id="version-with-hash",
                source_id="source-one",
                version_number=2,
                content_hash="real-hash",
                change_type="updated",
                captured_at=TEST_TIMESTAMP,
            )

        apply_migrations(self.connection)

        versions = self.connection.execute(
            """
            SELECT entity_id, source_id, version_number, content_hash,
                   original_path, captured_at, change_type, metadata_json
            FROM source_versions
            ORDER BY version_number
            """
        ).fetchall()
        source = get_source(self.connection, "source-one")

        self.assertEqual(
            versions[0]["entity_id"],
            "version-without-hash",
        )
        self.assertIsNone(versions[0]["content_hash"])
        self.assertEqual(
            versions[1]["content_hash"],
            "real-hash",
        )
        self.assertEqual(
            source.current_source_version_id,
            "version-with-hash",
        )
        self.assertEqual(
            self.connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall(),
            [],
        )

        with transaction(self.connection):
            create_source(
                self.connection,
                entity_id="source-two",
                source_kind="repository",
                display_name="Source Two",
                created_at=TEST_TIMESTAMP,
            )

        with self.assertRaises(sqlite3.IntegrityError):
            with transaction(self.connection):
                self.connection.execute(
                    """
                    UPDATE sources
                    SET current_source_version_id =
                        'version-with-hash'
                    WHERE entity_id = 'source-two'
                    """
                )

    def test_failed_rebuild_rolls_back_and_is_not_recorded(
        self,
    ):
        with patch.object(
            ledger.migrations,
            "MIGRATIONS",
            MIGRATIONS[:2],
        ):
            apply_migrations(self.connection)

        failing_migration = Migration(
            version=3,
            name="failing_table_rebuild",
            rebuilds_foreign_keys=True,
            statements=(
                """
                ALTER TABLE source_versions
                RENAME TO source_versions_old
                """,
                "THIS IS NOT VALID SQL",
            ),
        )

        with patch.object(
            ledger.migrations,
            "MIGRATIONS",
            (failing_migration,),
        ):
            with self.assertRaises(sqlite3.OperationalError):
                apply_migrations(self.connection)

        self.assertIsNotNone(
            self.connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'source_versions'
                """
            ).fetchone()
        )
        self.assertIsNone(
            self.connection.execute(
                """
                SELECT version FROM schema_migrations
                WHERE version = 3
                """
            ).fetchone()
        )
        self.assertEqual(
            self.connection.execute(
                "PRAGMA foreign_keys"
            ).fetchone()[0],
            1,
        )

    def test_failed_migration_rolls_back_and_is_not_recorded(
        self,
    ):
        failing_migration = Migration(
            version=1,
            name="failing_migration",
            statements=(
                """
                CREATE TABLE migration_probe (
                    probe_id TEXT PRIMARY KEY
                )
                """,
                "THIS IS NOT VALID SQL",
            ),
        )

        with patch.object(
            ledger.migrations,
            "MIGRATIONS",
            (failing_migration,),
        ):
            with self.assertRaises(
                sqlite3.OperationalError
            ):
                apply_migrations(self.connection)

        migration_row = self.connection.execute(
            """
            SELECT version
            FROM schema_migrations
            WHERE version = 1
            """
        ).fetchone()
        probe_table = self.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'migration_probe'
            """
        ).fetchone()

        self.assertIsNone(migration_row)
        self.assertIsNone(probe_table)

    def test_connection_configuration(self):
        self.assertIs(
            self.connection.row_factory,
            sqlite3.Row,
        )
        self.assertEqual(
            self.connection.execute(
                "PRAGMA foreign_keys"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(
            self.connection.execute(
                "PRAGMA journal_mode"
            ).fetchone()[0].lower(),
            "wal",
        )
        self.assertEqual(
            self.connection.execute(
                "PRAGMA busy_timeout"
            ).fetchone()[0],
            5000,
        )

    def test_foreign_keys_are_enforced(self):
        self.migrate()

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            with transaction(self.connection):
                self.connection.execute(
                    """
                    INSERT INTO sources (
                        entity_id,
                        source_kind,
                        display_name
                    )
                    VALUES ('missing', 'repository', 'Missing')
                    """
                )

    def test_transaction_commits_on_success(self):
        self.migrate()

        with transaction(self.connection):
            self.connection.execute(
                """
                INSERT INTO entities (
                    entity_id,
                    entity_type,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "committed",
                    "test",
                    "active",
                    TEST_TIMESTAMP,
                    TEST_TIMESTAMP,
                ),
            )

        self.assertIsNotNone(
            self.connection.execute(
                """
                SELECT entity_id
                FROM entities
                WHERE entity_id = 'committed'
                """
            ).fetchone()
        )

    def test_transaction_rolls_back_repository_writes(self):
        self.migrate()

        with self.assertRaisesRegex(
            RuntimeError,
            "force rollback",
        ):
            with transaction(self.connection):
                create_source(
                    self.connection,
                    entity_id="rolled-back-source",
                    source_kind="upload",
                    display_name="Rolled Back",
                    created_at=TEST_TIMESTAMP,
                )
                create_action(
                    self.connection,
                    entity_id="rolled-back-action",
                    title="Rolled Back Action",
                    status="planned",
                    created_at=TEST_TIMESTAMP,
                )
                raise RuntimeError("force rollback")

        count = self.connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM entities
            WHERE entity_id LIKE 'rolled-back-%'
            """
        ).fetchone()["count"]
        self.assertEqual(count, 0)

    def test_repository_writes_require_a_transaction(self):
        self.migrate()

        with self.assertRaisesRegex(
            RuntimeError,
            "require an active transaction",
        ):
            create_source(
                self.connection,
                entity_id="uncommitted-source",
                source_kind="upload",
                display_name="Uncommitted",
                created_at=TEST_TIMESTAMP,
            )

        self.assertIsNone(
            self.connection.execute(
                """
                SELECT entity_id
                FROM entities
                WHERE entity_id = 'uncommitted-source'
                """
            ).fetchone()
        )

    def test_environment_path_override(self):
        override_path = (
            Path(self.temporary_directory.name)
            / "override"
            / "ledger.sqlite3"
        )

        with patch.dict(
            os.environ,
            {
                "WINGMAN_LEDGER_PATH": str(
                    override_path
                )
            },
        ):
            self.assertEqual(
                get_database_path(),
                override_path,
            )
            connection = connect_database()
            connection.close()

        self.assertTrue(override_path.exists())

    def test_source_and_source_version_round_trip(self):
        self.migrate()
        source = self.create_test_source()

        with transaction(self.connection):
            source_version = create_source_version(
                self.connection,
                entity_id="source-one-version-1",
                source_id=source.entity_id,
                version_number=1,
                content_hash="abc123",
                change_type="created",
                original_path="/documents/source.pdf",
                metadata={"capture": "metadata"},
                version_metadata={
                    "checksum_algorithm": "sha256"
                },
                captured_at=TEST_TIMESTAMP,
            )

        refreshed_source = get_source(
            self.connection,
            source.entity_id,
        )

        self.assertIsInstance(source, SourceRecord)
        self.assertIsInstance(
            source_version,
            SourceVersionRecord,
        )
        self.assertEqual(
            source.metadata,
            {"owner": "Wingman"},
        )
        self.assertEqual(
            source_version.version_metadata,
            {"checksum_algorithm": "sha256"},
        )
        self.assertEqual(
            refreshed_source.current_source_version_id,
            source_version.entity_id,
        )
        self.assertEqual(refreshed_source.version, 2)

        with transaction(self.connection):
            set_current_source_version(
                self.connection,
                source.entity_id,
                source_version.entity_id,
                updated_at=TEST_TIMESTAMP,
            )

        self.assertEqual(
            get_source(
                self.connection,
                source.entity_id,
            ).version,
            2,
        )

    def test_source_current_version_must_belong_to_source(
        self,
    ):
        self.migrate()

        with transaction(self.connection):
            create_source(
                self.connection,
                entity_id="source-a",
                source_kind="repository",
                display_name="Source A",
                created_at=TEST_TIMESTAMP,
            )
            create_source(
                self.connection,
                entity_id="source-b",
                source_kind="repository",
                display_name="Source B",
                created_at=TEST_TIMESTAMP,
            )
            create_source_version(
                self.connection,
                entity_id="source-b-version-1",
                source_id="source-b",
                version_number=1,
                content_hash="hash-b",
                change_type="created",
                captured_at=TEST_TIMESTAMP,
                make_current=False,
            )

        with self.assertRaisesRegex(
            ValueError,
            "must belong",
        ):
            with transaction(self.connection):
                set_current_source_version(
                    self.connection,
                    "source-a",
                    "source-b-version-1",
                    updated_at=TEST_TIMESTAMP,
                )

        source = get_source(
            self.connection,
            "source-a",
        )
        self.assertIsNone(
            source.current_source_version_id
        )
        self.assertEqual(source.version, 1)

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            with transaction(self.connection):
                self.connection.execute(
                    """
                    UPDATE sources
                    SET current_source_version_id = ?
                    WHERE entity_id = ?
                    """,
                    (
                        "source-b-version-1",
                        "source-a",
                    ),
                )

    def test_duplicate_source_version_number_is_rejected(
        self,
    ):
        self.migrate()
        self.create_test_source()

        with transaction(self.connection):
            create_source_version(
                self.connection,
                entity_id="source-version-1",
                source_id="source-one",
                version_number=1,
                content_hash="first",
                change_type="created",
                captured_at=TEST_TIMESTAMP,
            )

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            with transaction(self.connection):
                create_source_version(
                    self.connection,
                    entity_id="source-version-duplicate",
                    source_id="source-one",
                    version_number=1,
                    content_hash="second",
                    change_type="updated",
                    captured_at=TEST_TIMESTAMP,
                )

        orphan = self.connection.execute(
            """
            SELECT entity_id
            FROM entities
            WHERE entity_id = 'source-version-duplicate'
            """
        ).fetchone()
        self.assertIsNone(orphan)

    def test_caught_repository_failure_rolls_back_savepoint(
        self,
    ):
        self.migrate()
        self.create_test_source()

        with transaction(self.connection):
            create_source_version(
                self.connection,
                entity_id="existing-version",
                source_id="source-one",
                version_number=1,
                content_hash="first",
                change_type="created",
                captured_at=TEST_TIMESTAMP,
            )

        with transaction(self.connection):
            with self.assertRaises(
                sqlite3.IntegrityError
            ):
                create_source_version(
                    self.connection,
                    entity_id="failed-version",
                    source_id="source-one",
                    version_number=1,
                    content_hash="duplicate",
                    change_type="updated",
                    captured_at=TEST_TIMESTAMP,
                )

            create_action(
                self.connection,
                entity_id="write-after-failure",
                title="Still valid",
                status="proposed",
                created_at=TEST_TIMESTAMP,
            )

        failed_entity = self.connection.execute(
            """
            SELECT entity_id
            FROM entities
            WHERE entity_id = 'failed-version'
            """
        ).fetchone()
        self.assertIsNone(failed_entity)
        self.assertIsNotNone(
            get_action(
                self.connection,
                "write-after-failure",
            )
        )

    def test_briefing_and_version_json_round_trip(self):
        self.migrate()

        with transaction(self.connection):
            briefing = create_briefing(
                self.connection,
                entity_id="briefing-one",
                topic="Prepare for a module",
                title="Module Briefing",
                product_key="product-one",
                metadata={"requested_by": "user-one"},
                created_at=TEST_TIMESTAMP,
            )
            briefing_version = create_briefing_version(
                self.connection,
                entity_id="briefing-one-version-1",
                briefing_id=briefing.entity_id,
                version_number=1,
                request_text="Prepare me",
                planner_type="deterministic",
                briefing={
                    "verified_facts": [
                        {"fact": "Fact one"}
                    ]
                },
                retrieval_results=[
                    {"category": "curriculum"}
                ],
                evidence_snapshot=[
                    {"source": "source-one"}
                ],
                source_fingerprint="fingerprint-one",
                metadata={"model": "test"},
                created_at=TEST_TIMESTAMP,
            )

        refreshed_briefing = get_briefing(
            self.connection,
            briefing.entity_id,
        )

        self.assertIsInstance(
            briefing,
            BriefingRecord,
        )
        self.assertIsInstance(
            briefing_version,
            BriefingVersionRecord,
        )
        self.assertEqual(
            briefing_version.briefing[
                "verified_facts"
            ][0]["fact"],
            "Fact one",
        )
        self.assertEqual(
            briefing_version.retrieval_results,
            [{"category": "curriculum"}],
        )
        self.assertEqual(
            briefing_version.evidence_snapshot,
            [{"source": "source-one"}],
        )
        self.assertEqual(
            refreshed_briefing.current_briefing_version_id,
            briefing_version.entity_id,
        )
        self.assertEqual(refreshed_briefing.version, 2)

        with transaction(self.connection):
            set_current_briefing_version(
                self.connection,
                briefing.entity_id,
                briefing_version.entity_id,
                updated_at=TEST_TIMESTAMP,
            )

        self.assertEqual(
            get_briefing(
                self.connection,
                briefing.entity_id,
            ).version,
            2,
        )

    def test_briefing_current_version_must_belong_to_briefing(
        self,
    ):
        self.migrate()

        with transaction(self.connection):
            create_briefing(
                self.connection,
                entity_id="briefing-a",
                topic="Topic A",
                title="Briefing A",
                created_at=TEST_TIMESTAMP,
            )
            create_briefing(
                self.connection,
                entity_id="briefing-b",
                topic="Topic B",
                title="Briefing B",
                created_at=TEST_TIMESTAMP,
            )
            create_briefing_version(
                self.connection,
                entity_id="briefing-b-version-1",
                briefing_id="briefing-b",
                version_number=1,
                request_text="Request B",
                planner_type="general",
                briefing={},
                retrieval_results=[],
                evidence_snapshot=[],
                created_at=TEST_TIMESTAMP,
                make_current=False,
            )

        with self.assertRaisesRegex(
            ValueError,
            "must belong",
        ):
            with transaction(self.connection):
                set_current_briefing_version(
                    self.connection,
                    "briefing-a",
                    "briefing-b-version-1",
                    updated_at=TEST_TIMESTAMP,
                )

        briefing = get_briefing(
            self.connection,
            "briefing-a",
        )
        self.assertIsNone(
            briefing.current_briefing_version_id
        )
        self.assertEqual(briefing.version, 1)

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            with transaction(self.connection):
                self.connection.execute(
                    """
                    UPDATE briefings
                    SET current_briefing_version_id = ?
                    WHERE entity_id = ?
                    """,
                    (
                        "briefing-b-version-1",
                        "briefing-a",
                    ),
                )

    def test_duplicate_briefing_version_is_rejected(self):
        self.migrate()

        with transaction(self.connection):
            create_briefing(
                self.connection,
                entity_id="briefing-one",
                topic="Topic",
                title="Title",
                created_at=TEST_TIMESTAMP,
            )
            create_briefing_version(
                self.connection,
                entity_id="briefing-version-1",
                briefing_id="briefing-one",
                version_number=1,
                request_text="Request",
                planner_type="general",
                briefing={},
                retrieval_results=[],
                evidence_snapshot=[],
                created_at=TEST_TIMESTAMP,
            )

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            with transaction(self.connection):
                create_briefing_version(
                    self.connection,
                    entity_id="briefing-version-duplicate",
                    briefing_id="briefing-one",
                    version_number=1,
                    request_text="Request",
                    planner_type="general",
                    briefing={},
                    retrieval_results=[],
                    evidence_snapshot=[],
                    created_at=TEST_TIMESTAMP,
                )

    def test_action_creation_and_status_update(self):
        self.migrate()

        with transaction(self.connection):
            origin = create_briefing(
                self.connection,
                entity_id="briefing-origin",
                topic="Topic",
                title="Title",
                created_at=TEST_TIMESTAMP,
            )
            action = create_action(
                self.connection,
                entity_id="action-one",
                origin_type="briefing",
                origin_entity_id=origin.entity_id,
                origin_item_key="recommended-action-1",
                title="Review materials",
                priority="High",
                status="proposed",
                notes="Initial note",
                metadata={"source": "generated"},
                created_at=TEST_TIMESTAMP,
            )

        with transaction(self.connection):
            updated_action = update_action_status(
                self.connection,
                action.entity_id,
                "completed",
                approved_at=TEST_TIMESTAMP,
                completed_at=TEST_TIMESTAMP,
                updated_at=TEST_TIMESTAMP,
            )

        self.assertIsInstance(action, ActionRecord)
        self.assertIsInstance(
            get_action(
                self.connection,
                action.entity_id,
            ),
            ActionRecord,
        )
        self.assertEqual(
            updated_action.status,
            "completed",
        )
        self.assertEqual(
            updated_action.action_status,
            "completed",
        )
        self.assertEqual(
            updated_action.completed_at,
            TEST_TIMESTAMP,
        )
        self.assertEqual(
            updated_action.metadata,
            {"source": "generated"},
        )
        self.assertEqual(updated_action.version, 2)

    def test_diagnostic_event_creation(self):
        self.migrate()

        with transaction(self.connection):
            related = create_action(
                self.connection,
                entity_id="related-action",
                title="Related",
                status="active",
                created_at=TEST_TIMESTAMP,
            )
            event = create_diagnostic_event(
                self.connection,
                entity_id="diagnostic-one",
                trace_id="trace-one",
                operation="test_operation",
                severity="warning",
                recoverable=True,
                related_entity_id=related.entity_id,
                message="Recoverable event",
                details={"attempt": 1},
                metadata={"component": "test"},
                occurred_at=TEST_TIMESTAMP,
            )

        self.assertIsInstance(
            event,
            DiagnosticEventRecord,
        )
        self.assertTrue(event.recoverable)
        self.assertEqual(event.details, {"attempt": 1})
        self.assertEqual(
            event.related_entity_id,
            related.entity_id,
        )

    def test_nullable_entity_links_are_cleared_on_delete(
        self,
    ):
        self.migrate()

        with transaction(self.connection):
            origin = create_briefing(
                self.connection,
                entity_id="deletable-origin",
                topic="Topic",
                title="Title",
                created_at=TEST_TIMESTAMP,
            )
            create_action(
                self.connection,
                entity_id="linked-action",
                origin_type="briefing",
                origin_entity_id=origin.entity_id,
                title="Linked action",
                status="proposed",
                created_at=TEST_TIMESTAMP,
            )
            create_diagnostic_event(
                self.connection,
                entity_id="linked-diagnostic",
                operation="linked_operation",
                severity="info",
                recoverable=True,
                related_entity_id=origin.entity_id,
                message="Linked event",
                occurred_at=TEST_TIMESTAMP,
            )

        with transaction(self.connection):
            self.connection.execute(
                """
                DELETE FROM entities
                WHERE entity_id = 'deletable-origin'
                """
            )

        self.assertIsNone(
            get_action(
                self.connection,
                "linked-action",
            ).origin_entity_id
        )
        self.assertIsNone(
            get_diagnostic_event(
                self.connection,
                "linked-diagnostic",
            ).related_entity_id
        )
        self.assertEqual(
            self.connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall(),
            [],
        )

    def test_parent_delete_is_restricted_while_versions_exist(
        self,
    ):
        self.migrate()
        self.create_test_source()

        with transaction(self.connection):
            create_source_version(
                self.connection,
                entity_id="protected-version",
                source_id="source-one",
                version_number=1,
                content_hash="hash",
                change_type="created",
                captured_at=TEST_TIMESTAMP,
            )

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            with transaction(self.connection):
                self.connection.execute(
                    """
                    DELETE FROM entities
                    WHERE entity_id = 'source-one'
                    """
                )

        self.assertIsNotNone(
            get_source(
                self.connection,
                "source-one",
            )
        )
        self.assertIsNotNone(
            self.connection.execute(
                """
                SELECT entity_id
                FROM source_versions
                WHERE entity_id = 'protected-version'
                """
            ).fetchone()
        )
        self.assertEqual(
            self.connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall(),
            [],
        )

    def test_deleting_current_version_clears_pointer(self):
        self.migrate()
        self.create_test_source()

        with transaction(self.connection):
            create_source_version(
                self.connection,
                entity_id="current-version",
                source_id="source-one",
                version_number=1,
                content_hash="hash",
                change_type="created",
                captured_at=TEST_TIMESTAMP,
            )

        with transaction(self.connection):
            self.connection.execute(
                """
                DELETE FROM entities
                WHERE entity_id = 'current-version'
                """
            )

        self.assertIsNone(
            get_source(
                self.connection,
                "source-one",
            ).current_source_version_id
        )
        self.assertEqual(
            self.connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall(),
            [],
        )

    def test_repository_rejects_invalid_json(self):
        self.migrate()

        with self.assertRaisesRegex(
            ValueError,
            "valid JSON",
        ):
            with transaction(self.connection):
                create_source(
                    self.connection,
                    entity_id="invalid-json-source",
                    source_kind="repository",
                    display_name="Invalid",
                    metadata={"invalid": object()},
                    created_at=TEST_TIMESTAMP,
                )

        self.assertIsNone(
            get_source(
                self.connection,
                "invalid-json-source",
            )
        )

        with self.assertRaisesRegex(
            ValueError,
            "must be a dict",
        ):
            with transaction(self.connection):
                create_source(
                    self.connection,
                    entity_id="invalid-container-source",
                    source_kind="repository",
                    display_name="Invalid Container",
                    metadata=[],
                    created_at=TEST_TIMESTAMP,
                )

        self.assertIsNone(
            get_source(
                self.connection,
                "invalid-container-source",
            )
        )

    def test_specialized_json_is_validated_before_writes(
        self,
    ):
        self.migrate()
        self.create_test_source()

        with transaction(self.connection):
            with self.assertRaisesRegex(
                ValueError,
                "version_metadata must be a dict",
            ):
                create_source_version(
                    self.connection,
                    entity_id="invalid-source-version-json",
                    source_id="source-one",
                    version_number=1,
                    content_hash="hash",
                    change_type="created",
                    version_metadata=[],
                    captured_at=TEST_TIMESTAMP,
                )

        with transaction(self.connection):
            create_briefing(
                self.connection,
                entity_id="json-briefing",
                topic="Topic",
                title="Title",
                created_at=TEST_TIMESTAMP,
            )
            with self.assertRaisesRegex(
                ValueError,
                "retrieval_results must be a list",
            ):
                create_briefing_version(
                    self.connection,
                    entity_id="invalid-briefing-version-json",
                    briefing_id="json-briefing",
                    version_number=1,
                    request_text="Request",
                    planner_type="general",
                    briefing={},
                    retrieval_results={},
                    evidence_snapshot=[],
                    created_at=TEST_TIMESTAMP,
                )

        partial_entity_count = self.connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM entities
            WHERE entity_id IN (
                'invalid-source-version-json',
                'invalid-briefing-version-json'
            )
            """
        ).fetchone()["count"]
        self.assertEqual(partial_entity_count, 0)


if __name__ == "__main__":
    unittest.main()
