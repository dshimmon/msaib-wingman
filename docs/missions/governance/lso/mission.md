# Landing Signal Officer v1

<!-- wingman-mission-metadata
{
  "schema_version": 1,
  "id": "governance/lso",
  "legacy_aliases": [],
  "title": "Landing Signal Officer v1",
  "call_sign": "LSO",
  "namespace": "governance",
  "lifecycle": "completed",
  "priority": "high",
  "portfolio_primary": true,
  "authorization_gate": "closed by Maverick after exact LSO conditional closeout",
  "approval_evidence": [
    {
      "date": "2026-08-11",
      "authority": "Maverick",
      "scope": "Authorized construction of LSO v1 in an isolated worktree. Commit, push, merge, Crew Chief invocation, live Ledger work, publication, and mission completion were not authorized."
    },
    {
      "date": "2026-08-11",
      "authority": "Maverick",
      "scope": "Approved the exact LSO closeout plan, including implementation commit, branch and main publication, completion-record generation, closeout commit, remote verification, and completion declaration; no live operation authorized."
    }
  ],
  "baseline_commit": "9c68ca8ef10a270358c510d1a333daf001d7caa1",
  "implementation_commits": [
    "6c3d1e094a84d3615cd2ab542520bf7e11ca2c06"
  ],
  "pushed": true,
  "merged": true,
  "official_decisions": [
    "docs/decisions/governance/crew-chief-audit.md",
    "docs/decisions/governance/lso-closeout.md",
    "docs/decisions/governance/repository-records.md"
  ],
  "workstream": {
    "owner_session": "Wingman Mission Control LSO v1 build authorized by Maverick on 2026-08-11",
    "branch": "codex/lso-v1-20260811",
    "worktree": "/private/tmp/wingman-lso-v1-20260811-9c68ca8",
    "writable_scope": [
      ".github/workflows/governance.yml",
      "CURRENT_MISSION.md",
      "WINGMAN_VAULT.md",
      "docs/README.md",
      "docs/decisions/README.md",
      "docs/decisions/governance/lso-closeout.md",
      "docs/governance/mission-control-context.md",
      "docs/missions/README.md",
      "docs/missions/governance/lso/",
      "docs/roadmap.md",
      "docs/runbooks/lso.md",
      "tests/governance/test_lso.py",
      "tests/governance/test_repository_governance.py",
      "tools/governance/repository.py",
      "tools/lso/"
    ],
    "state": "completed",
    "next_gate": "Maverick selects and authorizes the next mission."
  },
  "next_gate": "Maverick selects and authorizes the next mission.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "healthy"
}
-->

Lifecycle: **active implementation**. Call sign: **LSO**.

LSO is Wingman's deterministic closeout controller. Crew Chief decides whether
the frozen engineering evidence passes review; LSO verifies that result and
the unchanged subject, prepares the exact approval card, and executes only the
actions named in a later single-use Maverick authorization receipt.

The approved scope and exclusions are in [`approved-brief.md`](approved-brief.md).
Build and validation evidence belongs in [`evidence.md`](evidence.md). The
operator procedure is [`docs/runbooks/lso.md`](../../../runbooks/lso.md), and
[GOV-005](../../../decisions/governance/lso-closeout.md) owns the enduring
authority and failure-boundary decision.

No real repository closeout and no live operation is authorized by this active
mission record.
