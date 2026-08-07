"""
Persists durable markers for one-time legacy imports.
"""

from dataclasses import dataclass

from wingman.core.ledger.database import atomic_repository_write
from wingman.core.ledger.models import deserialize_json, serialize_json


@dataclass(frozen=True)
class LegacyImportRecord:
    import_key: str
    status: str
    completed_at: str
    details: dict


def get_legacy_import(connection, import_key):
    """
    Return a legacy-import marker by stable key.
    """
    row = connection.execute(
        """
        SELECT import_key, status, completed_at, details_json
        FROM legacy_imports
        WHERE import_key = ?
        """,
        (import_key,),
    ).fetchone()
    if row is None:
        return None
    return LegacyImportRecord(
        import_key=row["import_key"],
        status=row["status"],
        completed_at=row["completed_at"],
        details=deserialize_json(row["details_json"]),
    )


@atomic_repository_write
def record_legacy_import(
    connection,
    *,
    import_key,
    status,
    completed_at,
    details=None,
):
    """
    Record a completed or intentionally skipped import.
    """
    connection.execute(
        """
        INSERT INTO legacy_imports (
            import_key, status, completed_at, details_json
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            import_key,
            status,
            completed_at,
            serialize_json(details or {}, "details", dict),
        ),
    )
    return get_legacy_import(connection, import_key)
