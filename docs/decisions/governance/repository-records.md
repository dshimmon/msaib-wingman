# GOV-001 — Repository Records and Lifecycle

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "GOV-001",
  "title": "Repository Records and Lifecycle",
  "namespaces": ["governance"],
  "status": "accepted",
  "date": "2026-08-07",
  "authority": "Maverick",
  "scope": "Canonical homes, mission lifecycle, generated entry points, and status evidence",
  "approval_evidence": "governance/repository-architecture mission brief",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

`AGENTS.md` owns repository operating instructions. `docs/missions/` owns
mission authority and status. `docs/decisions/` owns enduring decisions.
`CURRENT_MISSION.md` and the mission/decision indexes are generated views, not
independent authorities. README provides product orientation and stable links.

Mission lifecycle is one of `draft`, `active`, `completed`, or `archived`.
Paused and cancelled state and capability health are separate fields. Multiple
missions may be active, but exactly one is portfolio-primary. Every secondary
active workstream must declare its owner/session, branch or worktree, writable
scope, state, and next gate.

Completed mission records are append-only in substance. Later corrections are
dated amendments. Approval, implementation, commit, push, merge, and mission
completion are recorded separately and must agree with Git evidence.

## Consequences

Generated views must be refreshed from authoritative metadata and validation
must fail when they are stale. Drafts, archives, architecture documentation,
and the Vault cannot claim current mission authority.
