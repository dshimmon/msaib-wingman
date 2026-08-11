"""
Applies ordered Ledger database schema migrations.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from wingman.core.ledger.database import (
    exclusive_connection_lock,
    transaction,
)
from wingman.core.ledger.models import serialize_json


@dataclass(frozen=True)
class Migration:
    """
    One ordered database schema migration.
    """

    version: int
    name: str
    statements: tuple[str, ...]
    rebuilds_foreign_keys: bool = False


INITIAL_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE entities (
        entity_id TEXT PRIMARY KEY,
        entity_type TEXT NOT NULL,
        product_key TEXT NULL,
        domain TEXT NULL,
        status TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE sources (
        entity_id TEXT PRIMARY KEY,
        source_kind TEXT NOT NULL,
        display_name TEXT NOT NULL,
        file_name TEXT NULL,
        file_type TEXT NULL,
        mime_type TEXT NULL,
        program TEXT NULL,
        academic_year TEXT NULL,
        source_url TEXT NULL,
        original_path TEXT NULL,
        current_source_version_id TEXT NULL,
        FOREIGN KEY (entity_id)
            REFERENCES entities(entity_id)
            ON DELETE CASCADE,
        FOREIGN KEY (current_source_version_id)
            REFERENCES source_versions(entity_id)
            ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE source_versions (
        entity_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        content_hash TEXT NOT NULL,
        original_path TEXT NULL,
        captured_at TEXT NOT NULL,
        change_type TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        FOREIGN KEY (entity_id)
            REFERENCES entities(entity_id)
            ON DELETE CASCADE,
        FOREIGN KEY (source_id)
            REFERENCES sources(entity_id)
            ON DELETE RESTRICT,
        UNIQUE (source_id, version_number)
    )
    """,
    """
    CREATE TABLE briefings (
        entity_id TEXT PRIMARY KEY,
        topic TEXT NOT NULL,
        title TEXT NOT NULL,
        current_briefing_version_id TEXT NULL,
        FOREIGN KEY (entity_id)
            REFERENCES entities(entity_id)
            ON DELETE CASCADE,
        FOREIGN KEY (current_briefing_version_id)
            REFERENCES briefing_versions(entity_id)
            ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE briefing_versions (
        entity_id TEXT PRIMARY KEY,
        briefing_id TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        request_text TEXT NOT NULL,
        planner_type TEXT NOT NULL,
        briefing_json TEXT NOT NULL,
        retrieval_results_json TEXT NOT NULL,
        evidence_snapshot_json TEXT NOT NULL,
        source_fingerprint TEXT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (entity_id)
            REFERENCES entities(entity_id)
            ON DELETE CASCADE,
        FOREIGN KEY (briefing_id)
            REFERENCES briefings(entity_id)
            ON DELETE RESTRICT,
        UNIQUE (briefing_id, version_number)
    )
    """,
    """
    CREATE TABLE actions (
        entity_id TEXT PRIMARY KEY,
        origin_type TEXT NULL,
        origin_entity_id TEXT NULL,
        origin_item_key TEXT NULL,
        title TEXT NOT NULL,
        priority TEXT NULL,
        status TEXT NOT NULL,
        due_at TEXT NULL,
        notes TEXT NULL,
        approved_at TEXT NULL,
        completed_at TEXT NULL,
        FOREIGN KEY (entity_id)
            REFERENCES entities(entity_id)
            ON DELETE CASCADE,
        FOREIGN KEY (origin_entity_id)
            REFERENCES entities(entity_id)
            ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE diagnostic_events (
        entity_id TEXT PRIMARY KEY,
        trace_id TEXT NULL,
        operation TEXT NOT NULL,
        severity TEXT NOT NULL,
        recoverable INTEGER NOT NULL,
        related_entity_id TEXT NULL,
        message TEXT NOT NULL,
        details_json TEXT NOT NULL DEFAULT '{}',
        occurred_at TEXT NOT NULL,
        FOREIGN KEY (entity_id)
            REFERENCES entities(entity_id)
            ON DELETE CASCADE,
        FOREIGN KEY (related_entity_id)
            REFERENCES entities(entity_id)
            ON DELETE SET NULL,
        CHECK (recoverable IN (0, 1))
    )
    """,
    """
    CREATE INDEX source_versions_source_id_index
    ON source_versions(source_id)
    """,
    """
    CREATE TRIGGER sources_current_version_insert_guard
    BEFORE INSERT ON sources
    WHEN NEW.current_source_version_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM source_versions
          WHERE entity_id = NEW.current_source_version_id
            AND source_id = NEW.entity_id
      )
    BEGIN
        SELECT RAISE(
            ABORT,
            'Current source version must belong to the source.'
        );
    END
    """,
    """
    CREATE TRIGGER sources_current_version_update_guard
    BEFORE UPDATE OF current_source_version_id ON sources
    WHEN NEW.current_source_version_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM source_versions
          WHERE entity_id = NEW.current_source_version_id
            AND source_id = NEW.entity_id
      )
    BEGIN
        SELECT RAISE(
            ABORT,
            'Current source version must belong to the source.'
        );
    END
    """,
    """
    CREATE INDEX briefing_versions_briefing_id_index
    ON briefing_versions(briefing_id)
    """,
    """
    CREATE TRIGGER briefings_current_version_insert_guard
    BEFORE INSERT ON briefings
    WHEN NEW.current_briefing_version_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM briefing_versions
          WHERE entity_id = NEW.current_briefing_version_id
            AND briefing_id = NEW.entity_id
      )
    BEGIN
        SELECT RAISE(
            ABORT,
            'Current briefing version must belong to the briefing.'
        );
    END
    """,
    """
    CREATE TRIGGER briefings_current_version_update_guard
    BEFORE UPDATE OF current_briefing_version_id ON briefings
    WHEN NEW.current_briefing_version_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM briefing_versions
          WHERE entity_id = NEW.current_briefing_version_id
            AND briefing_id = NEW.entity_id
      )
    BEGIN
        SELECT RAISE(
            ABORT,
            'Current briefing version must belong to the briefing.'
        );
    END
    """,
    """
    CREATE INDEX actions_origin_entity_id_index
    ON actions(origin_entity_id)
    """,
    """
    CREATE INDEX diagnostic_events_trace_id_index
    ON diagnostic_events(trace_id)
    """,
)


