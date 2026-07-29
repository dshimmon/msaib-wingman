"""
Persists typed briefing and briefing-version records.
"""

from datetime import datetime, timezone

from ledger.database import atomic_repository_write
from ledger.models import (
    BriefingRecord,
    BriefingVersionRecord,
    deserialize_json,
    serialize_json,
)


def utc_now():
    """
    Return a current UTC ISO timestamp.
    """
    return datetime.now(timezone.utc).isoformat()


def insert_entity(
    connection,
    entity_id,
    entity_type,
    product_key,
    domain,
    status,
    created_at,
    metadata,
):
    """
    Insert one shared entity row.
    """
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
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            entity_id,
            entity_type,
            product_key,
            domain,
            status,
            created_at,
            created_at,
            serialize_json(
                metadata,
                "metadata",
                dict,
            ),
        ),
    )


def briefing_from_row(row):
    """
    Convert a database row to a briefing record.
    """
    if row is None:
        return None

    return BriefingRecord(
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
        topic=row["topic"],
        title=row["title"],
        current_briefing_version_id=(
            row["current_briefing_version_id"]
        ),
    )


def briefing_version_from_row(row):
    """
    Convert a database row to a briefing-version record.
    """
    if row is None:
        return None

    return BriefingVersionRecord(
        entity_id=row["entity_id"],
        entity_type=row["entity_type"],
        product_key=row["product_key"],
        domain=row["domain"],
        status=row["entity_status"],
        version=row["entity_version"],
        created_at=row["entity_created_at"],
        updated_at=row["updated_at"],
        metadata=deserialize_json(
            row["entity_metadata_json"]
        ),
        briefing_id=row["briefing_id"],
        version_number=row["version_number"],
        request_text=row["request_text"],
        planner_type=row["planner_type"],
        briefing=deserialize_json(
            row["briefing_json"]
        ),
        retrieval_results=deserialize_json(
            row["retrieval_results_json"]
        ),
        evidence_snapshot=deserialize_json(
            row["evidence_snapshot_json"]
        ),
        source_fingerprint=row["source_fingerprint"],
        version_created_at=row["version_created_at"],
    )


@atomic_repository_write
def create_briefing(
    connection,
    *,
    entity_id,
    topic,
    title,
    status="active",
    product_key=None,
    domain=None,
    metadata=None,
    created_at=None,
):
    """
    Create a briefing entity and specialized row.
    """
    timestamp = created_at or utc_now()
    insert_entity(
        connection,
        entity_id,
        "briefing",
        product_key,
        domain,
        status,
        timestamp,
        (
            metadata
            if metadata is not None
            else {}
        ),
    )
    connection.execute(
        """
        INSERT INTO briefings (
            entity_id,
            topic,
            title,
            current_briefing_version_id
        )
        VALUES (?, ?, ?, NULL)
        """,
        (entity_id, topic, title),
    )

    return get_briefing(connection, entity_id)


def get_briefing(connection, entity_id):
    """
    Return one briefing record by ID.
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
            b.topic,
            b.title,
            b.current_briefing_version_id
        FROM entities AS e
        JOIN briefings AS b
            ON b.entity_id = e.entity_id
        WHERE e.entity_id = ?
        """,
        (entity_id,),
    ).fetchone()

    return briefing_from_row(row)


@atomic_repository_write
def create_briefing_version(
    connection,
    *,
    entity_id,
    briefing_id,
    version_number,
    request_text,
    planner_type,
    briefing,
    retrieval_results,
    evidence_snapshot,
    source_fingerprint=None,
    status="created",
    product_key=None,
    domain=None,
    metadata=None,
    created_at=None,
    make_current=True,
):
    """
    Create a briefing version and optionally make it current.
    """
    timestamp = created_at or utc_now()
    briefing_json = serialize_json(
        briefing,
        "briefing",
        dict,
    )
    retrieval_results_json = serialize_json(
        retrieval_results,
        "retrieval_results",
        list,
    )
    evidence_snapshot_json = serialize_json(
        evidence_snapshot,
        "evidence_snapshot",
        list,
    )
    insert_entity(
        connection,
        entity_id,
        "briefing_version",
        product_key,
        domain,
        status,
        timestamp,
        (
            metadata
            if metadata is not None
            else {}
        ),
    )
    connection.execute(
        """
        INSERT INTO briefing_versions (
            entity_id,
            briefing_id,
            version_number,
            request_text,
            planner_type,
            briefing_json,
            retrieval_results_json,
            evidence_snapshot_json,
            source_fingerprint,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_id,
            briefing_id,
            version_number,
            request_text,
            planner_type,
            briefing_json,
            retrieval_results_json,
            evidence_snapshot_json,
            source_fingerprint,
            timestamp,
        ),
    )

    if make_current:
        set_current_briefing_version(
            connection,
            briefing_id,
            entity_id,
            updated_at=timestamp,
        )

    return get_briefing_version(
        connection,
        entity_id,
    )


@atomic_repository_write
def set_current_briefing_version(
    connection,
    briefing_id,
    briefing_version_id,
    *,
    updated_at=None,
):
    """
    Point a briefing at one of its versions.
    """
    version_row = connection.execute(
        """
        SELECT briefing_id
        FROM briefing_versions
        WHERE entity_id = ?
        """,
        (briefing_version_id,),
    ).fetchone()

    if (
        version_row is None
        or version_row["briefing_id"] != briefing_id
    ):
        raise ValueError(
            "Current briefing version must belong "
            "to the briefing."
        )

    briefing_row = connection.execute(
        """
        SELECT current_briefing_version_id
        FROM briefings
        WHERE entity_id = ?
        """,
        (briefing_id,),
    ).fetchone()

    if briefing_row is None:
        raise KeyError(
            f"Unknown briefing: {briefing_id}"
        )

    if (
        briefing_row["current_briefing_version_id"]
        == briefing_version_id
    ):
        return

    timestamp = updated_at or utc_now()
    connection.execute(
        """
        UPDATE briefings
        SET current_briefing_version_id = ?
        WHERE entity_id = ?
        """,
        (briefing_version_id, briefing_id),
    )

    connection.execute(
        """
        UPDATE entities
        SET
            version = version + 1,
            updated_at = ?
        WHERE entity_id = ?
        """,
        (timestamp, briefing_id),
    )


def get_briefing_version(connection, entity_id):
    """
    Return one briefing-version record by ID.
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
            e.created_at AS entity_created_at,
            e.updated_at,
            e.metadata_json AS entity_metadata_json,
            bv.briefing_id,
            bv.version_number,
            bv.request_text,
            bv.planner_type,
            bv.briefing_json,
            bv.retrieval_results_json,
            bv.evidence_snapshot_json,
            bv.source_fingerprint,
            bv.created_at AS version_created_at
        FROM entities AS e
        JOIN briefing_versions AS bv
            ON bv.entity_id = e.entity_id
        WHERE e.entity_id = ?
        """,
        (entity_id,),
    ).fetchone()

    return briefing_version_from_row(row)
