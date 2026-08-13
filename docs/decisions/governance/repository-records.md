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
  "scope": "Canonical homes, mission and task boundaries, concurrent work, generated entry points, and status evidence",
  "approval_evidence": "governance/repository-architecture mission brief and Maverick's 2026-08-12/13 CEO-COO-Quarterback operating decisions dispatched through Goose/Mission Control",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

`AGENTS.md` owns repository operating instructions and ordinary bounded-task
authority. `docs/missions/` owns strategic mission authority and status.
`docs/decisions/` owns enduring decisions. `CURRENT_MISSION.md` and the
mission/decision indexes are generated views, not independent authorities.
README provides product orientation and stable links.

Mission lifecycle is one of `draft`, `active`, `completed`, or `archived`.
Paused and cancelled state and capability health are separate fields. Multiple
missions may be active, and zero or one active mission may be
portfolio-primary; more than one is invalid. A completed or inactive mission
may retain historical `portfolio_primary` metadata without becoming the current
primary. Every active mission workstream recorded in mission metadata declares
its owner/session, branch or worktree, writable scope, state, and next gate.
That workstream rule applies to recorded mission workstreams, not to ordinary
bounded tasks operating without mission metadata under valid task authority.
Writable-scope overlap is not an automatic governance failure, and paused and
cancelled metadata are not mutually exclusive.

The original 2026-08-07 between-missions view used “implementation authority:
none” and made mission selection the next gate. The 2026-08-13 amendment below
supersedes that wording as an ordinary-work rule while preserving
`between missions` as strategic status.

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

## 2026-08-13 amendment — Bounded tasks and concurrent operations

A mission is a strategic objective; a task is a bounded unit of work. Multiple
missions and tasks may be active concurrently. A task does not require a new
mission record or a portfolio-primary designation unless its authority says
otherwise.

When no active portfolio-primary mission exists, the strategic repository
state remains `between missions`. That state does not deny ordinary
implementation permission: a valid bounded task under `AGENTS.md`, whether
issued through Goose/Mission Control or directly by Maverick, is sufficient to
proceed. `CURRENT_MISSION.md` is a compatibility and status view, not required
reading, implementation authority, a dispatch prerequisite, or a completion
gate.
