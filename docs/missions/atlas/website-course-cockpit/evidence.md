# Atlas Website & Course Cockpit Evidence

The adjacent [`mission.md`](mission.md) remains the authoritative lifecycle
record. This evidence note does not authorize a commit, publication,
deployment, migration, or mission-completion declaration.

## 2026-08-10 Crew Chief timestamp metadata correction

The immutable final Crew Chief package is preserved outside the repository at
`atlas-website-final-audit-20260810`. Its checksums and report bytes must not be
rewritten.

The package records these three timestamps:

- final Crew Chief report `generated_at`: `2026-08-10T20:30:00Z`;
- controller run record `completed_at`: `2026-08-10T20:19:00Z`; and
- reconciliation `generated_at`: `2026-08-10T20:19:35Z`.

The report's later `generated_at` value is a model-authored timestamp metadata
defect. The controller and reconciliation timestamps are the operational
sequence evidence. This discrepancy is not an Atlas implementation finding
and does not indicate evidence tampering. The immutable report, reconciliation,
run record, and package checksums remain unchanged so their original evidence
bindings stay verifiable.

## 2026-08-11 corrected-base audit and 200% acceptance

Codex reconciled the exact audited Atlas implementation and mission-document
changes onto refreshed `origin/main` at
`09abc0ce50e4c86cd69da4608b6c86f1c744816e` in a disposable review subject.
All 28 non-generated implementation, test, manifest, mission, and evidence
paths were byte-identical to the original implementation worktree. Focused
validation passed 59 tests, the complete credential-free offline suite passed
448 tests, and compilation, affected-scope formatting/linting, governance, and
Git whitespace checks passed.

The genuine read-only Crew Chief audit identified one blocking medium evidence
finding, `CC-0001`: the existing 200% check was an equivalent half-size CSS
viewport rather than direct browser page zoom. Crew Chief did not identify an
Atlas implementation defect in that finding. The in-app browser did not expose
or honor page-level zoom, and no connected external browser was available for
a direct automated check.

Maverick subsequently accepted that disclosed equivalent-viewport limitation
for this mission and accepted the narrowed verification claim. The evidence
therefore establishes responsive reflow at the tested equivalent viewport; it
does **not** claim that a direct actual-200%-browser-zoom flow was performed.
The accepted subject requires a fresh Crew Chief review before the authorized
commit, push, and merge proceed.

The immutable 2026-08-11 Crew Chief report records `generated_at` as
`2026-08-11T04:00:00Z`, while its controller run record records `completed_at`
as `2026-08-11T03:31:41Z`. This is preserved as a model-authored timestamp
metadata defect, not an Atlas implementation finding or an evidence-tampering
indication. The report and its checksums were not rewritten.
