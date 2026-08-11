# Wingman Ledger Transition

<!-- wingman-mission-metadata
{
  "schema_version": 1,
  "id": "wingman-os/ledger-transition",
  "legacy_aliases": [],
  "title": "Wingman Ledger Transition",
  "call_sign": "LEDGER-TRANSITION",
  "namespace": "wingman-os",
  "lifecycle": "completed",
  "priority": "high",
  "portfolio_primary": false,
  "authorization_gate": "closed for transition-machinery implementation and GitHub publication; physical Ledger transition remains separately gated",
  "approval_evidence": [
    {
      "date": "2026-08-10",
      "authority": "Maverick",
      "scope": "Authorized bounded Ledger Transition engineering in an isolated worktree, including Migration 4, compatibility, locking, initialization, exact-target authorization, backup, restoration, recovery, preservation, rollback, dry-run tooling, validation, and a mandatory Crew Chief review; prohibited live/default Ledger access, commit, publication, and mission completion."
    },
    {
      "date": "2026-08-10",
      "authority": "Maverick",
      "scope": "Authorized one read-only, no-retry Crew Chief invocation for the exact initial audit package and later one read-only, no-retry follow-up invocation for the exact corrected package."
    },
    {
      "date": "2026-08-11",
      "authority": "Maverick",
      "scope": "Authorized hunk-preserving integration of the audited Ledger candidate, then authorized commit and push to main after review of the exact staged evidence."
    },
    {
      "date": "2026-08-11",
      "authority": "Maverick",
      "scope": "Authorized one documentation/governance-only reconciliation commit covering the remaining Ledger Transition record gaps, explicitly excluding CURRENT_MISSION.md; no live Ledger operation or runtime change authorized."
    },
    {
      "date": "2026-08-11",
      "authority": "Maverick",
      "scope": "Approved the completed Ledger Transition implementation mission record and authorized gap-only reconciliation onto canonical main 196a1804d51992259018281286f5571db2b4d556, generated-governance correction, commit, push, merge, and GitHub-main publication; explicitly prohibited any physical or live Ledger operation."
    }
  ],
  "baseline_commit": "b1910d0c69a52d73ddde93cb9722f12540c5d1e7",
  "implementation_commits": [
    "51fb750d2364a4e137ba7e42963a11b10fe4cdc0"
  ],
  "pushed": true,
  "merged": true,
  "official_decisions": [
    "docs/decisions/architecture/airframe-boundaries.md",
    "docs/decisions/governance/crew-chief-audit.md",
    "docs/decisions/security/ledger-and-data-safety.md"
  ],
  "next_gate": "Physical Migration 4 requires Assurance v1, every DATA-001 prerequisite, exact live-target identification, a disposable rehearsal, an immutable backup destination, frozen manifest and package bytes, fresh Crew Chief review, a single-use receipt, and Maverick approval of that exact package.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "healthy"
}
-->

Lifecycle: **completed for transition-machinery implementation and GitHub
publication**. Call sign: **LEDGER-TRANSITION**.

## Delivered engineering boundary

The Wingman OS Ledger now contains a product-neutral Migration 4 and governed
transition machinery for exact-target authorization, lifetime application
locking, concurrent initialization, WAL/SHM-safe quiescence, immutable
backups and checksums, crash-safe restoration, schema readiness, semantic and
byte preservation, disposable rehearsals, rollback, and postflight
verification.

Fresh empty databases initialize at version 4. Existing version-3 databases
remain readable and writable through the compatibility adapter and do not
advance automatically. Atlas behavior remains compatible, while the
transition mechanisms belong to product-neutral Wingman Core.

## Audit and publication

Crew Chief's initial review returned `FAIL` with one blocking medium finding,
`CC-0001`, concerning shared-to-exclusive lock conversion. The implementation
removed lock conversion, required maintenance connections to acquire exclusive
ownership from creation, and added a two-process lifetime-lock regression.
The exact follow-up review returned `PASS` with zero findings; reconciliation
was complete and approval-ready.

The earlier follow-up audit and its four committed artifacts remain preserved
as development history. Maverick later authorized the decisive corrected-base
follow-up: audit
`4b2951304f67667fdb654a707caa75292f78a4e429c4ad4a4f60db514fef4669`,
envelope
`33398f0c7c08aef8eed909ca7914f84f2efab05c2ed2eba19c5399d414dd1b33`.
It returned `PASS` with zero findings; reconciliation was complete and
`approval_ready=true`. Its report hash is
`3b2a8320fa38d548495a09d9b563904f8fe99795ef39f08991e9a4b3c38606d3`
and package hash is
`01b49942772375aa93a285a5ce07adf895913c963f92c0bb72f1a97f57b67f58`.

The immutable report records `generated_at` as
`2026-08-11T12:00:00-03:00`, while the controller records `completed_at` as
`2026-08-11T03:50:48Z` and reconciliation records `generated_at` as
`2026-08-11T03:51:28Z`. This is a model-authored timestamp metadata defect,
not a Ledger finding or an indication of artifact tampering; the immutable
source artifacts were not rewritten.

The 31-file implementation was committed as
`51fb750d2364a4e137ba7e42963a11b10fe4cdc0`, integrated through
`f4dd327cad0be5da8bead4df633d7308a1ec80fb`, and published on `main`.
The audited staged patch identity was preserved at SHA-256
`a4e0f0af65de8413c2e659dfe0167a047efe6bee3b182d01ddcd0df252b4a7c3`.
The detailed build, validation, audit, and publication record is in
[`evidence.md`](evidence.md); the operator procedure is the
[Ledger Transition runbook](../../../runbooks/ledger-transition.md).
The historical, noncanonical implementation journal is archived at
[`docs/archive/mission-history/wingman-os/ledger-transition/journal.md`](../../../archive/mission-history/wingman-os/ledger-transition/journal.md).

## Operational boundary

No default or live Ledger, `data/**`, credential, live receipt, backup,
migration, restoration, recovery, or rollback was touched. Shipping the
mechanism does not authorize running it. Live execution remains fail-closed
behind Assurance v1, DATA-001, an exact reviewed target package, a single-use
receipt, fresh Crew Chief review, and Maverick's explicit authorization.
