# Ledger Transition — Approved Implementation Brief

- **Canary:** `CANOPY-7C2F-ATLAS`
- **Authority:** Maverick
- **Authorization date:** August 10, 2026
- **Approved implementation baseline:**
  `b1910d0c69a52d73ddde93cb9722f12540c5d1e7`
- **Implementation state:** authorized engineering in an isolated worktree; live
  execution prohibited

## Objective

Replace the version-3 product-shaped `sources.program` and
`sources.academic_year` columns with a version-4 product-neutral physical
representation without changing public application behavior, unrelated
Ledger values, durable identity, version history, pointers, traceability, or
the exact path back to the pre-transition database.

Metadata keys are authoritative, including explicit null. Only a missing key
may inherit a corresponding non-null version-3 column. A conflicting legacy
value never overwrites metadata, and a missing key paired with a null legacy
column remains missing.

## Authorized engineering

- Implement Migration 4 and version-3/version-4 compatibility.
- Implement strict readiness, cooperative locks, multiprocess-safe
  initialization, exact-target authorization, immutable backup, crash-safe
  restoration, recovery, preservation validation, rollback, and disposable
  dry-run tooling.
- Use only synthetic fixtures, temporary databases, and credential-free
  offline validation.
- Update Ledger-specific mission, architecture, decision, runbook, and
  evidence records.
- Freeze an unstaged and uncommitted implementation for the Crew Chief gate.

## Explicit exclusions

- No operation against `data/**`, the default Ledger, or a live Ledger path.
- No live backup, migration, restore, rollback, postflight, authorization
  receipt, receipt consumption, model invocation, or package transmission.
- No staging, commit, push, merge, deployment, publication, or mission
  completion claim.
- No Flight Cards, Storage Port, PostgreSQL, Ledger Black Box, Contrail, Truth
  Clock, Product Contract, facade retirement, or unrelated persistence work.

## Acceptance gates

Engineering must prove readiness rejection, exact metadata semantics, byte and
storage-class preservation, full-connection shared locks, exclusive
maintenance, real multiprocess behavior, WAL/SHM quiescence, immutable backup,
crash recovery at each durable boundary, rollback, version-3/version-4
compatibility, existing behavior, governance, and the complete eligible suite.

Live execution remains separately gated on Assurance v1, all DATA-001
requirements, an exact reviewed package, a single-use receipt, Crew Chief
review, finding reconciliation, and Maverick's explicit live-transition
authorization.
