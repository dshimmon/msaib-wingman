# GOV-004 — Crew Chief Independent Audit Workflow

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "GOV-004",
  "title": "Crew Chief Independent Audit Workflow",
  "namespaces": ["governance", "operations"],
  "status": "accepted",
  "date": "2026-08-09",
  "authority": "Maverick",
  "scope": "Repository-scoped Crew Chief v1 audit envelopes, fresh read-only review, structured findings, and finding-by-finding reconciliation",
  "approval_evidence": "Maverick's 2026-08-09 CANOPY-7C2F-ATLAS Crew Chief implementation and single-local-commit authorization",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

Crew Chief is Wingman's repository-scoped independent audit role for the
governed Codex review loop. Codex freezes an approved mission, exact Git
subject, engineer report, test claims, and evidence into a deterministic,
expiring audit envelope. A fresh read-only reviewer produces canonical JSON
findings. Codex then resolves, disputes with exact counter-evidence, or
escalates every finding before delivering a validated decision package to
Goose and Maverick.

The project-scoped model-facing role has one canonical definition:
[`crew-chief.toml`](../../../.codex/agents/crew-chief.toml). The deterministic
controller and stable JSON Schemas live under
[`tools/crew_chief/`](../../../tools/crew_chief/). The operational procedure
is the canonical [Crew Chief runbook](../../runbooks/crew-chief.md).

Crew Chief is advisory and cannot mutate the repository, approve a lifecycle
gate, expand scope, impersonate Goose or the Development Flightline Auditor,
or certify its own implementation. The v1 controller uses external,
single-workspace consumption markers rather than a global audit database.
Model audits occur only at an explicitly governed handoff and never in CI.

## Bootstrap boundary

The initial implementation cannot be self-certified. Its local implementation
commit must be handed to a fresh ordinary Codex reviewer operating read-only
and stating, “This bootstrap audit is not a Crew Chief audit.” Only a later,
separately authorized controlled acceptance run may establish that the Crew
Chief selection and execution path operates as designed.

This decision does not publish the implementation, make Crew Chief
operational, complete the mission, or authorize a live model audit.