MIGRATIONS = (
    Migration(
        version=1,
        name="initial_ledger_schema",
        statements=INITIAL_SCHEMA_STATEMENTS,
    ),
    Migration(
        version=2,
        name="legacy_import_tracking",
        statements=(
            """
            CREATE TABLE legacy_imports (
                import_key TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '{}'
            )
            """,
        ),
    ),
    Migration(
        version=3,
        name="nullable_source_version_content_hash",
        rebuilds_foreign_keys=True,
        statements=(
            """
            DROP TRIGGER sources_current_version_insert_guard
            """,
            """
            DROP TRIGGER sources_current_version_update_guard
            """,
            """
            CREATE TABLE source_versions_rebuilt (
                entity_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                content_hash TEXT NULL,
                original_path TEXT NULL,
                captured_at TEXT NOT NULL,
                change_type TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (entity_id)
                    REFERENCES entities(entity_id)
                    ON DELETE CASCADE,
                FOREIGN KEY (source_id)
                    REFERENCES sources(entity_id)
                    ON DELETE RESTRICT,
                UNIQUE (source_id, version_number)
            )
            """,
            """
            INSERT INTO source_versions_rebuilt (
                entity_id,
                source_id,
                version_number,
                content_hash,
                original_path,
                captured_at,
                change_type,
                metadata_json
            )
            SELECT
                entity_id,
                source_id,
                version_number,
                NULLIF(content_hash, ''),
                original_path,
                captured_at,
                change_type,
                metadata_json
            FROM source_versions
            """,
            """
            DROP INDEX source_versions_source_id_index
            """,
            """
            DROP TABLE source_versions
            """,
            """
            ALTER TABLE source_versions_rebuilt
            RENAME TO source_versions
            """,
            """
            CREATE INDEX source_versions_source_id_index
            ON source_versions(source_id)
            """,
            """
            CREATE TRIGGER sources_current_version_insert_guard
            BEFORE INSERT ON sources
            WHEN NEW.current_source_version_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM source_versions
                  WHERE entity_id = NEW.current_source_version_id
                    AND source_id = NEW.entity_id
              )
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'Current source version must belong to the source.'
                );
            END
            """,
            """
            CREATE TRIGGER sources_current_version_update_guard
            BEFORE UPDATE OF current_source_version_id ON sources
            WHEN NEW.current_source_version_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM source_versions
                  WHERE entity_id = NEW.current_source_version_id
                    AND source_id = NEW.entity_id
              )
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'Current source version must belong to the source.'
                );
            END
            """,
        ),
    ),
    Migration(
        version=4,
        name="product_neutral_sources",
        rebuilds_foreign_keys=True,
        statements=(
            """
            DROP TRIGGER sources_current_version_insert_guard
            """,
            """
            DROP TRIGGER sources_current_version_update_guard
            """,
            """
            CREATE TABLE sources_rebuilt (
                entity_id TEXT PRIMARY KEY,
                source_kind TEXT NOT NULL,
                display_name TEXT NOT NULL,
                file_name TEXT NULL,
                file_type TEXT NULL,
                mime_type TEXT NULL,
                source_url TEXT NULL,
                original_path TEXT NULL,
                current_source_version_id TEXT NULL,
                FOREIGN KEY (entity_id)
                    REFERENCES entities(entity_id)
                    ON DELETE CASCADE,
                FOREIGN KEY (current_source_version_id)
                    REFERENCES source_versions(entity_id)
                    ON DELETE SET NULL
            )
            """,
            """
            INSERT INTO sources_rebuilt (
                entity_id,
                source_kind,
                display_name,
                file_name,
                file_type,
                mime_type,
                source_url,
                original_path,
                current_source_version_id
            )
            SELECT
                entity_id,
                source_kind,
                display_name,
                file_name,
                file_type,
                mime_type,
                source_url,
                original_path,
                current_source_version_id
            FROM sources
            """,
            """
            DROP TABLE sources
            """,
            """
            ALTER TABLE sources_rebuilt
            RENAME TO sources
            """,
            """
            CREATE TRIGGER sources_current_version_insert_guard
            BEFORE INSERT ON sources
            WHEN NEW.current_source_version_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM source_versions
                  WHERE entity_id = NEW.current_source_version_id
                    AND source_id = NEW.entity_id
              )
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'Current source version must belong to the source.'
                );
            END
            """,
            """
            CREATE TRIGGER sources_current_version_update_guard
            BEFORE UPDATE OF current_source_version_id ON sources
            WHEN NEW.current_source_version_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM source_versions
                  WHERE entity_id = NEW.current_source_version_id
                    AND source_id = NEW.entity_id
              )
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'Current source version must belong to the source.'
                );
            END
            """,
        ),
    ),
)

