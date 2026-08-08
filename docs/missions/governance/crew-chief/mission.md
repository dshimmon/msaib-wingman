# Crew Chief Independent Audit

<!-- wingman-mission-metadata
{
  "schema_version": 1,
  "id": "governance/crew-chief",
  "legacy_aliases": [],
  "title": "Crew Chief Independent Audit",
  "call_sign": "CREW-CHIEF",
  "namespace": "governance",
  "lifecycle": "active",
  "priority": "high",
  "portfolio_primary": true,
  "authorization_gate": "planning approved; implementation requires a separate Crew Chief build prompt",
  "approval_evidence": [
    {
      "date": "2026-08-08",
      "authority": "Maverick",
      "scope": "Approved governance/crew-chief as the successor portfolio-primary planning mission; implementation requires a separately authorized Crew Chief build prompt."
    }
  ],
  "baseline_commit": "cff8222fbe6092e0c145f7d8d7cabe8963cd66e6",
  "implementation_commits": [],
  "pushed": false,
  "merged": false,
  "official_decisions": [
    "docs/decisions/governance/roadmap-sequencing.md",
    "docs/decisions/governance/repository-records.md"
  ],
  "workstream": {
    "owner_session": "Unassigned; planning record only",
    "branch": "Not assigned; implementation not authorized",
    "worktree": "Not assigned; implementation not authorized",
    "writable_scope": [
      "docs/missions/governance/crew-chief/"
    ],
    "state": "planning_approved_implementation_not_authorized",
    "next_gate": "Execute a separately authorized Crew Chief implementation mission."
  },
  "next_gate": "Execute a separately authorized Crew Chief implementation mission.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "healthy"
}
-->

Lifecycle: **active** and **portfolio-primary**. Call sign: **CREW-CHIEF**.

Maverick approved Crew Chief on 2026-08-08 as the successor portfolio-primary
planning mission after completion of `governance/repository-architecture`.
This record authorizes planning only. Crew Chief is not implemented,
operational, or available to conduct an independent audit; implementation
requires a separate Crew Chief build prompt.

## Approved responsibility

The [Wingman Vault](../../../../WINGMAN_VAULT.md#crew-chief) defines Crew Chief
as the independent audit function in the mandatory review loop: receive the
Codex report and evidence, independently audit the authorized work, return
findings to Codex for resolution or evidence-backed dispute, and support a
final evidence package for Maverick. Findings begin as advisory, and Crew Chief
cannot expand scope, mutate repository state, authorize work, or overrule
Maverick.

## Authorization boundary

No Crew Chief agent configuration, tools, schemas, tests, controllers,
prompts, or runbooks are authorized by this planning record. The exact next
gate is to execute a separately authorized Crew Chief implementation mission.
