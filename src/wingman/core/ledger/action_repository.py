"""
Persists typed action records.
"""

from datetime import datetime, timezone

from wingman.core.ledger.database import atomic_repository_write
from wingman.core.ledger.models import (
    ActionRecord,
    deserialize_json,
    serialize_json,
)


def utc_now():
    """
    Return a current UTC ISO timestamp.
    """
    return datetime.now(timezone.utc).isoformat()


def action_from_row(row):
    """
    Convert a database row to an action record.
    """
    if row is None:
        return None

    return ActionRecord(
        entity_id=row["entity_id"],
        entity_type=row["entity_type"],
        product_key=row["product_key"],
        domain=row["domain"],
        status=row["action_status"],
        version=row["entity_version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        metadata=deserialize_json(
            row["entity_metadata_json"]
        ),
        origin_type=row["origin_type"],
        origin_entity_id=row["origin_entity_id"],
        origin_item_key=row["origin_item_key"],
        title=row["title"],
        priority=row["priority"],
        action_status=row["action_status"],
        due_at=row["due_at"],
        notes=row["notes"],
        approved_at=row["approved_at"],
        completed_at=row["completed_at"],
    )


@atomic_repository_write
def create_action(
    connection,
    *,
    entity_id,
    title,
    status,
    origin_type=None,
    origin_entity_id=None,
    origin_item_key=None,
    priority=None,
    due_at=None,
    notes=None,
    approved_at=None,
    completed_at=None,
    product_key=None,
    domain=None,
    metadata=None,
    created_at=None,
):
    """
    Create one action entity and specialized action row.
    """
    timestamp = created_at or utc_now()
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
        VALUES (?, 'action', ?, ?, ?, 1, ?, ?, ?)
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
        INSERT INTO actions (
            entity_id,
            origin_type,
            origin_entity_id,
            origin_item_key,
            title,
            priority,
            status,
            due_at,
            notes,
            approved_at,
            completed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_id,
            origin_type,
            origin_entity_id,
            origin_item_key,
            title,
            priority,
            status,
            due_at,
            notes,
            approved_at,
            completed_at,
        ),
    )

    return get_action(connection, entity_id)


def get_action(connection, entity_id):
    """
    Return one action record by ID.
    """
    row = connection.execute(
        """
        SELECT
            e.entity_id,
            e.entity_type,
            e.product_key,
            e.domain,
            e.version AS entity_version,
            e.created_at,
            e.updated_at,
            e.metadata_json AS entity_metadata_json,
            a.origin_type,
            a.origin_entity_id,
            a.origin_item_key,
            a.title,
            a.priority,
            a.status AS action_status,
            a.due_at,
            a.notes,
            a.approved_at,
            a.completed_at
        FROM entities AS e
        JOIN actions AS a
            ON a.entity_id = e.entity_id
        WHERE e.entity_id = ?
        """,
        (entity_id,),
    ).fetchone()

    return action_from_row(row)


@atomic_repository_write
def update_action_status(
    connection,
    entity_id,
    status,
    *,
    approved_at=None,
    completed_at=None,
    updated_at=None,
):
    """
    Update an action status and lifecycle timestamps.
    """
    timestamp = updated_at or utc_now()
    cursor = connection.execute(
        """
        UPDATE actions
        SET
            status = ?,
            approved_at = COALESCE(?, approved_at),
            completed_at = COALESCE(?, completed_at)
        WHERE entity_id = ?
        """,
        (
            status,
            approved_at,
            completed_at,
            entity_id,
        ),
    )

    if cursor.rowcount != 1:
        raise KeyError(
            f"Unknown action: {entity_id}"
        )

    connection.execute(
        """
        UPDATE entities
        SET
            status = ?,
            version = version + 1,
            updated_at = ?
        WHERE entity_id = ?
        """,
        (status, timestamp, entity_id),
    )

    return get_action(connection, entity_id)