MIGRATION_NAMES = {
    migration.version: migration.name
    for migration in MIGRATIONS
}
APPLICATION_AUTO_MIGRATION_VERSION = 3


def ensure_migration_table(connection):
    """
    Create the migration ledger if it does not exist.
    """
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def get_applied_versions(connection):
    """
    Return migration versions already applied.
    """
    rows = connection.execute(
        """
        SELECT version
        FROM schema_migrations
        ORDER BY version
        """
    ).fetchall()

    return {
        row["version"]
        for row in rows
    }


def get_migration_history(connection):
    """Return the complete applied history without hiding duplicates."""
    table = connection.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name = 'schema_migrations'
        """
    ).fetchone()
    if table is None:
        return []
    return connection.execute(
        """
        SELECT version, name, applied_at
        FROM schema_migrations
        ORDER BY version, rowid
        """
    ).fetchall()


def validate_migration_history(connection, *, allow_empty=False):
    """Reject altered, discontinuous, duplicated, or future history."""
    rows = get_migration_history(connection)
    if not rows:
        if allow_empty:
            return 0
        raise RuntimeError("Ledger migration history is missing.")

    versions = [row["version"] for row in rows]
    if len(versions) != len(set(versions)):
        raise RuntimeError("Ledger migration history contains duplicates.")
    if any(not isinstance(version, int) for version in versions):
        raise RuntimeError("Ledger migration versions must be integers.")
    if versions != list(range(1, versions[-1] + 1)):
        raise RuntimeError("Ledger migration history contains a gap.")
    if versions[-1] > max(MIGRATION_NAMES):
        raise RuntimeError("Ledger has an unknown future migration version.")
    for row in rows:
        expected_name = MIGRATION_NAMES.get(row["version"])
        if row["name"] != expected_name:
            raise RuntimeError(
                "Ledger migration history contains a name mismatch."
            )
    return versions[-1]


def _database_has_user_tables(connection):
    return connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        LIMIT 1
        """
    ).fetchone() is not None


