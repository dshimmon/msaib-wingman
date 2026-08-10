# OPS-001 — Development Flightline Operating Model

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "OPS-001",
  "title": "Development Flightline Operating Model",
  "namespaces": ["operations", "governance"],
  "status": "accepted",
  "date": "2026-08-01",
  "authority": "Maverick",
  "scope": "Isolated development-plane implementation and independent review",
  "approval_evidence": "Decisions B and D in the archived pre-Mission-028 planning package",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

One mutable Development Engineer works in one bounded isolated worktree. A
fresh, separate read-only Independent Auditor reviews frozen evidence.
Concurrency boundaries for additional engineers are selected for the task;
formally partitioned writable scopes and separate authorizations are not
universal requirements. Roles receive no default network, credentials, commit,
push, merge, or destructive authority.

The Development Flightline Independent Auditor is not Crew Chief. Flightline
setup delivery is historically completed at `ea9f3e0`; its capability health
is currently maintenance-pending while the protected foreground correction is
uncommitted.
