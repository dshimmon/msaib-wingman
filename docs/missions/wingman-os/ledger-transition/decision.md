# Ledger Transition Implementation Decision

This bounded implementation decision does not itself own lifecycle. The
adjacent canonical [`mission.md`](mission.md) records the completed engineering
mission, publication, and next-gate status; Maverick's explicit approvals own
every implementation and operational authorization.

- **Date:** August 10, 2026
- **Authority:** Maverick
- **Status:** implemented, audited, merged, published, and closed as an
  engineering mission; live execution is not authorized by this decision

## Decision

Add an explicit Migration 4 that removes the two historical product-shaped
source columns while preserving version-3 behavior throughout a governed
rollback window. Existing version-3 databases require an exact, separately
authorized transition; fresh databases may initialize directly at version 4.

The transition is an operational system, not merely a SQL migration. Exact
target identity, released-schema readiness, complete cooperative locking,
WAL-safe backup, single-use authorization, crash-safe restoration, semantic
and byte preservation, disposable rehearsal, and tested rollback are required
parts of the implementation.

## Authorization trust boundary

The version-1 receipt records Maverick's exact manifest approval and binds its
bytes, target, code, reviewed range, plan, command, expiry, operation, and
no-retry state. Its external trust boundary is the authenticated Mission
Control interaction plus the trusted local operating-system account. It does
not claim independent human authentication. A hostile process already
operating as that same account could impersonate the local approval wrapper;
stronger identity proof requires separately authorized identity infrastructure.

## Consequences

- Historical compatibility facades remain thin and unchanged.
- Version 3 remains readable and writable through the private adapter.
- Version 4 stores product-owned values only as opaque metadata.
- A consumed operation is never automatically retried. Recovery continues or
  restores from the durable journal and immutable backup.
- Backup files, failed databases, completed journals, and evidence manifests
  are non-overwriting preserved evidence.
- Assurance v1, DATA-001, Crew Chief review, and a separate Maverick live gate
  remain mandatory before any live execution.
- The implementation is published at
  `51fb750d2364a4e137ba7e42963a11b10fe4cdc0`; this publication changes no
  live/default Ledger and does not transfer its audit to a future exact-target
  execution package.
