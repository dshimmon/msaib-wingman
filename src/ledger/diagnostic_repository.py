"""
Persists typed diagnostic-event records.
"""

from datetime import datetime, timezone

from ledger.database import atomic_repository_write
from ledger.models import (
    DiagnosticEventRecord,
    deserialize_json,
    serialize_json,
)


def utc_now():
    """
    Return a current UTC ISO timestamp.
    """
    return datetime.now(timezone.utc).isoformat()


def diagnostic_event_from_row(row):
    """
    Convert a database row to a diagnostic-event record.
    """
    if row is None:
        return None

    return DiagnosticEventRecord(
        entity_id=row["entity_id"],
        entity_type=row["entity_type"],
        product_key=row["product_key"],
        domain=row["domain"],
        status=row["entity_status"],
        version=row["entity_version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        metadata=deserialize_json(
            row["entity_metadata_json"]
        ),
        trace_id=row["trace_id"],
        operation=row["operation"],
        severity=row["severity"],
        recoverable=bool(row["recoverable"]),
        related_entity_id=row["related_entity_id"],
        message=row["message"],
        details=deserialize_json(
            row["details_json"]
        ),
        occurred_at=row["occurred_at"],
    )


@atomic_repository_write
def create_diagnostic_event(
    connection,
    *,
    entity_id,
    operation,
    severity,
    recoverable,
    message,
    trace_id=None,
    related_entity_id=None,
    details=None,
    status="recorded",
    product_key=None,
    domain=None,
    metadata=None,
    occurred_at=None,
):
    """
    Create one diagnostic event.
    """
    timestamp = occurred_at or utc_now()
    details_json = serialize_json(
        (
            details
            if details is not None
            else {}
        ),
        "details",
        dict,
    )
    connection.execute(
        """
        INSERT INTO entities (
            entity_id,
            entity_type,
            product_key,
            domain,
            status,
            version,
            created_at,
            updated_at,
            metadata_json
        )
        VALUES (
            ?,
            'diagnostic_event',
            ?,
            ?,
            ?,
            1,
            ?,
            ?,
            ?
        )
        """,
        (
            entity_id,
            product_key,
            domain,
            status,
            timestamp,
            timestamp,
            serialize_json(
                (
                    metadata
                    if metadata is not None
                    else {}
                ),
                "metadata",
                dict,
            ),
        ),
    )
    connection.execute(
        """
        INSERT INTO diagnostic_events (
            entity_id,
            trace_id,
            operation,
            severity,
            recoverable,
            related_entity_id,
            message,
            details_json,
            occurred_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_id,
            trace_id,
            operation,
            severity,
            int(recoverable),
            related_entity_id,
            message,
            details_json,
            timestamp,
        ),
    )

    return get_diagnostic_event(
        connection,
        entity_id,
    )


def get_diagnostic_event(connection, entity_id):
    """
    Return one diagnostic-event record by ID.
    """
    row = connection.execute(
        """
        SELECT
            e.entity_id,
            e.entity_type,
            e.product_key,
            e.domain,
            e.status AS entity_status,
            e.version AS entity_version,
            e.created_at,
            e.updated_at,
            e.metadata_json AS entity_metadata_json,
            d.trace_id,
            d.operation,
            d.severity,
            d.recoverable,
            d.related_entity_id,
            d.message,
            d.details_json,
            d.occurred_at
        FROM entities AS e
        JOIN diagnostic_events AS d
            ON d.entity_id = e.entity_id
        WHERE e.entity_id = ?
        """,
        (entity_id,),
    ).fetchone()

    return diagnostic_event_from_row(row)


def _list_diagnostic_events(connection, clause, value):
    rows = connection.execute(
        f"""
        SELECT
            e.entity_id, e.entity_type, e.product_key, e.domain,
            e.status AS entity_status, e.version AS entity_version,
            e.created_at, e.updated_at,
            e.metadata_json AS entity_metadata_json,
            d.trace_id, d.operation, d.severity, d.recoverable,
            d.related_entity_id, d.message, d.details_json, d.occurred_at
        FROM entities AS e
        JOIN diagnostic_events AS d ON d.entity_id = e.entity_id
        WHERE d.{clause} = ?
        ORDER BY d.occurred_at, e.entity_id
        """,
        (value,),
    ).fetchall()
    return [diagnostic_event_from_row(row) for row in rows]


def list_events_for_trace(connection, trace_id):
    """Return diagnostic events belonging to a trace."""
    return _list_diagnostic_events(connection, "trace_id", trace_id)


def list_events_for_related_entity(connection, related_entity_id):
    """Return diagnostic events associated with an entity."""
    return _list_diagnostic_events(
        connection, "related_entity_id", related_entity_id
    )
