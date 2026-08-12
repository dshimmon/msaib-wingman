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

## Authorization provenance boundary

The version-2 receipt records a trusted-local caller attestation that Maverick,
the sole authorizing principal, made the external decision. It binds the exact
action-specific manifest approval, evidence reference, bytes, target, code,
reviewed range, plan, command, expiry, operation, no-retry state, execution
route, and Codex executor. Direct Codex invocation and Mission Control dispatch
preserve the same asserted authorizing principal. A valid version-2 record can
identify Mission Control only as dispatcher, not as authorizing principal.

Receipt creation requires the exact generated approval text for the
content-addressed manifest plus an explicit caller attestation. The writer
checks internal consistency and scope, not the human origin of those inputs.
Authentication alone, missing evidence, an unknown principal or route, or
approval that does not cover the exact operation fails before a receipt is
written. Version-1 receipts retain their exact historical structure and
wording and remain readable; they are never migrated or re-rendered.

The receipt does not claim independent human authentication. A hostile process
already operating as the trusted local account could supply a false but
internally consistent attestation and reproduce the generated approval text;
stronger identity proof requires separately authorized identity
infrastructure.

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
