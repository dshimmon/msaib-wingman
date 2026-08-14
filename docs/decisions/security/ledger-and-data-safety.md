# DATA-001 — Ledger and Data Safety Boundary

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "DATA-001",
  "title": "Ledger and Data Safety Boundary",
  "namespaces": ["wingman-os", "security", "data"],
  "status": "accepted",
  "date": "2026-08-01",
  "authority": "Maverick",
  "scope": "Ledger migration sequence, live-data gates, and deferred safety obligations",
  "approval_evidence": "WINGMAN_VAULT.md and wingman-os/airframe mission record",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

The default/live Wingman Ledger remains at schema version 3 until an exact
governed operation is separately approved. No ordinary repository,
product-contract, packaging, or implementation mission authorizes a physical
schema migration or live-data mutation.

Migration 4 and the supporting exact-target authorization, cooperative and
exclusive locking, multiprocess initialization control, WAL/SHM-safe
quiescence and backup identity, immutable backup, crash-safe restoration,
readiness, preservation, dry-run, rollback, and postflight mechanisms were
implemented and published at
`51fb750d2364a4e137ba7e42963a11b10fe4cdc0`. Fresh empty databases may
initialize at version 4; existing version-3 databases do not advance
automatically. Shipping those controls does not satisfy or bypass this live
safety boundary.

A live transition still requires Assurance v1, every target-specific DATA-001
check, a fresh exact target and code package, an immutable backup destination,
a single-use no-retry receipt bound to Maverick's approval, disposable dry-run
evidence, independent review and reconciliation of the exact package under
GOV-006, explicit rollback and recovery readiness, and Maverick's separate
live-execution authorization. Any changed target, code, schema, inventory, checksum, command,
expiry, or operation invalidates the package.
