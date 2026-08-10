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
  "authorization_gate": "service-schema compatibility correction authorized locally; model invocation and package transmission prohibited pending new exact-package approval",
  "approval_evidence": [
    {
      "date": "2026-08-08",
      "authority": "Maverick",
      "scope": "Approved governance/crew-chief as the successor portfolio-primary planning mission; implementation requires a separately authorized Crew Chief build prompt."
    },
    {
      "date": "2026-08-09",
      "authority": "Maverick",
      "scope": "Authorized Crew Chief v1 implementation, credential-free validation, and exactly one local implementation commit; prohibited live model audit, push, merge, publication, operational declaration, and mission completion."
    },
    {
      "date": "2026-08-09",
      "authority": "Maverick",
      "scope": "Authorized one bounded Crew Chief correction and one local correction commit to enforce fail-closed feature handling, complete frozen source context, risk-profile coverage, and frozen citation binding; prohibited push, merge, publication, live Crew Chief execution, and mission completion."
    },
    {
      "date": "2026-08-09",
      "authority": "Maverick",
      "scope": "Authorized bounded Crew Chief closeout: acceptance-readiness corrections, canonical reconciliation, up to two fresh ordinary-Codex bootstrap attempts, exactly two controlled Crew Chief fixture acceptance invocations, in-scope finding correction, no more than six new local commits, and a final evidence package; prohibited push, merge, rebase, amend, tag, publication, credential exposure, and mission completion."
    },
    {
      "date": "2026-08-09",
      "authority": "Maverick",
      "scope": "Authorized one bounded local service-schema compatibility correction, deterministic validation, one local correction commit, closeout-record reconciliation, and preparation but not transmission of a newly frozen bootstrap package; prohibited model invocation, package transmission, push, merge, publication, main modification, and mission completion."
    }
  ],
  "baseline_commit": "b1910d0c69a52d73ddde93cb9722f12540c5d1e7",
  "implementation_commits": [
    "82c5952e64eb8fe5638701fef1f9d289b7735d82",
    "3e4edff5cc5e9b9810827331ca1024fd14c8f875",
    "1cddd1d65156d69053b30564c00343b3843cbe66",
    "0f7057896d2abfa9d04daa83e332f2015123c154"
  ],
  "pushed": false,
  "merged": false,
  "official_decisions": [
    "docs/decisions/governance/roadmap-sequencing.md",
    "docs/decisions/governance/repository-records.md",
    "docs/decisions/governance/crew-chief-audit.md"
  ],
  "workstream": {
    "owner_session": "Codex closeout session authorized by Maverick on 2026-08-09",
    "branch": "codex/crew-chief-v1-build-20260809",
    "worktree": "/Users/davidshimmon/.codex/worktrees/a83e/msaib-wingman",
    "writable_scope": [
      ".codex/agents/crew-chief.toml",
      ".github/workflows/governance.yml",
      "AGENTS.md",
      "CURRENT_MISSION.md",
      "WINGMAN_VAULT.md",
      "docs/README.md",
      "docs/decisions/README.md",
      "docs/decisions/governance/crew-chief-audit.md",
      "docs/decisions/governance/roadmap-sequencing.md",
      "docs/governance/mission-control-context.md",
      "docs/missions/README.md",
      "docs/missions/governance/crew-chief/",
      "docs/roadmap.md",
      "docs/runbooks/crew-chief.md",
      "tests/governance/test_crew_chief.py",
      "tests/governance/test_repository_governance.py",
      "tools/crew_chief/",
      "tools/governance/repository.py"
    ],
    "state": "service_schema_compatibility_corrected_awaiting_new_bootstrap_transmission_approval",
    "next_gate": "Obtain Maverick's explicit transmission approval for the newly frozen bootstrap package bound to the correction commit."
  },
  "next_gate": "Obtain Maverick's explicit approval for the exact newly frozen bootstrap package before any transmission or model invocation; controlled Crew Chief fixture acceptance remains contingent on a successful bootstrap review.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "healthy"
}
-->

Lifecycle: **active** and **portfolio-primary**. Call sign: **CREW-CHIEF**.

Maverick authorized Crew Chief v1 implementation, a bounded enforcement
correction, bounded closeout, and one service-schema compatibility correction
on 2026-08-09. The four pre-compatibility commits are locally committed at the
exact hashes recorded above. The current correction is limited to local
implementation, deterministic validation, one local commit, record
reconciliation, and preparation of a new frozen package. It does not authorize
transmission or a model invocation.

Implemented, tested, locally committed, service-schema-corrected,
bootstrap-reviewed, acceptance-validated, Maverick-approved, published,
operational, and mission-complete are distinct states. The authenticated
bootstrap attempt was rejected by the service's schema validation before model
generation. It completed no bootstrap review, produced no verdict, and
permitted no controlled Crew Chief acceptance audit. Zero bootstrap reviews
and zero Crew Chief acceptance audits have completed. Crew Chief is not
approved, published, operational, or mission-complete, and the lifecycle
remains active.

## Approved responsibility

The [Wingman Vault](../../../../WINGMAN_VAULT.md#crew-chief) defines Crew Chief
as the independent audit function in the mandatory review loop: receive the
Codex report and evidence, independently audit the authorized work, return
findings to Codex for resolution or evidence-backed dispute, and support a
final evidence package for Maverick. Findings begin as advisory, and Crew Chief
cannot expand scope, mutate repository state, authorize work, or overrule
Maverick.

## Implemented boundary

The approved implementation contains the project-scoped
[`crew-chief` agent](../../../../.codex/agents/crew-chief.toml), the
deterministic [`tools/crew_chief`](../../../../tools/crew_chief/) controller and
versioned schemas, the canonical [runbook](../../../runbooks/crew-chief.md),
and credential-free tests. [GOV-004](../../../decisions/governance/crew-chief-audit.md)
defines the enduring workflow and bootstrap boundary.

The exact evidence and validation record belongs in [`evidence.md`](evidence.md),
with chronological build notes in [`journal.md`](journal.md). The previous
767,450-byte package and its consent are obsolete because the correction
changes HEAD. The next gate is Maverick's explicit transmission approval for a
newly frozen package after its exact size, SHA-256, sensitive-content scan, and
binding evidence are reported. A later successful ordinary Codex bootstrap
review must operate read-only and state, “This bootstrap audit is not a Crew
Chief audit,” before the controlled fixture acceptance exercise can begin.
Neither review transfers Maverick's final authority.
