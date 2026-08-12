# CC-0001 Authorization Provenance Correction

<!-- wingman-mission-metadata
{
  "schema_version": 1,
  "id": "governance/cc-0001-authorization-provenance",
  "legacy_aliases": [],
  "title": "CC-0001 Authorization Provenance Correction",
  "call_sign": "CC-0001",
  "namespace": "governance",
  "lifecycle": "active",
  "priority": "high",
  "portfolio_primary": true,
  "authorization_gate": "open for deterministic validation, fresh Crew Chief review, reconciliation, and LSO preparation under Maverick's 2026-08-11 instruction; LSO execution remains separately gated",
  "approval_evidence": [
    {
      "date": "2026-08-11",
      "authority": "Maverick",
      "scope": "Authorized the bounded CC-0001 governance and provenance correction: record Maverick as the sole authorizing principal, represent direct Codex and Mission Control only as execution or dispatch routes, preserve legacy receipt wording and representation, validate exact action scope, and fail safely without sufficient authority evidence."
    },
    {
      "date": "2026-08-11",
      "authority": "Maverick",
      "scope": "Approved the corrected candidate after a fresh independent Crew Chief PASS and authorized Codex to complete all preparatory steps needed to initiate LSO. This does not itself approve the exact LSO plan, staging, commits, publication, merge, shared-truth completion records, or mission completion."
    }
  ],
  "baseline_commit": "899370b6e3e6796acc2c1b04e4bdc9b13c58575e",
  "implementation_commits": [],
  "pushed": false,
  "merged": false,
  "official_decisions": [
    "docs/decisions/governance/crew-chief-audit.md",
    "docs/decisions/governance/lso-closeout.md"
  ],
  "workstream": {
    "owner_session": "Codex CC-0001 landing preparation authorized by Maverick on 2026-08-11",
    "branch": "codex/cc0001-landing-20260811",
    "worktree": "/Users/davidshimmon/.codex/worktrees/ebeb/msaib-wingman",
    "writable_scope": [
      "CURRENT_MISSION.md",
      "WINGMAN_VAULT.md",
      "docs/decisions/governance/crew-chief-audit.md",
      "docs/decisions/governance/lso-closeout.md",
      "docs/governance/mission-control-context.md",
      "docs/missions/README.md",
      "docs/missions/governance/cc-0001-authorization-provenance/mission.md",
      "docs/missions/governance/crew-chief/journal.md",
      "docs/missions/wingman-os/ledger-transition/architecture.md",
      "docs/missions/wingman-os/ledger-transition/decision.md",
      "docs/runbooks/crew-chief.md",
      "docs/runbooks/ledger-transition.md",
      "docs/runbooks/lso.md",
      "src/wingman/core/ledger/authorization.py",
      "src/wingman/core/ledger/schemas/authorization-receipt-v2.schema.json",
      "tests/governance/test_crew_chief.py",
      "tests/governance/test_lso.py",
      "tests/governance/test_repository_governance.py",
      "tests/wingman/test_ledger_transition.py",
      "tools/authorization.py",
      "tools/crew_chief/bootstrap_authorization.py",
      "tools/crew_chief/core.py",
      "tools/crew_chief/schemas/authorization-receipt-v2.schema.json",
      "tools/lso/__main__.py",
      "tools/lso/controller.py",
      "tools/lso/core.py",
      "tools/lso/schemas/authorization-receipt-v2.schema.json"
    ],
    "state": "closeout preparation",
    "next_gate": "Exact LSO plan approval by Maverick after required validation and a fresh zero-finding Crew Chief PASS."
  },
  "next_gate": "Exact LSO plan approval by Maverick after required validation and a fresh zero-finding Crew Chief PASS.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "healthy"
}
-->

Lifecycle: **active landing preparation**. Call sign: **CC-0001**.

## Objective

Land the already bounded authorization-provenance correction without expanding
it into a new identity or authentication system. New receipts record Maverick
as the sole authorizing principal, keep Mission Control and direct Codex as
execution routes, bind exact action-specific evidence and scope, and preserve
the exact historical version-1 representation.

## Authorized boundary

- Preserve the trusted-local caller-attestation model and disclose its
  residual same-account impersonation risk.
- Preserve exact version-1 schemas, receipts, and historical wording.
- Keep action-specific approval requirements for commits, merges, spending,
  publication, shared truth, and other reserved actions.
- Complete deterministic validation, a fresh package-bound Crew Chief audit,
  reconciliation, and non-mutating LSO preparation.
- Do not execute LSO, stage, commit, merge, push, publish, migrate, use live
  credentials, invoke a live service, or declare mission completion without
  Maverick's later approval of the exact LSO card.

## Closeout contract

The mission record itself is part of the final audited working-tree subject.
LSO may prepare an exact plan only after all required closeout checks pass, the
unchanged subject receives a fresh Crew Chief `PASS` with zero findings, and
the reconciliation is complete and approval-ready. Maverick must then approve
the complete plan-specific authorization text before any repository mutation.
