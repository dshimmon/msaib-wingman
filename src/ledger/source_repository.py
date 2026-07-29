"""
Persists typed source and source-version records.
"""

from datetime import datetime, timezone

from ledger.database import atomic_repository_write
from ledger.models import (
    SourceRecord,
    SourceVersionRecord,
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
    version,
    created_at,
    updated_at,
    metadata,
):
    """
    Insert one shared entity row.
    """
    metadata_json = serialize_json(
        metadata,
        "metadata",
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_id,
            entity_type,
            product_key,
            domain,
            status,
            version,
            created_at,
            updated_at,
            metadata_json,
        ),
    )


def source_from_row(row):
    """
    Convert a database row to a source record.
    """
    if row is None:
        return None

    return SourceRecord(
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
        source_kind=row["source_kind"],
        display_name=row["display_name"],
        file_name=row["file_name"],
        file_type=row["file_type"],
        mime_type=row["mime_type"],
        program=row["program"],
        academic_year=row["academic_year"],
        source_url=row["source_url"],
        original_path=row["original_path"],
        current_source_version_id=(
            row["current_source_version_id"]
        ),
    )


def source_version_from_row(row):
    """
    Convert a database row to a source-version record.
    """
    if row is None:
        return None

    return SourceVersionRecord(
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
        source_id=row["source_id"],
        version_number=row["version_number"],
        content_hash=row["content_hash"],
        original_path=row["original_path"],
        captured_at=row["captured_at"],
        change_type=row["change_type"],
        version_metadata=deserialize_json(
            row["version_metadata_json"]
        ),
    )


@atomic_repository_write
def create_source(
    connection,
    *,
    entity_id,
    source_kind,
    display_name,
    status="active",
    product_key=None,
    domain=None,
    file_name=None,
    file_type=None,
    mime_type=None,
    program=None,
    academic_year=None,
    source_url=None,
    original_path=None,
    metadata=None,
    created_at=None,
):
    """
    Create a source entity and specialized source row.
    """
    timestamp = created_at or utc_now()
    insert_entity(
        connection,
        entity_id,
        "source",
        product_key,
        domain,
        status,
        1,
        timestamp,
        timestamp,
        (
            metadata
            if metadata is not None
            else {}
        ),
    )
    connection.execute(
        """
        INSERT INTO sources (
            entity_id,
            source_kind,
            display_name,
            file_name,
            file_type,
            mime_type,
            program,
            academic_year,
            source_url,
            original_path,
            current_source_version_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            entity_id,
            source_kind,
            display_name,
            file_name,
            file_type,
            mime_type,
            program,
            academic_year,
            source_url,
            original_path,
        ),
    )

    return get_source(connection, entity_id)


def get_source(connection, entity_id):
    """
    Return one source record by ID.
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
            s.source_kind,
            s.display_name,
            s.file_name,
            s.file_type,
            s.mime_type,
            s.program,
            s.academic_year,
            s.source_url,
            s.original_path,
            s.current_source_version_id
        FROM entities AS e
        JOIN sources AS s
            ON s.entity_id = e.entity_id
        WHERE e.entity_id = ?
        """,
        (entity_id,),
    ).fetchone()

    return source_from_row(row)


def list_sources(connection, *, status=None):
    """
    Return sources, optionally filtered by entity status.
    """
    parameters = ()
    status_clause = ""
    if status is not None:
        status_clause = "WHERE e.status = ?"
        parameters = (status,)

    rows = connection.execute(
        f"""
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
            s.source_kind,
            s.display_name,
            s.file_name,
            s.file_type,
            s.mime_type,
            s.program,
            s.academic_year,
            s.source_url,
            s.original_path,
            s.current_source_version_id
        FROM entities AS e
        JOIN sources AS s
            ON s.entity_id = e.entity_id
        {status_clause}
        ORDER BY e.entity_id
        """,
        parameters,
    ).fetchall()

    return [source_from_row(row) for row in rows]


def list_active_sources(connection):
    """
    Return active sources in stable ID order.
    """
    return list_sources(connection, status="active")


@atomic_repository_write
def update_source(
    connection,
    entity_id,
    *,
    source_kind,
    display_name,
    status,
    domain=None,
    file_name=None,
    file_type=None,
    mime_type=None,
    program=None,
    academic_year=None,
    source_url=None,
    original_path=None,
    metadata=None,
    updated_at=None,
):
    """
    Replace one source's current metadata and status.
    """
    if get_source(connection, entity_id) is None:
        raise KeyError(f"Unknown source: {entity_id}")

    timestamp = updated_at or utc_now()
    metadata_json = serialize_json(
        metadata if metadata is not None else {},
        "metadata",
        dict,
    )
    connection.execute(
        """
        UPDATE entities
        SET domain = ?, status = ?, version = version + 1,
            updated_at = ?, metadata_json = ?
        WHERE entity_id = ?
        """,
        (
            domain,
            status,
            timestamp,
            metadata_json,
            entity_id,
        ),
    )
    connection.execute(
        """
        UPDATE sources
        SET source_kind = ?, display_name = ?, file_name = ?,
            file_type = ?, mime_type = ?, program = ?,
            academic_year = ?, source_url = ?,
            original_path = ?
        WHERE entity_id = ?
        """,
        (
            source_kind,
            display_name,
            file_name,
            file_type,
            mime_type,
            program,
            academic_year,
            source_url,
            original_path,
            entity_id,
        ),
    )
    return get_source(connection, entity_id)


@atomic_repository_write
def set_source_status(
    connection,
    entity_id,
    status,
    *,
    updated_at=None,
):
    """
    Mark one source active or removed.
    """
    source = get_source(connection, entity_id)
    if source is None:
        raise KeyError(f"Unknown source: {entity_id}")
    if source.status == status:
        return source

    connection.execute(
        """
        UPDATE entities
        SET status = ?, version = version + 1, updated_at = ?
        WHERE entity_id = ?
        """,
        (status, updated_at or utc_now(), entity_id),
    )
    return get_source(connection, entity_id)


@atomic_repository_write
def create_source_version(
    connection,
    *,
    entity_id,
    source_id,
    version_number,
    content_hash,
    change_type,
    original_path=None,
    status="captured",
    product_key=None,
    domain=None,
    metadata=None,
    version_metadata=None,
    captured_at=None,
    make_current=True,
):
    """
    Create a source version and optionally make it current.
    """
    timestamp = captured_at or utc_now()
    version_metadata_json = serialize_json(
        (
            version_metadata
            if version_metadata is not None
            else {}
        ),
        "version_metadata",
        dict,
    )
    insert_entity(
        connection,
        entity_id,
        "source_version",
        product_key,
        domain,
        status,
        1,
        timestamp,
        timestamp,
        (
            metadata
            if metadata is not None
            else {}
        ),
    )
    connection.execute(
        """
        INSERT INTO source_versions (
            entity_id,
            source_id,
            version_number,
            content_hash,
            original_path,
            captured_at,
            change_type,
            metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_id,
            source_id,
            version_number,
            content_hash,
            original_path,
            timestamp,
            change_type,
            version_metadata_json,
        ),
    )

    if make_current:
        set_current_source_version(
            connection,
            source_id,
            entity_id,
            updated_at=timestamp,
        )

    return get_source_version(
        connection,
        entity_id,
    )


