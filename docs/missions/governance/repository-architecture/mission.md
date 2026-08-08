# Wingman Repository Architecture

<!-- wingman-mission-metadata
{
  "schema_version": 1,
  "id": "governance/repository-architecture",
  "legacy_aliases": [],
  "title": "Wingman Repository Architecture",
  "call_sign": null,
  "namespace": "governance",
  "lifecycle": "active",
  "priority": "high",
  "portfolio_primary": true,
  "authorization_gate": "published_to_main_awaiting_maverick_mission_completion_declaration",
  "approval_evidence": [
    {
      "date": "2026-08-07",
      "authority": "Maverick",
      "scope": "Mission brief authorizes implementation, testing, bounded commits, branch publication, and gated merge."
    },
    {
      "date": "2026-08-07",
      "authority": "Maverick",
      "scope": "Correction brief authorizes bounded local audit corrections, nondestructive tests, and exactly three local commits; push and merge are prohibited."
    },
    {
      "date": "2026-08-07",
      "authority": "Maverick",
      "scope": "Follow-up evidence-correction brief authorizes corrected foreground rename lineage, strengthened automated proof, validation, and exactly one additional local commit; push and merge are prohibited."
    },
    {
      "date": "2026-08-08",
      "authority": "Maverick",
      "scope": "Credential-free offline-suite correction authorizes bounded implementation, testing, mission evidence updates, and generated-record refresh; commit, push, and merge are prohibited."
    },
    {
      "date": "2026-08-08",
      "authority": "Maverick",
      "scope": "Credential-free offline-suite correction authorizes exactly one local commit with subject 'Make offline test suite credential-free'; push, merge, amend, rebase, fetch, and unrelated changes remain prohibited."
    },
    {
      "date": "2026-08-08",
      "authority": "Maverick",
      "scope": "Approved publication of all eight antecedent commits and the independently audited repository-architecture history to main, including exactly one bounded closeout commit."
    }
  ],
  "baseline_commit": "c88a226ac13e69e235ed5df1347a3872e3330554",
  "implementation_commits": [
    "a26ca3a1cae1c6f7269c873127c06b8ee1454b8e",
    "1052f17c5627861091d9df87ee31141f7d440f46",
    "b2a61773335a20725e1d33a911e4133d4f01e29e",
    "99f0ef308cef30b42e4bb557c6e76e723aaff014",
    "bf73134d85b1fde9ffab1c6f0eddc07aabaead22",
    "60134f7c6ea9b5fa6de2756bbe8424e94445bb03",
    "0bc7be1e88d5a7c70d4485d49264c02fc8d95b81",
    "ea774b088f2886d2b34b79d8a177b95f326616b9",
    "1250e8c070c3b3f17644adf3bac1fcb381702c0c",
    "99accba8b3433b6f9485881f4033f507bd6ae3ef",
    "6661712ca325d9fd47a9cf436fd3b11e04c53b62"
  ],
  "pushed": true,
  "merged": true,
  "official_decisions": [
    "docs/decisions/governance/repository-records.md",
    "docs/decisions/architecture/airframe-boundaries.md",
    "docs/decisions/architecture/product-separation.md",
    "docs/decisions/architecture/source-traceability.md"
  ],
  "workstream": {
    "owner_session": "Codex /root",
    "branch": "codex/governance-repository-architecture",
    "worktree": "/private/tmp/wingman-repository-architecture-20260807-01",
    "writable_scope": [
      "/private/tmp/wingman-repository-architecture-20260807-01"
    ],
    "state": "published_to_main_awaiting_maverick_mission_completion_declaration",
    "next_gate": "Maverick must decide whether to declare governance/repository-architecture complete and select or authorize the next portfolio-primary mission; no further implementation is authorized."
  },
  "next_gate": "Maverick must decide whether to declare governance/repository-architecture complete and select or authorize the next portfolio-primary mission; no further implementation is authorized.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "healthy"
}
-->

Lifecycle: **active** and **portfolio-primary**.

The fresh independent read-only audit passed the complete repository-
architecture state at credential-free correction commit `6661712`. Maverick
then approved all eight antecedent commits and authorized publication of the
audited history to `main`, including one bounded closeout commit. Every listed
implementation and correction commit through `6661712` is published and
contained by `origin/main`. The mission remains active until Maverick
separately declares it complete and selects or authorizes the next portfolio-
primary mission; no further implementation is authorized by this closeout.

## Objective

Create an unambiguous repository organization for Wingman OS, Atlas, Radar,
and concurrent governed workstreams while preserving behavior, traceability,
compatibility surfaces, and the protected foreground checkout.

## Scope and exclusions

The approved mission covers governance records, documentation classification,
physical source/test separation, compatibility facades, automated enforcement,
validation, bounded commits, and gated publication/merge. It excludes Ledger
migration, live-data mutation, Product Contract version changes, Radar behavior,
plugin infrastructure, broad capability work, and unrelated refactoring.

## Acceptance and evidence

The authorized baseline is `c88a226`. The isolated clean baseline measured on
2026-08-07 is 271 passing offline tests. Work-package and final evidence belongs
in [`evidence.md`](evidence.md); chronological implementation notes are in
[`journal.md`](journal.md). The fresh-context handoff is defined in
[`usability-drill.md`](usability-drill.md). Foreground exclusion is recorded in
the machine-readable
[`foreground-preservation-manifest.json`](artifacts/foreground-preservation-manifest.json).
