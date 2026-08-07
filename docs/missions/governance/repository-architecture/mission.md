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
  "authorization_gate": "publication_blocked_pending_antecedent_authority_and_independent_review",
  "approval_evidence": [
    {
      "date": "2026-08-07",
      "authority": "Maverick",
      "scope": "Mission brief authorizes implementation, testing, bounded commits, branch publication, and gated merge."
    }
  ],
  "baseline_commit": "c88a226ac13e69e235ed5df1347a3872e3330554",
  "implementation_commits": [
    "a26ca3a1cae1c6f7269c873127c06b8ee1454b8e",
    "1052f17c5627861091d9df87ee31141f7d440f46",
    "b2a61773335a20725e1d33a911e4133d4f01e29e",
    "99f0ef308cef30b42e4bb557c6e76e723aaff014"
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
    "state": "validated_pending_external_gates",
    "next_gate": "Maverick must disposition publication of the eight antecedent commits; then an approved fresh reviewer must complete the usability drill and independent read-only audit before push or merge."
  },
  "next_gate": "Maverick must disposition publication of the eight antecedent commits; then an approved fresh reviewer must complete the usability drill and independent read-only audit before push or merge.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "healthy"
}
-->

Lifecycle: **active** and **portfolio-primary**.

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
[`usability-drill.md`](usability-drill.md).
