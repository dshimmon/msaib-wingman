<!-- wingman-archive-metadata
{
  "schema_version": 1,
  "classification": "historical_noncanonical",
  "canonical_replacement": "docs/missions/wingman-os/ledger-transition/mission.md",
  "archived_from": "docs/missions/wingman-os/ledger-transition/journal.md"
}
-->

> [!WARNING]
> **HISTORICAL / NONCANONICAL MISSION EVIDENCE.** The sole canonical
> lifecycle, publication, and next-gate record is
> [`docs/missions/wingman-os/ledger-transition/mission.md`](../../../../missions/wingman-os/ledger-transition/mission.md).
> This journal preserves the implementation sequence and does not authorize a
> physical or live Ledger transition.

# Ledger Transition Historical Journal

**Call sign:** LEDGER-TRANSITION
**Implementation baseline:** `b1910d0c69a52d73ddde93cb9722f12540c5d1e7`
**Final status:** Transition machinery completed, independently audited,
committed, merged, and published; live Ledger remains version 3

## Objective and exclusions

Maverick authorized a product-neutral physical representation for Ledger
sources while preserving application behavior, durable identity, traceability,
rollback, and an exact route to the pre-transition state. Migration 4 removes
the version-3 `sources.program` and `sources.academic_year` columns. Existing
metadata keys remain authoritative, including explicit null; only absent keys
may inherit corresponding non-null legacy values.

Engineering was restricted to isolated worktrees, synthetic fixtures,
temporary databases, and credential-free offline validation. The default/live
Ledger, `data/**`, credentials, live receipts, live backup, physical migration,
restoration, recovery, rollback, deployment, and unrelated product or storage
work were excluded.

## Engineering sequence

The implementation added:

- explicit Migration 4 with immutable migrations 1–3;
- version-3 and version-4 adapter support across the rollback window;
- strict migration-history, schema-fingerprint, metadata, integrity, and
  foreign-key readiness;
- lifetime shared locks and exclusive maintenance locks;
- bounded, double-checked multiprocess initialization;
- exact-target, versioned, single-use authorization controls;
- WAL checkpoint/truncation and DB/WAL/SHM quiescence binding;
- immutable, non-overwriting backup and manifest creation;
- durably journaled crash-safe restoration and recovery;
- semantic, storage-class, and byte-preservation comparison; and
- genuinely disposable clone-only rehearsal tooling.

Development exposed and corrected path canonicalization, initialization lock
ordering, WAL/SHM inventory, concurrent initialization, rollback-fixture,
post-commit recovery, and lock-conversion defects. The complete failed-attempt
and exact-rerun history remains in the canonical
[`evidence.md`](../../../../missions/wingman-os/ledger-transition/evidence.md).

## Shared-file coordination

Ledger overlapped Flight Cards and Course Cockpit only in shared files whose
hunks and contracts were separate. Maverick approved hunk-level coordination.
The final integration preserved Ledger's Core ownership registrations and
version-3 fixture setup alongside the product tasks' distinct UI registrations
and assertions. No product-owned implementation was absorbed into Ledger.

## Crew Chief sequence

The first full implementation audit found `CC-0001`: a failed BSD `flock`
shared-to-exclusive conversion could lose the caller's shared lock. Codex
accepted the finding, removed lock upgrade, required exclusive maintenance
connections from creation, and added a real multiprocess regression.

An earlier corrected follow-up audit
`6396de29749f52ea9cd4b95b03f75bc35894c9dc1d520809c49633b61492d46c`
returned `PASS`; its four report and reconciliation artifacts remain committed
as immutable history. Maverick subsequently superseded the original no-staging
clause for the exact candidate and authorized the decisive final follow-up:

- payload SHA-256
  `f30e90367f32e7d42c6bb92eacc0c3a70841b2372e5265dd7ee5c184c4632251`
  at 803,178 bytes;
- audit ID
  `4b2951304f67667fdb654a707caa75292f78a4e429c4ad4a4f60db514fef4669`;
- envelope ID
  `33398f0c7c08aef8eed909ca7914f84f2efab05c2ed2eba19c5399d414dd1b33`;
- report hash
  `3b2a8320fa38d548495a09d9b563904f8fe99795ef39f08991e9a4b3c38606d3`;
- package hash
  `01b49942772375aa93a285a5ce07adf895913c963f92c0bb72f1a97f57b67f58`;
- verdict `PASS`, zero findings; and
- complete reconciliation with `approval_ready=true`.

The immutable report records `generated_at` as
`2026-08-11T12:00:00-03:00`, the controller records completion at
`2026-08-11T03:50:48Z`, and reconciliation records generation at
`2026-08-11T03:51:28Z`. This is a model-authored timestamp metadata
inconsistency. It is not a Ledger finding and does not indicate artifact
tampering; the source files were not rewritten.

## Validation and publication

The corrected-base candidate passed 25/25 transition-safety tests, 146/146
focused compatibility and governance tests, and 453/453 complete
credential-free offline repository tests before publication.

The 31-file implementation was committed as
`51fb750d2364a4e137ba7e42963a11b10fe4cdc0`. It was integrated with current
Atlas work at `f4dd327cad0be5da8bead4df633d7308a1ec80fb`; the combined tree then
passed 25/25 safety tests, 146/146 focused tests, and 473/473 complete
repository tests. Both the Ledger branch and GitHub main were published under
Maverick's authorization. Atlas then completed without changing a Ledger-owned
implementation or transition-documentation path.

Canonical record reconciliation was first published as
`196a1804d51992259018281286f5571db2b4d556`. Maverick treated that concurrent
commit as canonical, preserved its four audit artifacts and valid status
corrections, and authorized only the remaining lifecycle, final-audit,
historical-journal, generated-view, and ordering gaps to be closed afterward.

That gap-only closeout passed 25/25 transition-safety tests in 9.526 seconds,
33/33 repository-governance tests in 10.026 seconds, and 474/474 complete
credential-free offline repository tests in 198.179 seconds. Standalone
governance, 20 JSON Schemas, 226 in-memory Python compilations, changed-hunk
Ruff and Black, link/document hygiene, package checksums, and Git whitespace
checks also passed. Tool-location and formatting-range attempts that did not
change files are recorded in the canonical evidence record.

## Durable evidence and limitations

The final audit payload, complete envelope, report bundle, reconciliation,
checksums, readable summary, and sensitive-content scan are preserved at
`/Users/davidshimmon/.codex/visualizations/2026/08/10/019fec4e-6d68-7910-ba7c-0a7a21472336/ledger-transition-crew-chief-final-4b295130`.
Its `SHA256SUMS` file has SHA-256
`049002db9f475aeec0bc4c407f5a15a8268dd64f9cf3ccf8f8f7cf040ecba0c9`
and verifies all 81 other files.

The lock remains cooperative: an unrelated direct SQLite opener does not
honor it, although WAL quiescence rejects an active durable writer. The local
receipt records Maverick's decision but does not independently authenticate a
human against a hostile process already running under the same trusted OS
account.

## Remaining live-execution gates

Physical Migration 4 has not run. Before it may run, the repository requires:

1. Assurance v1 and every DATA-001 prerequisite;
2. exact canonical identification of the live target and DB/WAL/SHM inventory;
3. a disposable rehearsal that writes only to a clone;
4. an immutable, non-overwriting backup destination;
5. frozen exact manifest and package bytes;
6. fresh Crew Chief review of that exact live-transition package;
7. a single-use no-retry authorization receipt; and
8. Maverick's explicit approval of that exact package.

No journal text supersedes those gates.
