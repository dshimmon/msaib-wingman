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
  "authorization_gate": "BOOTSTRAP-003 disputed with explicit residual risk and BOOTSTRAP-004 corrected locally; focused re-audit receipt creation, transmission, and model invocation prohibited pending exact-package approval",
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
    }
  ],
  "baseline_commit": "b1910d0c69a52d73ddde93cb9722f12540c5d1e7",
  "implementation_commits": [
    "82c5952e64eb8fe5638701fef1f9d289b7735d82",
    "3e4edff5cc5e9b9810827331ca1024fd14c8f875",
    "1cddd1d65156d69053b30564c00343b3843cbe66",
    "0f7057896d2abfa9d04daa83e332f2015123c154",
    "2a868bac1088bd6523048623032af6d277143858",
    "f34c7ad810a50b36be453493d17fee8ac4c3ea00"
  ],
  "pushed": false,
  "merged": false,
  "official_decisions": [
    "docs/decisions/governance/roadmap-sequencing.md",
    "docs/decisions/governance/repository-records.md",
    "docs/decisions/governance/crew-chief-audit.md"
  ],
  "workstream": {
    "owner_session": "Codex BOOTSTRAP-003/004 finding correction authorized by Maverick on 2026-08-10",
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
    "state": "bootstrap_003_disputed_004_corrected_awaiting_focused_reaudit_approval",
    "next_gate": "Report the exact finding-focused package binding and obtain Maverick's explicit approval before receipt creation, transmission, or one finding-focused re-audit."
  },
  "next_gate": "Obtain Maverick's explicit approval for the exact compact finding-focused package before receipt creation, transmission, or model invocation; controlled Crew Chief fixture acceptance remains contingent on an accepted bootstrap disposition.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "healthy"
}
-->

Lifecycle: **active** and **portfolio-primary**. Call sign: **CREW-CHIEF**.

Maverick authorized Crew Chief v1 implementation, bounded enforcement and
closeout corrections, service-schema compatibility, the package-bound
bootstrap-governance correction, and the focused `BOOTSTRAP-003`/`004`
correction recorded above. The six earlier code-bearing commits are locally
committed at the exact hashes in `implementation_commits`. The single current
correction commit cannot embed its own final hash; the finding-focused package
must bind that final commit externally as its reviewed subject and exact diff.

Implemented, tested, locally committed, service-schema-corrected,
bootstrap-reviewed, acceptance-validated, Maverick-approved, published,
operational, and mission-complete are distinct states. The first completed
ordinary bootstrap returned `BLOCKED` with `BOOTSTRAP-001` and `002`. A later
ordinary bootstrap over evidence snapshot
`e88f25579e2c976c50e3abf49118abadb118f5b9` returned `FAIL` with
`BOOTSTRAP-003` and `004`, used 256,383 tokens, and was not a Crew Chief audit.
Both blocking results stopped conditional fixture acceptance, so zero Crew
Chief acceptance audits ran. `BOOTSTRAP-004` is corrected locally;
`BOOTSTRAP-003` is disputed within the approved v1 trust boundary with the
same-account impersonation risk escalated for Maverick's decision. Crew Chief
remains unapproved, unpublished, non-operational, and not mission-complete.

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
with chronological build notes in [`journal.md`](journal.md). The completed
first blocked review and dispositions are frozen under
[`artifacts/bootstrap-blocked-20260810/`](artifacts/bootstrap-blocked-20260810/).
The later `FAIL` report and complete external evidence remain preserved at
their reported hashes; the focused
[`disposition.json`](artifacts/bootstrap-failed-20260810/disposition.json)
artifact binds them.
No receipt exists for the finding-focused package because its final binding
has not been approved. The next gate is Maverick's approval of that exact
package before receipt creation or one focused re-audit. Conditional fixture
acceptance remains contingent on an accepted bootstrap disposition. Neither
review transfers Maverick's authority.
