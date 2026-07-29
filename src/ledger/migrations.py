"""
Applies ordered Ledger database schema migrations.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from ledger.database import transaction


@dataclass(frozen=True)
class Migration:
    """
    One ordered database schema migration.
    """

    version: int
    name: str
    statements: tuple[str, ...]


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
)


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


def apply_migrations(connection):
    """
    Apply every unapplied migration in order.
    """
    with transaction(connection):
        ensure_migration_table(connection)

    applied_versions = get_applied_versions(
        connection
    )

    for migration in MIGRATIONS:
        if migration.version in applied_versions:
            continue

        with transaction(connection):
            for statement in migration.statements:
                connection.execute(statement)

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

    return get_applied_versions(connection)