@atomic_repository_write
def set_current_source_version(
    connection,
    source_id,
    source_version_id,
    *,
    updated_at=None,
):
    """
    Point a source at one of its versions.
    """
    version_row = connection.execute(
        """
        SELECT source_id
        FROM source_versions
        WHERE entity_id = ?
        """,
        (source_version_id,),
    ).fetchone()

    if (
        version_row is None
        or version_row["source_id"] != source_id
    ):
        raise ValueError(
            "Current source version must belong "
            "to the source."
        )

    source_row = connection.execute(
        """
        SELECT current_source_version_id
        FROM sources
        WHERE entity_id = ?
        """,
        (source_id,),
    ).fetchone()

    if source_row is None:
        raise KeyError(
            f"Unknown source: {source_id}"
        )

    if (
        source_row["current_source_version_id"]
        == source_version_id
    ):
        return

    timestamp = updated_at or utc_now()
    connection.execute(
        """
        UPDATE sources
        SET current_source_version_id = ?
        WHERE entity_id = ?
        """,
        (source_version_id, source_id),
    )

    connection.execute(
        """
        UPDATE entities
        SET
            version = version + 1,
            updated_at = ?
        WHERE entity_id = ?
        """,
        (timestamp, source_id),
    )


def get_source_version(connection, entity_id):
    """
    Return one source-version record by ID.
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
            sv.source_id,
            sv.version_number,
            sv.content_hash,
            sv.original_path,
            sv.captured_at,
            sv.change_type,
            sv.metadata_json AS version_metadata_json
        FROM entities AS e
        JOIN source_versions AS sv
            ON sv.entity_id = e.entity_id
        WHERE e.entity_id = ?
        """,
        (entity_id,),
    ).fetchone()

    return source_version_from_row(row)


def list_source_versions(connection, source_id):
    """
    Return a source's versions in version-number order.
    """
    rows = connection.execute(
        """
        SELECT
            e.entity_id, e.entity_type, e.product_key, e.domain,
            e.status AS entity_status,
            e.version AS entity_version, e.created_at, e.updated_at,
            e.metadata_json AS entity_metadata_json,
            sv.source_id, sv.version_number, sv.content_hash,
            sv.original_path, sv.captured_at, sv.change_type,
            sv.metadata_json AS version_metadata_json
        FROM entities AS e
        JOIN source_versions AS sv
            ON sv.entity_id = e.entity_id
        WHERE sv.source_id = ?
        ORDER BY sv.version_number
        """,
        (source_id,),
    ).fetchall()
    return [source_version_from_row(row) for row in rows]


def find_matching_source_version(
    connection,
    source_id,
    *,
    content_hash,
    original_path,
    reprocessed_at,
):
    """
    Find an equivalent historical version-defining snapshot.
    """
    for version in list_source_versions(connection, source_id):
        if (
            version.content_hash == content_hash
            and version.original_path == original_path
            and version.version_metadata.get("reprocessed_at")
            == reprocessed_at
        ):
            return version
    return None


def next_source_version_number(connection, source_id):
    """
    Return the next sequential number for a source version.
    """
    row = connection.execute(
        """
        SELECT COALESCE(MAX(version_number), 0) + 1 AS next_number
        FROM source_versions
        WHERE source_id = ?
        """,
        (source_id,),
    ).fetchone()
    return row["next_number"]


def find_active_source_by_current_content_hash(
    connection,
    content_hash,
):
    """
    Find an active source by its current version's hash.
    """
    if not content_hash:
        return None

    row = connection.execute(
        """
        SELECT e.entity_id
        FROM entities AS e
        JOIN sources AS s ON s.entity_id = e.entity_id
        JOIN source_versions AS sv
            ON sv.entity_id = s.current_source_version_id
        WHERE e.status = 'active' AND sv.content_hash = ?
        ORDER BY e.entity_id
        LIMIT 1
        """,
        (content_hash,),
    ).fetchone()
    return get_source(
        connection,
        row["entity_id"],
    ) if row is not None else None
