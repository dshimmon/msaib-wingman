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
missions may be active, and zero or one active mission may be
portfolio-primary; more than one is invalid. A completed or inactive mission
may retain historical `portfolio_primary` metadata without becoming the current
primary. Every active workstream declares its owner/session, branch or
worktree, writable scope, state, and next gate. Writable-scope overlap is not
an automatic governance failure, and paused and cancelled metadata are not
mutually exclusive.

When no active portfolio-primary mission exists, the repository is explicitly
between missions: portfolio primary is none, implementation authority is none,
and the next gate is Maverick's selection and authorization of a mission.

Completed mission records preserve their historical evidence. Later
corrections are dated amendments. Structured approval, implementation, commit,
push, merge, and lifecycle metadata remains available for compatibility and
must agree with Git evidence where applicable, but reports need only describe
the states material to the task.

## Consequences

Generated views must be refreshed from authoritative metadata and validation
must fail when they are stale. Journals and other documents may summarize
current status. If a summary conflicts with mission metadata, the mission
record controls. Empty canonical documents and unresolved internal
documentation links are maintenance concerns rather than governance failures;
repository-link root confinement remains enforced.
