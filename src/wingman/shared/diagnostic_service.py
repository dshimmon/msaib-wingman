"""Application-facing diagnostic persistence with safe logging fallback."""

import logging
import uuid

from wingman.core.ledger.database import transaction
from wingman.core.ledger.diagnostic_repository import create_diagnostic_event
from wingman.core.ledger.models import serialize_json
from wingman.shared.source_registry import open_registry_database


LOGGER = logging.getLogger(__name__)


def new_trace_id():
    """Create a collision-resistant trace identity."""
    return f"trace_{uuid.uuid4()}"


def record_diagnostic(
    *,
    operation,
    severity,
    recoverable,
    message,
    trace_id=None,
    related_entity_id=None,
    details=None,
):
    """Persist one event, falling back to standard logging on failure."""
    trace_id = trace_id or new_trace_id()
    details = details if details is not None else {}
    connection = None
    try:
        serialize_json(details, "details", dict)
        connection = open_registry_database()
        with transaction(connection):
            return create_diagnostic_event(
                connection,
                entity_id=f"diagnostic_{uuid.uuid4()}",
                trace_id=trace_id,
                operation=operation,
                severity=severity,
                recoverable=recoverable,
                related_entity_id=related_entity_id,
                message=message,
                details=details,
            )
    except Exception:
        LOGGER.exception(
            "Ledger diagnostic persistence failed "
            "(trace_id=%s, operation=%s)",
            trace_id,
            operation,
        )
        return None
    finally:
        if connection is not None:
            connection.close()
