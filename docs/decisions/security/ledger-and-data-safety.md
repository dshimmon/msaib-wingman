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

The Wingman Ledger remains at migration versions 1–3. No ordinary repository,
product-contract, or packaging mission authorizes a physical schema migration
or live-data mutation.

A later transition requires exact-target authorization, cooperative and
exclusive locking, multiprocess initialization control, WAL/SHM-safe
quiescence and backup identity, immutable backups and checksums, crash-safe
restoration, readiness checks, semantic and byte-preservation validation,
disposable dry runs, tested rollback, Assurance v1, Crew Chief prerequisites,
and a separate Maverick live-execution gate.
