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
  "authorization_gate": "previous_independent_audit_failed_corrections_committed_fresh_audit_and_antecedent_disposition_required",
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
    }
  ],
  "baseline_commit": "c88a226ac13e69e235ed5df1347a3872e3330554",
  "implementation_commits": [
    "a26ca3a1cae1c6f7269c873127c06b8ee1454b8e",
    "1052f17c5627861091d9df87ee31141f7d440f46",
    "b2a61773335a20725e1d33a911e4133d4f01e29e",
    "99f0ef308cef30b42e4bb557c6e76e723aaff014",
    "60134f7c6ea9b5fa6de2756bbe8424e94445bb03",
    "0bc7be1e88d5a7c70d4485d49264c02fc8d95b81"
  ],
  "pushed": false,
  "merged": false,
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
    "state": "corrections_locally_committed_awaiting_fresh_independent_audit",
    "next_gate": "A fresh independent read-only audit must pass on the correction commits; publication remains separately blocked until Maverick dispositions the eight antecedent commits."
  },
  "next_gate": "A fresh independent read-only audit must pass on the correction commits; publication remains separately blocked until Maverick dispositions the eight antecedent commits.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "healthy"
}
-->

Lifecycle: **active** and **portfolio-primary**.

The previous independent repository-organization audit failed. Its bounded
corrections are locally committed and await a fresh independent read-only
audit. Publication remains a separate blocked gate pending Maverick's
disposition of the eight antecedent commits.

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
