# GOV-005 — Landing Signal Officer Closeout Workflow

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "GOV-005",
  "title": "Landing Signal Officer Closeout Workflow",
  "namespaces": ["governance", "operations"],
  "status": "accepted",
  "date": "2026-08-11",
  "authority": "Maverick",
  "scope": "Deterministic exact-package closeout preparation and separately authorized conditional commit, publication, record generation, remote verification, and completion reporting",
  "approval_evidence": "Maverick's August 11, 2026 instruction to build LSO v1 in an isolated worktree after selecting the LSO closeout design",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

Landing Signal Officer (LSO) is a deterministic closeout controller, not an
auditor, approver, Mission Control replacement, or live-execution agent. It
may prepare a closeout plan only from a schema-valid Crew Chief `PASS` with
zero findings, complete approval-ready reconciliation, passing bound
validation evidence, unchanged audited bytes, and an unchanged fast-forward
target.

LSO execution requires a later exact authorization text bound to one plan by
an unexpired single-use receipt. The receipt may authorize the named sequence
as one conditional gate: stage the exact audited paths, commit the
implementation, publish the implementation branch and fast-forward `main`,
generate and validate completion records, commit and publish those records,
verify both remote refs, and declare completion. Any drift, failure, missing
evidence, target movement, altered action list, consumed receipt, or expiry
stops the sequence. LSO never force-pushes, retries automatically, rewrites
history, rolls back shared state, or converts partial delivery into a success
claim.

Before real staging, LSO snapshots the exact worktree index. If staging or its
pre-commit verification fails, LSO atomically restores and verifies that exact
index before reporting `FAILED`. If restoration itself fails, LSO reports
`PARTIAL` and preserves both the original and recovery errors; it never claims
that the persistent staging mutation was safely reversed.

Receipt consumption is stored in a repository-identity-scoped directory under
the Git common directory rather than in the external plan package. Linked
worktrees therefore share one durable marker namespace, and copying a plan or
receipt cannot create a second authorized attempt.

## Authority boundary

Crew Chief remains the independent review role. LSO verifies its exact output
but does not repeat or overrule its judgment. Goose/Mission Control remains the
planning and evidence-advisory function. Maverick alone authorizes package
transmission, repository writes, publication, mission completion, and all live
operations.

Every new closeout receipt records Maverick as the authorizing principal,
binds a trusted-local caller attestation to the exact action-specific approval
text and nine-action scope, and separately records whether Codex was invoked
directly or dispatched through Mission Control. A valid version-2 record can
represent Mission Control only as dispatcher/orchestration route, never as the
authorizing principal. Authentication alone does not approve a closeout.

The version-2 writer requires explicit caller-attested authority provenance at
its trusted-local entry boundary and derives its human-readable statement from
those structured fields. It validates internal consistency, the exact approval
text and scope, and the permitted route/executor values; it does not verify the
human origin of its CLI inputs. Missing, unknown, non-Maverick, internally
inconsistent, or insufficient context fails before the receipt is written.
Version-1 receipts retain their exact historical representation and wording
and remain readable; they are not rewritten or re-rendered. Both versions are
tamper-evident after creation, not independent identity proof against a
malicious process already operating as the trusted local account. Stronger
identity infrastructure requires a separate decision.

## Completion meaning

LSO may return `COMPLETE` only after the exact implementation and generated
completion-record commits are both present on the authorized remote branch and
`main`, the repository is clean, and the canonical mission lifecycle is
`completed`. `FAILED` means no authorized action completed and any pre-commit
index mutation was restored exactly. `PARTIAL` means at least one action
completed before a later failure or a pre-commit index mutation could not be
restored exactly; it requires new diagnosis and new authorization, never an
automatic retry.

No LSO closeout receipt authorizes a deployment, database change, migration,
or other live operation unless a separate live-operation contract explicitly
exists and Maverick separately approves those exact bytes.
