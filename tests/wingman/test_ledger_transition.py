"""Synthetic safety and preservation tests for Ledger Transition."""

import json
import multiprocessing
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIRECTORY = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIRECTORY))

from wingman.core.ledger.authorization import (
    create_authorization_receipt,
    create_transition_manifest,
)
from wingman.core.ledger.backup import (
    create_immutable_backup,
    load_and_validate_backup,
)
from wingman.core.ledger.database import connect_database, transaction
from wingman.core.ledger.database import exclusive_connection
from wingman.core.ledger.dry_run import run_disposable_dry_run
from wingman.core.ledger.locking import (
    LedgerFileLock,
    LedgerPathError,
    LedgerLockTimeout,
    recovery_journal_path_for,
)
from wingman.core.ledger.migrations import (
    MIGRATIONS,
    Migration,
    apply_migrations,
    validate_migration_history,
)
from wingman.core.ledger.preservation import (
    capture_preservation_state,
    compare_migration_preservation,
)
from wingman.core.ledger.readiness import validate_readiness
from wingman.core.ledger.recovery import (
    recover_incomplete,
    restore_backup_locked,
)
from wingman.core.ledger.source_repository import (
    create_source,
    get_source,
    list_sources,
    update_source,
)
from wingman.core.ledger.transition import execute_authorized_transition


BASELINE = "b1910d0c69a52d73ddde93cb9722f12540c5d1e7"


def _hold_cooperative_connection(database_path, ready, release, *, writer):
    connection = connect_database(database_path)
    if writer:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "UPDATE schema_migrations SET applied_at = applied_at WHERE version = 1"
        )
    ready.put("ready")
    release.get(timeout=10)
    if writer:
        connection.rollback()
    connection.close()


def _attempt_maintenance_from_shared_connection(
    database_path,
    ready,
    start,
    result,
    release,
):
    connection = connect_database(database_path)
    ready.put("ready")
    start.get(timeout=10)
    try:
        apply_migrations(connection)
    except Exception as error:
        ledger_lock = connection._ledger_lock
        result.put(
            {
                "error": f"{type(error).__name__}:{error}",
                "mode": ledger_lock.mode,
                "descriptor_open": ledger_lock.descriptor is not None,
            }
        )
    else:
        result.put({"error": None})
    release.get(timeout=10)
    connection.close()


def _initialize_worker(database_path, results):
    try:
        import wingman.shared.source_registry as source_registry

        source_registry.SOURCE_REGISTRY_PATH = (
            Path(database_path).parent / "missing-source-registry.json"
        )
        os.environ["WINGMAN_LEDGER_PATH"] = database_path
        source_registry.load_source_registry()
        connection = connect_database(database_path)
        try:
            results.put(validate_readiness(connection)["schema_version"])
        finally:
            connection.close()
    except Exception as error:
        results.put(f"error:{type(error).__name__}:{error}")


def _hold_uncooperative_writer(database_path, ready, release):
    connection = sqlite3.connect(database_path, isolation_level=None)
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute(
        "UPDATE schema_migrations SET applied_at = applied_at || '' WHERE version = 1"
    )
    ready.put("ready")
    release.get(timeout=10)
    connection.rollback()
    connection.close()


def _open_connection_while_recovery_starts(database_path, ready, result):
    ready.put("waiting")
    try:
        connection = connect_database(database_path)
    except Exception as error:
        result.put(f"{type(error).__name__}:{error}")
    else:
        connection.close()
        result.put("opened")


def _terminate_restore_at_phase(
    database_path,
    backup_path,
    run_id,
    termination_phase,
):
    def terminate(observed):
        if observed == termination_phase:
            os._exit(91)

    with exclusive_connection(database_path) as connection:
        restore_backup_locked(
            connection,
            database_path,
            backup_path,
            run_id=run_id,
            phase_hook=terminate,
        )


def _terminate_transition_at_phase(
    manifest_path,
    receipt_path,
    termination_phase,
):
    def terminate(observed):
        if observed == termination_phase:
            os._exit(92)

    execute_authorized_transition(
        manifest_path,
        receipt_path,
        _phase_hook=terminate,
    )


class LedgerTransitionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.database_path = self.root / "ledger.sqlite3"

    def create_version_3(self):
        connection = connect_database(
            self.database_path,
            lock_mode="exclusive",
        )
        apply_migrations(connection, target_version=3)
        return connection

    def seed_semantic_matrix(self, connection):
        with transaction(connection):
            create_source(
                connection,
                entity_id="explicit-null",
                source_kind="repository",
                display_name="Explicit Null",
                metadata={"program": None, "nested": {"keep": [1, 2]}},
            )
            create_source(
                connection,
                entity_id="missing-fallback",
                source_kind="repository",
                display_name="Missing Fallback",
                metadata={"unrelated": True},
            )
            create_source(
                connection,
                entity_id="missing-null",
                source_kind="repository",
                display_name="Missing Null",
                metadata={"other": "value"},
            )
            create_source(
                connection,
                entity_id="raw-unchanged",
                source_kind="repository",
                display_name="Raw Unchanged",
                metadata={"z": 1, "a": 2},
            )
            connection.execute(
                """
                UPDATE sources SET program = ?, academic_year = ?
                WHERE entity_id = ?
                """,
                ("legacy-conflict", "Year 1", "explicit-null"),
            )
            connection.execute(
                """
                UPDATE sources SET program = ?, academic_year = ?
                WHERE entity_id = ?
                """,
                ("Program A", "Year 2", "missing-fallback"),
            )
            connection.execute(
                """
                UPDATE sources SET program = NULL, academic_year = NULL
                WHERE entity_id IN ('missing-null', 'raw-unchanged')
                """
            )
            connection.execute(
                """
                UPDATE entities SET metadata_json = ?
                WHERE entity_id = 'raw-unchanged'
                """,
                ('{ "z": 1, "a": 2 }',),
            )

    def authorization_paths(self, operation="migrate", backup=None):
        manifest_path = self.root / f"{operation}-manifest.json"
        receipt_path = self.root / f"{operation}-receipt.json"
        backup_path = backup or self.root / f"{operation}-backup.sqlite3"
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat()
        create_transition_manifest(
            self.database_path,
            backup_path,
            manifest_path,
            receipt_path,
            operation=operation,
            run_id=f"run-{operation}",
            expires_at=expires_at,
            reviewed_base=BASELINE,
            reviewed_head="HEAD",
        )
        create_authorization_receipt(
            manifest_path,
            receipt_path,
            authorization_text=f"Synthetic approval for {operation}",
        )
        return manifest_path, receipt_path, backup_path

    def test_fresh_database_initializes_to_version_4(self):
        connection = connect_database(
            self.database_path,
            lock_mode="exclusive",
        )
        try:
            self.assertEqual(apply_migrations(connection), {1, 2, 3, 4})
            self.assertEqual(
                validate_readiness(connection)["schema_version"],
                4,
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(sources)")
            }
            self.assertNotIn("program", columns)
            self.assertNotIn("academic_year", columns)
        finally:
            connection.close()

    def test_existing_version_3_never_auto_applies_migration_4(self):
        connection = self.create_version_3()
        try:
            self.assertEqual(apply_migrations(connection), {1, 2, 3})
            self.assertEqual(
                validate_readiness(connection)["schema_version"],
                3,
            )
        finally:
            connection.close()

    def test_migration_4_exact_fallback_and_preservation(self):
        connection = self.create_version_3()
        try:
            self.seed_semantic_matrix(connection)
            before = capture_preservation_state(connection)
            raw_before = connection.execute(
                """
                SELECT metadata_json FROM entities
                WHERE entity_id = 'raw-unchanged'
                """
            ).fetchone()[0]
            apply_migrations(
                connection,
                target_version=4,
                allow_existing_transition=True,
            )
            after = capture_preservation_state(connection)
            manifest = compare_migration_preservation(before, after)
            self.assertEqual(manifest["result"], "preserved")
            self.assertEqual(
                get_source(connection, "explicit-null").metadata,
                {
                    "program": None,
                    "academic_year": "Year 1",
                    "nested": {"keep": [1, 2]},
                },
            )
            self.assertEqual(
                get_source(connection, "missing-fallback").metadata,
                {
                    "program": "Program A",
                    "academic_year": "Year 2",
                    "unrelated": True,
                },
            )
            self.assertNotIn(
                "program",
                get_source(connection, "missing-null").metadata,
            )
            raw_after = connection.execute(
                """
                SELECT metadata_json FROM entities
                WHERE entity_id = 'raw-unchanged'
                """
            ).fetchone()[0]
            self.assertEqual(raw_before, raw_after)
        finally:
            connection.close()

    def test_version_4_repository_round_trip_uses_metadata_only(self):
        connection = connect_database(
            self.database_path,
            lock_mode="exclusive",
        )
        try:
            apply_migrations(connection)
            with transaction(connection):
                created = create_source(
                    connection,
                    entity_id="source",
                    source_kind="repository",
                    display_name="Source",
                    metadata={"product_field": {"nested": True}},
                )
            with transaction(connection):
                updated = update_source(
                    connection,
                    "source",
                    source_kind="repository",
                    display_name="Renamed",
                    status="active",
                    metadata={"product_field": None},
                )
            self.assertEqual(created.metadata, {"product_field": {"nested": True}})
            self.assertEqual(updated.metadata, {"product_field": None})
            self.assertEqual(len(list_sources(connection)), 1)
        finally:
            connection.close()

    def test_history_and_schema_drift_are_rejected(self):
        connection = self.create_version_3()
        try:
            connection.execute(
                "UPDATE schema_migrations SET name = 'wrong' WHERE version = 2"
            )
            with self.assertRaisesRegex(RuntimeError, "name mismatch"):
                validate_migration_history(connection)
            connection.execute(
                "UPDATE schema_migrations SET name = 'legacy_import_tracking' "
                "WHERE version = 2"
            )
            connection.execute("ALTER TABLE actions ADD COLUMN drift TEXT")
            with self.assertRaisesRegex(RuntimeError, "fingerprint"):
                validate_readiness(connection)
        finally:
            connection.close()

    def test_future_and_gap_history_are_rejected(self):
        connection = self.create_version_3()
        try:
            connection.execute("DELETE FROM schema_migrations WHERE version = 2")
            with self.assertRaisesRegex(RuntimeError, "gap"):
                validate_migration_history(connection)
            connection.execute(
                "INSERT INTO schema_migrations VALUES (5, 'future', 'now')"
            )
            with self.assertRaisesRegex(RuntimeError, "gap|future"):
                validate_migration_history(connection)
        finally:
            connection.close()

    def test_duplicate_and_unknown_future_history_are_rejected(self):
        connection = self.create_version_3()
        try:
            connection.executescript(
                """
                ALTER TABLE schema_migrations RENAME TO old_history;
                CREATE TABLE schema_migrations (
                    version INTEGER,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                );
                INSERT INTO schema_migrations SELECT * FROM old_history;
                INSERT INTO schema_migrations VALUES (
                    3, 'nullable_source_version_content_hash', 'duplicate'
                );
                DROP TABLE old_history;
                """
            )
            with self.assertRaisesRegex(RuntimeError, "duplicates"):
                validate_migration_history(connection)
        finally:
            connection.close()

        second = self.root / "future.sqlite3"
        connection = connect_database(second, lock_mode="exclusive")
        try:
            apply_migrations(connection)
            connection.execute(
                "INSERT INTO schema_migrations VALUES (5, 'future', 'now')"
            )
            with self.assertRaisesRegex(RuntimeError, "future"):
                validate_migration_history(connection)
        finally:
            connection.close()

    def test_invalid_metadata_and_abandoned_artifacts_are_rejected(self):
        connection = self.create_version_3()
        try:
            with transaction(connection):
                create_source(
                    connection,
                    entity_id="invalid",
                    source_kind="repository",
                    display_name="Invalid",
                    metadata={},
                )
                connection.execute(
                    "UPDATE entities SET metadata_json = '[]' WHERE entity_id = 'invalid'"
                )
            with self.assertRaisesRegex(RuntimeError, "must contain dict"):
                validate_readiness(connection)
            connection.execute(
                "UPDATE entities SET metadata_json = '{}' WHERE entity_id = 'invalid'"
            )
            connection.execute("CREATE TABLE sources_old (probe TEXT)")
            with self.assertRaisesRegex(RuntimeError, "abandoned"):
                validate_readiness(connection)
        finally:
            connection.close()

    def test_versioned_json_schemas_load_and_cli_rejects_arbitrary_args(self):
        schema_directory = (
            SRC_DIRECTORY / "wingman/core/ledger/schemas"
        )
        schemas = sorted(schema_directory.glob("*-v1.schema.json"))
        self.assertEqual(len(schemas), 5)
        for schema in schemas:
            with self.subTest(schema=schema.name):
                document = json.loads(schema.read_text(encoding="utf-8"))
                self.assertEqual(
                    document["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )

        from wingman.core.ledger.transition_cli import parser

        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                parser().parse_args(
                    [
                        "execute",
                        "--manifest", "manifest.json",
                        "--receipt", "receipt.json",
                        "--sql", "DROP TABLE sources",
                    ]
                )
            with self.assertRaises(SystemExit):
                parser().parse_args(
                    [
                        "execute",
                        "--manifest", "manifest.json",
                        "--receipt", "receipt.json",
                        "--migration", "4",
                    ]
                )

    def test_symlink_alias_and_active_recovery_are_rejected(self):
        connection = self.create_version_3()
        connection.close()
        alias = self.root / "ledger-alias.sqlite3"
        alias.symlink_to(self.database_path)
        with self.assertRaises(LedgerPathError):
            create_transition_manifest(
                alias,
                self.root / "backup.sqlite3",
                self.root / "manifest.json",
                self.root / "receipt.json",
                operation="migrate",
                run_id="alias",
                expires_at=(
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat(),
                reviewed_base=BASELINE,
                reviewed_head="HEAD",
            )
        recovery_journal_path_for(self.database_path).write_text(
            "{}",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(RuntimeError, "recovery is incomplete"):
            connect_database(self.database_path)

    def test_waiting_application_rechecks_recovery_after_lock_acquisition(self):
        connection = self.create_version_3()
        connection.close()
        context = multiprocessing.get_context("spawn")
        ready = context.Queue()
        result = context.Queue()
        with LedgerFileLock(self.database_path, "exclusive"):
            process = context.Process(
                target=_open_connection_while_recovery_starts,
                args=(str(self.database_path), ready, result),
            )
            process.start()
            self.assertEqual(ready.get(timeout=10), "waiting")
            recovery_journal_path_for(self.database_path).write_text(
                "{}",
                encoding="utf-8",
            )
        observed = result.get(timeout=10)
        process.join(timeout=10)
        self.assertEqual(process.exitcode, 0)
        self.assertIn("recovery is incomplete", observed)

    def test_immutable_backup_is_verified_non_overwriting_and_read_only(self):
        connection = self.create_version_3()
        self.seed_semantic_matrix(connection)
        connection.close()
        backup = self.root / "backup.sqlite3"
        manifest = create_immutable_backup(
            self.database_path,
            backup,
            run_id="backup-run",
        )
        self.assertEqual(load_and_validate_backup(backup), manifest)
        self.assertEqual(backup.stat().st_mode & 0o222, 0)
        with self.assertRaises(FileExistsError):
            create_immutable_backup(
                self.database_path,
                backup,
                run_id="second-run",
            )

    def test_corrupt_backup_is_rejected(self):
        connection = self.create_version_3()
        connection.close()
        backup = self.root / "backup.sqlite3"
        create_immutable_backup(
            self.database_path,
            backup,
            run_id="backup-run",
        )
        os.chmod(backup, 0o600)
        with backup.open("ab") as stream:
            stream.write(b"corruption")
        os.chmod(backup, 0o444)
        with self.assertRaisesRegex(RuntimeError, "byte count|checksum"):
            load_and_validate_backup(backup)

    def test_authorized_transition_is_single_use_and_preserves_behavior(self):
        connection = self.create_version_3()
        self.seed_semantic_matrix(connection)
        connection.close()
        protected = self.root / "non-ledger-evidence.bin"
        protected.write_bytes(b"preserve these exact bytes")
        manifest, receipt, backup = self.authorization_paths()
        result = execute_authorized_transition(
            manifest,
            receipt,
            non_ledger_paths=(protected,),
        )
        self.assertEqual(result["status"], "migrated")
        self.assertTrue(backup.exists())
        self.assertIn(
            str(protected),
            result["preservation"]["non_ledger_files"],
        )
        connection = connect_database(self.database_path)
        try:
            self.assertEqual(validate_readiness(connection)["schema_version"], 4)
        finally:
            connection.close()
        with self.assertRaisesRegex(RuntimeError, "already consumed"):
            execute_authorized_transition(manifest, receipt)

    def test_authorization_rejects_target_drift_before_consumption(self):
        connection = self.create_version_3()
        connection.close()
        manifest, receipt, _ = self.authorization_paths()
        raw = sqlite3.connect(self.database_path)
        raw.execute("UPDATE schema_migrations SET applied_at = 'changed' WHERE version = 3")
        raw.commit()
        raw.close()
        with self.assertRaisesRegex(RuntimeError, "identity changed|inventory changed"):
            execute_authorized_transition(manifest, receipt)
        consumed = list(self.root.glob("migrate-receipt.json.consumed-*"))
        self.assertEqual(consumed, [])

    def test_expired_manifest_and_tampered_receipt_fail_closed(self):
        connection = self.create_version_3()
        connection.close()
        with self.assertRaisesRegex(RuntimeError, "expired"):
            create_transition_manifest(
                self.database_path,
                self.root / "expired-backup.sqlite3",
                self.root / "expired-manifest.json",
                self.root / "expired-receipt.json",
                operation="migrate",
                run_id="expired",
                expires_at=(
                    datetime.now(timezone.utc) - timedelta(seconds=1)
                ).isoformat(),
                reviewed_base=BASELINE,
                reviewed_head="HEAD",
            )

        manifest, receipt, _ = self.authorization_paths()
        os.chmod(receipt, 0o600)
        document = json.loads(receipt.read_text(encoding="utf-8"))
        document["unexpected"] = True
        receipt.write_text(json.dumps(document), encoding="utf-8")
        os.chmod(receipt, 0o444)
        with self.assertRaisesRegex(RuntimeError, "shape is invalid"):
            execute_authorized_transition(manifest, receipt)

    def test_disposable_dry_run_writes_only_clone(self):
        connection = self.create_version_3()
        self.seed_semantic_matrix(connection)
        connection.close()
        before = self.database_path.read_bytes()
        workspace = self.root / "disposable"
        report = run_disposable_dry_run(self.database_path, workspace)
        self.assertTrue(report["disposable"])
        self.assertFalse(report["live_target_writes"])
        self.assertEqual(before, self.database_path.read_bytes())
        self.assertEqual(report["target_readiness"]["schema_version"], 4)

    def test_shared_reader_and_writer_block_exclusive_maintenance(self):
        connection = self.create_version_3()
        connection.close()
        context = multiprocessing.get_context("spawn")
        for writer in (False, True):
            with self.subTest(writer=writer):
                ready = context.Queue()
                release = context.Queue()
                process = context.Process(
                    target=_hold_cooperative_connection,
                    args=(str(self.database_path), ready, release),
                    kwargs={"writer": writer},
                )
                process.start()
                self.assertEqual(ready.get(timeout=10), "ready")
                try:
                    with self.assertRaises(LedgerLockTimeout):
                        with exclusive_connection(
                            self.database_path,
                            lock_timeout=0.1,
                        ):
                            pass
                finally:
                    release.put("release")
                    process.join(timeout=10)
                self.assertEqual(process.exitcode, 0)

    def test_concurrent_shared_maintenance_is_rejected_without_lock_loss(self):
        connection = self.create_version_3()
        connection.close()
        context = multiprocessing.get_context("spawn")

        for remaining_worker in (0, 1):
            with self.subTest(remaining_worker=remaining_worker):
                ready = context.Queue()
                start = context.Queue()
                result = context.Queue()
                releases = [context.Queue(), context.Queue()]
                processes = [
                    context.Process(
                        target=_attempt_maintenance_from_shared_connection,
                        args=(
                            str(self.database_path),
                            ready,
                            start,
                            result,
                            releases[index],
                        ),
                    )
                    for index in range(2)
                ]
                for process in processes:
                    process.start()
                self.assertEqual(
                    [ready.get(timeout=10) for _ in processes],
                    ["ready", "ready"],
                )
                for _ in processes:
                    start.put("start")
                observed = [result.get(timeout=10) for _ in processes]
                self.assertTrue(
                    all(
                        item["error"].startswith("RuntimeError:")
                        and "exclusive lock from the outset" in item["error"]
                        and item["mode"] == "shared"
                        and item["descriptor_open"]
                        for item in observed
                    )
                )

                released_worker = 1 - remaining_worker
                releases[released_worker].put("release")
                processes[released_worker].join(timeout=10)
                self.assertEqual(processes[released_worker].exitcode, 0)
                try:
                    with self.assertRaises(LedgerLockTimeout):
                        with exclusive_connection(
                            self.database_path,
                            lock_timeout=0.1,
                        ):
                            pass
                finally:
                    releases[remaining_worker].put("release")
                    processes[remaining_worker].join(timeout=10)
                self.assertEqual(processes[remaining_worker].exitcode, 0)

        with exclusive_connection(
            self.database_path,
            lock_timeout=0.1,
        ):
            pass

    def test_concurrent_initialization_is_multiprocess_safe(self):
        context = multiprocessing.get_context("spawn")
        results = context.Queue()
        processes = [
            context.Process(
                target=_initialize_worker,
                args=(str(self.database_path), results),
            )
            for _ in range(4)
        ]
        for process in processes:
            process.start()
        observed = [results.get(timeout=15) for _ in processes]
        for process in processes:
            process.join(timeout=15)
        self.assertEqual(observed, [4, 4, 4, 4])
        self.assertTrue(all(process.exitcode == 0 for process in processes))
        connection = connect_database(self.database_path)
        try:
            rows = connection.execute(
                "SELECT version, COUNT(*) FROM schema_migrations GROUP BY version"
            ).fetchall()
            self.assertEqual([(row[0], row[1]) for row in rows], [(1, 1), (2, 1), (3, 1), (4, 1)])
        finally:
            connection.close()

    def test_uncooperative_wal_writer_fails_backup_quiescence(self):
        connection = self.create_version_3()
        connection.close()
        context = multiprocessing.get_context("spawn")
        ready = context.Queue()
        release = context.Queue()
        process = context.Process(
            target=_hold_uncooperative_writer,
            args=(str(self.database_path), ready, release),
        )
        process.start()
        self.assertEqual(ready.get(timeout=10), "ready")
        try:
            with self.assertRaisesRegex(RuntimeError, "WAL"):
                create_immutable_backup(
                    self.database_path,
                    self.root / "busy-backup.sqlite3",
                    run_id="busy",
                )
        finally:
            release.put("release")
            process.join(timeout=10)
        self.assertEqual(process.exitcode, 0)

    def test_migration_4_transaction_failure_rolls_back(self):
        connection = self.create_version_3()
        self.seed_semantic_matrix(connection)
        failing = Migration(
            version=4,
            name="product_neutral_sources",
            statements=(
                "CREATE TABLE transition_probe (value TEXT)",
                "THIS IS NOT VALID SQL",
            ),
        )
        try:
            with patch(
                "wingman.core.ledger.migrations.MIGRATIONS",
                (*MIGRATIONS[:3], failing),
            ):
                with self.assertRaises(sqlite3.OperationalError):
                    apply_migrations(
                        connection,
                        target_version=4,
                        allow_existing_transition=True,
                    )
            self.assertEqual(validate_migration_history(connection), 3)
            self.assertIsNone(
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE name = 'transition_probe'"
                ).fetchone()
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(sources)")
            }
            self.assertIn("program", columns)
        finally:
            connection.close()

    def test_restore_recovers_after_every_durable_boundary(self):
        phases = (
            "prepared",
            "staging_validated",
            "failed_preserved",
            "candidate_installed",
            "result_validated",
        )
        for index, phase in enumerate(phases):
            with self.subTest(phase=phase):
                target = self.root / f"restore-{index}.sqlite3"
                connection = connect_database(
                    target,
                    lock_mode="exclusive",
                )
                apply_migrations(connection, target_version=3)
                connection.close()
                backup = self.root / f"restore-{index}-backup.sqlite3"
                create_immutable_backup(target, backup, run_id=f"backup-{index}")
                connection = connect_database(
                    target,
                    lock_mode="exclusive",
                )
                apply_migrations(
                    connection,
                    target_version=4,
                    allow_existing_transition=True,
                )
                connection.close()

                context = multiprocessing.get_context("spawn")
                process = context.Process(
                    target=_terminate_restore_at_phase,
                    args=(
                        str(target),
                        str(backup),
                        f"restore-{index}",
                        phase,
                    ),
                )
                process.start()
                process.join(timeout=15)
                self.assertFalse(process.is_alive())
                self.assertEqual(process.exitcode, 91)
                with self.assertRaisesRegex(RuntimeError, "recovery is incomplete"):
                    connect_database(target)
                result = recover_incomplete(target)
                self.assertIn(result["status"], {"restored", "recovered_without_restore"})
                connection = connect_database(target)
                try:
                    self.assertEqual(validate_readiness(connection)["schema_version"], 3)
                finally:
                    connection.close()

    def test_authorized_post_commit_failure_recovers_exact_backup(self):
        connection = self.create_version_3()
        self.seed_semantic_matrix(connection)
        connection.close()
        manifest, receipt, backup = self.authorization_paths()

        context = multiprocessing.get_context("spawn")
        process = context.Process(
            target=_terminate_transition_at_phase,
            args=(str(manifest), str(receipt), "migration_committed"),
        )
        process.start()
        process.join(timeout=15)
        self.assertFalse(process.is_alive())
        self.assertEqual(process.exitcode, 92)
        with self.assertRaisesRegex(RuntimeError, "recovery is incomplete"):
            connect_database(self.database_path)
        result = recover_incomplete(self.database_path)
        self.assertEqual(result["status"], "restored")
        self.assertEqual(self.database_path.read_bytes(), backup.read_bytes())
        failed_database = Path(result["failed_database"])
        self.assertTrue(failed_database.exists())
        self.assertEqual(failed_database.stat().st_mode & 0o222, 0)
        connection = connect_database(
            self.database_path,
            lock_mode="exclusive",
        )
        try:
            self.assertEqual(validate_readiness(connection)["schema_version"], 3)
        finally:
            connection.close()

    def test_authorized_rollback_restores_version_3_and_preserves_failed_v4(self):
        connection = self.create_version_3()
        connection.close()
        backup = self.root / "rollback-source.sqlite3"
        create_immutable_backup(self.database_path, backup, run_id="rollback-source")
        connection = connect_database(
            self.database_path,
            lock_mode="exclusive",
        )
        apply_migrations(
            connection,
            target_version=4,
            allow_existing_transition=True,
        )
        connection.close()
        manifest, receipt, _ = self.authorization_paths(
            operation="rollback",
            backup=backup,
        )
        result = execute_authorized_transition(manifest, receipt)
        self.assertEqual(result["status"], "restored")
        self.assertTrue(Path(result["failed_database"]).exists())
        connection = connect_database(self.database_path)
        try:
            self.assertEqual(validate_readiness(connection)["schema_version"], 3)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