def _promote_version_3_source_metadata(connection):
    """Apply the exact missing-key fallback allowed by Migration 4."""
    rows = connection.execute(
        """
        SELECT e.entity_id, e.metadata_json, s.program, s.academic_year
        FROM entities AS e
        JOIN sources AS s ON s.entity_id = e.entity_id
        ORDER BY e.entity_id
        """
    ).fetchall()
    for row in rows:
        try:
            metadata = json.loads(row["metadata_json"])
        except (TypeError, json.JSONDecodeError) as error:
            raise RuntimeError(
                "Source metadata is not valid JSON."
            ) from error
        if not isinstance(metadata, dict):
            raise RuntimeError("Source metadata must contain a JSON object.")

        updated = dict(metadata)
        if "program" not in updated and row["program"] is not None:
            updated["program"] = row["program"]
        if (
            "academic_year" not in updated
            and row["academic_year"] is not None
        ):
            updated["academic_year"] = row["academic_year"]
        if updated != metadata:
            connection.execute(
                """
                UPDATE entities SET metadata_json = ?
                WHERE entity_id = ?
                """,
                (
                    serialize_json(updated, "source metadata", dict),
                    row["entity_id"],
                ),
            )


def migration_plan_digest():
    """Bind the immutable ordered Migration 4 implementation."""
    migration = MIGRATIONS[3]
    payload = json.dumps(
        {
            "version": migration.version,
            "name": migration.name,
            "statements": migration.statements,
            "fallback_rule": (
                "present metadata keys win including null; only missing "
                "keys inherit non-null legacy values"
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def apply_migrations(
    connection,
    *,
    target_version=None,
    allow_existing_transition=False,
):
    """
    Apply every unapplied migration in order.
    """
    with exclusive_connection_lock(connection):
        was_existing = _database_has_user_tables(connection)
        with transaction(connection):
            ensure_migration_table(connection)

        current_version = validate_migration_history(
            connection,
            allow_empty=True,
        )
        available_versions = {
            migration.version for migration in MIGRATIONS
        }
        latest_available = max(available_versions)
        if target_version is None:
            if not was_existing and current_version == 0:
                target_version = latest_available
            elif current_version >= 4:
                target_version = current_version
            else:
                target_version = min(
                    APPLICATION_AUTO_MIGRATION_VERSION,
                    latest_available,
                )
        if target_version not in available_versions:
            raise ValueError("Unknown Ledger migration target.")
        if target_version < current_version:
            raise RuntimeError("Ledger migrations cannot run backwards.")
        if (
            target_version >= 4
            and was_existing
            and current_version < 4
            and not allow_existing_transition
        ):
            raise RuntimeError(
                "Migration 4 requires an exact authorized transition."
            )

        applied_versions = get_applied_versions(connection)
        for migration in MIGRATIONS:
            if migration.version > target_version:
                continue
            if migration.version in applied_versions:
                continue

            if migration.rebuilds_foreign_keys:
                connection.execute(
                    "PRAGMA foreign_keys = OFF"
                )

            try:
                with transaction(connection):
                    if migration.version == 4:
                        _promote_version_3_source_metadata(connection)
                    for statement in migration.statements:
                        connection.execute(statement)

                    if migration.rebuilds_foreign_keys:
                        violations = connection.execute(
                            "PRAGMA foreign_key_check"
                        ).fetchall()
                        if violations:
                            raise RuntimeError(
                                "Foreign-key violations detected "
                                f"during migration {migration.version}."
                            )

                    connection.execute(
                        """
                        INSERT INTO schema_migrations (
                            version,
                            name,
                            applied_at
                        )
                        VALUES (?, ?, ?)
                        """,
                        (
                            migration.version,
                            migration.name,
                            datetime.now(
                                timezone.utc
                            ).isoformat(),
                        ),
                    )
            finally:
                if migration.rebuilds_foreign_keys:
                    connection.execute(
                        "PRAGMA foreign_keys = ON"
                    )

        validate_migration_history(connection)
        return get_applied_versions(connection)
