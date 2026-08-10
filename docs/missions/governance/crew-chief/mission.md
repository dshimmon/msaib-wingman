# Crew Chief Independent Audit

<!-- wingman-mission-metadata
{
  "schema_version": 1,
  "id": "governance/crew-chief",
  "legacy_aliases": [],
  "title": "Crew Chief Independent Audit",
  "call_sign": "CREW-CHIEF",
  "namespace": "governance",
  "lifecycle": "completed",
  "priority": "high",
  "portfolio_primary": true,
  "authorization_gate": "closed by Maverick with accepted limitations",
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
    },
    {
      "date": "2026-08-10",
      "authority": "Maverick",
      "scope": "Authorized one bounded bootstrap-governance correction: a package-bound authorization receipt control, preservation and reconciliation of the completed BLOCKED review, exactly two ordered local commits, deterministic validation, and preparation but not transmission of a new package; prohibited model invocation, fixture audit, push, merge, publication, main modification, and mission completion."
    },
    {
      "date": "2026-08-10",
      "authority": "Maverick",
      "scope": "Authorized one bounded correction commit for BOOTSTRAP-004, an evidence-backed BOOTSTRAP-003 scope dispute with explicit residual same-account risk, complete deterministic validation, and preparation but not transmission of one compact finding-focused re-audit package; prohibited new identity infrastructure, receipt creation, model invocation, fixture audit, push, merge, publication, main modification, and mission completion."
    },
    {
      "date": "2026-08-10",
      "authority": "Maverick",
      "scope": "Accepted the same-account authorization risk, authorized one finding-focused re-audit and two conditional fixture audits, and accepted the resulting FOCUSED-RUN-001 pre-service failure evidence."
    },
    {
      "date": "2026-08-10",
      "authority": "Maverick",
      "scope": "Authorized governance simplification, preservation of FOCUSED-RUN-001 evidence, completion of governance/crew-chief with the frozen-workspace launcher limitation and incomplete acceptance evidence stated honestly, and exactly one local closeout commit; prohibited push, merge, publication, main modification, model invocation, and successor activation."
    }
  ],
  "baseline_commit": "b1910d0c69a52d73ddde93cb9722f12540c5d1e7",
  "implementation_commits": [
    "82c5952e64eb8fe5638701fef1f9d289b7735d82",
    "3e4edff5cc5e9b9810827331ca1024fd14c8f875",
    "1cddd1d65156d69053b30564c00343b3843cbe66",
    "0f7057896d2abfa9d04daa83e332f2015123c154",
    "2a868bac1088bd6523048623032af6d277143858",
    "f34c7ad810a50b36be453493d17fee8ac4c3ea00",
    "6658076e8c9440665245793621edf1e309bedfdf"
  ],
  "pushed": false,
  "merged": false,
  "official_decisions": [
    "docs/decisions/governance/roadmap-sequencing.md",
    "docs/decisions/governance/repository-records.md",
    "docs/decisions/governance/crew-chief-audit.md"
  ],
  "workstream": {
    "owner_session": "Codex Crew Chief closeout authorized by Maverick on 2026-08-10",
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
    "state": "completed_by_maverick_with_accepted_limitations",
    "next_gate": "Maverick selects and authorizes a mission."
  },
  "next_gate": "Maverick selects and authorizes a mission.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "maintenance_pending"
}
-->

Lifecycle: **completed by Maverick with accepted limitations**. The retained
`portfolio_primary` value is historical metadata and does not make Crew Chief
the current primary. Call sign: **CREW-CHIEF**.

Crew Chief v1 is implemented at
`6658076e8c9440665245793621edf1e309bedfdf`, and the previously recorded
deterministic suites passed. The full ordinary bootstrap audit completed with
`FAIL`; it was not a Crew Chief audit. The later finding-focused re-audit did
not complete because the frozen external workspace was rejected before
service execution: the canonical command omitted `--skip-git-repo-check`.
The seeded-defect and corrected-fixture audits therefore did not run. Crew
Chief is not independently acceptance-certified or proven operational.

Maverick accepted the residual risk that a malicious process already operating
as the trusted local operating-system account could impersonate Maverick to the
authorization wrapper. Maverick also accepted the frozen-workspace launcher
limitation and completed the mission without claiming the failed or unexecuted
acceptance gates passed. No successor mission is active; the repository is
between missions, and Maverick selects and authorizes the next mission.

## Approved responsibility

The [Wingman Vault](../../../../WINGMAN_VAULT.md#crew-chief) defines Crew Chief
as a repository audit function: receive the Codex report and evidence, audit
the authorized work, return findings for resolution or evidence-backed
dispute, and support a final evidence package for Maverick. Self-review must be
labeled as self-review; independent review requires a separate reviewer.
Findings begin as advisory, and Crew Chief cannot expand scope, mutate
repository state, authorize work, or overrule Maverick.

## Implemented boundary

The approved implementation contains the project-scoped
[`crew-chief` agent](../../../../.codex/agents/crew-chief.toml), the
deterministic [`tools/crew_chief`](../../../../tools/crew_chief/) controller and
versioned schemas, the canonical [runbook](../../../runbooks/crew-chief.md),
and credential-free tests. [GOV-004](../../../decisions/governance/crew-chief-audit.md)
defines the enduring workflow and bootstrap boundary.

The exact evidence and validation record belongs in [`evidence.md`](evidence.md),
with chronological build notes in [`journal.md`](journal.md). The completed
first blocked review and dispositions are frozen under
[`artifacts/bootstrap-blocked-20260810/`](artifacts/bootstrap-blocked-20260810/).
The later `FAIL` report and historical evidence remain preserved at their
reported hashes; the focused
[`disposition.json`](artifacts/bootstrap-failed-20260810/disposition.json)
artifact binds them. The final failed focused-run evidence, authorization
receipt, invocation, run record, short stderr, and external evidence bindings
are preserved under
[`artifacts/focused-run-failed-20260810/`](artifacts/focused-run-failed-20260810/).
No structured focused report exists, no fixture audit ran, and neither review
transfers Maverick's authority.
